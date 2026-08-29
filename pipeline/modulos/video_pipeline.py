# -*- coding: utf-8 -*-
"""
video_pipeline.py — Pipeline enxuto do projeto Narrated Video: gera só o vídeo base.

Este módulo NÃO inclui Whisper, legendas, tradução ou classificação
morfológica — isso é responsabilidade dos notebooks seguintes (Single
Subtitle, Language Subtitles, etc.), que terão seu próprio módulo.

Sequência dos notebooks video-base-*.ipynb:
    pipeline.gerar_audio()        → Fase 1: narração (Edge TTS ou carregada)
    pipeline.baixar_clipes()      → Fase 6: corta/credita clipes do Pixabay
    pipeline.criar_video_base()   → Fase 7: concatena + narração + trilha
    pipeline.salvar_clipes_no_drive()  → opcional, backup do pool de clipes

CORREÇÃO CRÍTICA (bug de duração corrompida na concatenação):
Clipes do Pixabay vêm de autores diferentes, cada um com sua própria
resolução e taxa de quadros (fps). Concatenar clipes com esses parâmetros
DIFERENTES via stream copy corrompe silenciosamente a duração do vídeo
final — o FFmpeg não trava, só gera um aviso de "Non-monotonic DTS" que
passa despercebido, e o vídeo final fica com timestamps errados (ex: o
player mostra 5:17 de duração, mas o áudio para em 2:38).
A correção: TODO clipe é re-padronizado pra uma resolução/fps comuns
(LARGURA_CLIPE/ALTURA_CLIPE/FPS_CLIPE em config.py) no momento em que
recebe o crédito — ver ffmpeg_utils.adicionar_credito_e_logo(). A partir
daí, a concatenação por stream copy é segura e exata, porque todos os
clipes de entrada têm parâmetros idênticos.
"""
from __future__ import annotations

import hashlib
import logging
import math
import random
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from checkpoint import Checkpoint
from config import PipelineConfig
from drive_utils import DriveClient
from ffmpeg_utils import (
    FFmpegError,
    adicionar_audio,
    adicionar_credito_e_logo,
    adicionar_trilha_fundo,
    ajustar_velocidade_audio,
    concatenar_videos,
    converter_para_wav,
    cortar_video,
    imagem_para_clipe,
    obter_duracao,
)
from models import Clipe
# A regra de link do Pixabay mora num módulo só -- ela já valia aqui e no
# semeador, e ia virar um terceiro lugar. Ver pixabay_urls.py.
from pixabay_urls import (
    e_link_assinado as _e_link_assinado,
    urls_alternativas as urls_alternativas_pixabay,
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Erro geral do pipeline."""
    pass


class ClipeError(PipelineError):
    """Falha ao preparar UM clipe — existe pra o motivo chegar até o chamador.

    Antes cada caminho de falha fazia `return None` com um `logger.debug` que
    ninguém vê (o Colab liga o log em INFO). O laço então só sabia "veio
    vazio", e o erro final dizia "veja os avisos ❌ acima" — avisos que nunca
    tinham sido emitidos. Falhar sem dizer por quê custa uma sessão inteira
    de tentativa e erro.
    """


# `\S+` engoliria o ")" ou o "." que fecham a frase, e o exemplo impresso
# viraria uma URL que não abre. O `[^\s)]` para antes disso.
_RE_URL = re.compile(r"https?://[^\s)]+")


def _forma_da_falha(motivo: str) -> str:
    """A FORMA do erro, sem a URL — é por ela que se agrupa.

    Agrupar pelo texto inteiro não agrupa nada: cada imagem traz uma URL
    diferente, então 45 falhas idênticas viram "45 motivos distintos" e a
    mensagem despeja seis URLs gigantes sem dizer o que houve. O que importa
    é a forma ("HTTP 400 no link do Pixabay"), não quantas vezes ela apareceu
    escrita de um jeito ligeiramente diferente.
    """
    return _RE_URL.sub("<url>", motivo)


def _resumo_das_falhas(falhas: list[str], limite: int = 6) -> str:
    """Junta os motivos num texto que cabe numa mensagem de erro.

    Repete só o que é distinto POR FORMA: 45 imagens que morreram no mesmo
    400 são uma informação, não quarenta e cinco. De cada grupo sai um
    exemplo de URL, que é o suficiente pra você conferir à mão.
    """
    if not falhas:
        return ("Nenhum motivo foi registrado — se isto aparecer, o defeito está "
                "aqui, não na sua planilha.")

    grupos: dict[str, list[str]] = {}
    for f in falhas:
        grupos.setdefault(_forma_da_falha(f), []).append(f)

    linhas = []
    for forma, exemplos in list(grupos.items())[:limite]:
        linhas.append(f"  · {forma}" + (f"  (×{len(exemplos)})" if len(exemplos) > 1 else ""))
        urls = _RE_URL.findall(exemplos[0])
        if urls:
            linhas.append(f"      ex.: {urls[0]}")
    if len(grupos) > limite:
        linhas.append(f"  · ... e mais {len(grupos) - limite} forma(s) de falha")
    return "\n".join(linhas)


def _e_retrato(linha: dict) -> bool:
    """A foto é mais alta que larga, pelas colunas da planilha?

    Usa `Largura`/`Altura`, que a semeadura já grava — não precisa baixar a
    imagem pra saber. Linha sem essas colunas, ou com valor ilegível, passa:
    descartar pelo que não se sabe erraria pro lado caro.
    """
    try:
        largura = int(float(str(linha.get("Largura") or "").strip()))
        altura  = int(float(str(linha.get("Altura")  or "").strip()))
    except (TypeError, ValueError):
        return False
    return largura > 0 and altura > largura


def _motivo_download_imagem(clipe, erros: list[str]) -> str:
    """A mensagem de quem tentou tudo e não conseguiu baixar a imagem.

    Diz o que tentou e, no caso comum, o que fazer: link `/get/` do Pixabay
    com 400 é assinatura vencida, não imagem removida. Sem essa frase, o
    caminho natural é procurar defeito na rede ou na imagem — nos dois
    lugares errados.
    """
    partes = [f"não consegui baixar a imagem de nenhum link ({len(erros)} tentativa(s))"]
    partes.append("; ".join(erros[:3]))
    expirou = _e_link_assinado(clipe.url) and any("400" in e for e in erros)
    if expirou and not clipe.urls_alternativas:
        partes.append(
            "O link /get/ do Pixabay é ASSINADO e expira — a planilha guardou o "
            "`largeImageURL` de quando foi semeada e ele não vale mais. A coluna "
            "'URL Thumbnail' desta linha está vazia, então não há link estável pra "
            "derivar: refaça o estoque com o notebook `estoque-imagem`"
        )
    elif expirou:
        partes.append(
            "O link /get/ do Pixabay expirou E os links estáveis derivados do "
            "thumbnail também não serviram — refaça o estoque com `estoque-imagem`"
        )
    return ". ".join(partes)


def _autor_do_nome(caminho: Path) -> str:
    """Recupera o autor do nome do arquivo, se seguir a convenção clipe_NNN_autor_XXX.mp4."""
    return caminho.stem.split("_autor_")[-1] if "_autor_" in caminho.stem else "Pixabay"


class VideoPipeline:
    """Gera o vídeo base: narração + clipes creditados + trilha sonora."""

    def __init__(self, config: PipelineConfig) -> None:
        config.validate()
        self._cfg   = config
        self._drive = DriveClient.get()
        self._cp    = Checkpoint(nome_oracao=config.NOME_ORACAO)

    # ── Fase 1: Narração ─────────────────────────────────────────────────────

    def gerar_audio(self) -> Path:
        """Gera áudio com Edge TTS e salva no Drive.

        Antes de gerar qualquer coisa, procura uma narração pronta: na VM, na
        pasta do vídeo no Drive e no estoque `assets/biblia_audio/` (ver
        `_trazer_audio_do_drive`). Só cai no Edge TTS quando não achou nada em
        lugar nenhum — nunca sobrescreve um áudio já presente, aqui ou no Drive.

        Se `VELOCIDADE_AUDIO` != 1.0, ajusta a velocidade da narração (sem
        alterar o tom da voz) uma única vez — controlado por checkpoint, para
        não compor o ajuste a cada nova execução da célula.
        """
        import edge_tts
        import asyncio
        import threading

        audio_path  = Path(self._cfg.NOME_AUDIO)
        texto_hash  = hashlib.sha1(self._cfg.TEXTO_ORACAO.encode("utf-8")).hexdigest()[:12]

        # Procura no DRIVE antes de decidir gerar. Sem isto, a checagem abaixo
        # olhava só o disco da VM do Colab -- que numa sessão nova está sempre
        # vazio -- e o Edge TTS gerava por cima. Como o upload vai pra
        # `pasta_assets_audio`, que é alias de `pasta_oracao`, e o nome é o
        # mesmo, a narração sintética SOBRESCREVIA o áudio que você tinha
        # subido à mão. Perder uma gravação própria assim é calado: o vídeo
        # sai pronto, só com a voz errada, e nada no log diz que houve troca.
        origem_audio = None
        if not audio_path.exists():
            origem_audio = self._trazer_audio_do_drive(audio_path)

        if audio_path.exists():
            # 🔒 O áudio existente pode ser de uma execução anterior com um
            # TEXTO_ORACAO diferente (ex: você editou a Configuração e rodou de
            # novo sem limpar o áudio antigo primeiro). Sem isso, o pipeline
            # ficaria narrando um texto desatualizado sem avisar.
            # ...mas só faz sentido comparar hash de texto com áudio que o
            # Edge TTS gerou a partir dele. Narração humana não tem hash --
            # comparar dispararia o alarme justamente no caso normal, e
            # aviso que sempre grita é aviso que ninguém lê.
            meta = self._cp.metadados("audio_gerado") or {}
            hash_registrado = (
                meta.get("texto_hash")
                if origem_audio is None and meta.get("origem") == "edge_tts"
                else None
            )
            if hash_registrado and hash_registrado != texto_hash:
                logger.warning(
                    "   ⚠️  %s existe, mas foi gerado a partir de um TEXTO_ORACAO "
                    "diferente do atual (hash %s ≠ %s). Se isso não for esperado "
                    "(ex: você editou o texto na Configuração), apague o áudio na "
                    "limpeza seletiva e rode de novo.",
                    audio_path.name, hash_registrado, texto_hash,
                )
            logger.info("── Narração: áudio já existe (%s) — pulando geração", audio_path.name)
            self._cp.salvar("audio_gerado", {
                "arquivo": str(audio_path), "origem": origem_audio or "existente",
                "texto_hash": texto_hash,
            })
            self._ajustar_velocidade_audio(audio_path)
            # Só sobe quando o áudio NÃO veio da pasta do vídeo: aí ele ainda
            # não está lá, e as fases seguintes (clipes, mescla) o procuram
            # justamente lá. Vindo da pasta do vídeo, subir seria reescrever
            # por cima do original -- que é o que este método existe pra evitar.
            if origem_audio == "estoque":
                self._drive.upload(audio_path, self._cfg.pasta_oracao, "audio/wav")
            return audio_path

        logger.info("── Narração: gerando áudio com Edge TTS")

        async def _gerar():
            for tentativa in range(1, 4):
                try:
                    comm = edge_tts.Communicate(self._cfg.TEXTO_ORACAO, self._cfg.VOZ_EDGE)
                    await comm.save(str(audio_path))
                    return
                except Exception as exc:
                    logger.warning("Edge TTS tentativa %d/3: %s", tentativa, exc)
                    await asyncio.sleep(2)
            raise PipelineError("Edge TTS falhou após 3 tentativas")

        falha: list[BaseException] = []

        def run_in_thread():
            try:
                asyncio.run(_gerar())
            except BaseException as exc:   # repassada logo abaixo, na thread principal
                falha.append(exc)

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()

        # Exceção levantada dentro de uma thread morre com ela: o join() volta
        # como se tivesse dado certo. Sem isto, "Edge TTS falhou após 3
        # tentativas" só reaparecia como um FileNotFoundError três linhas
        # abaixo -- um erro que aponta pro lugar errado é pior que nenhum,
        # porque manda você procurar o problema onde ele não está.
        if falha:
            raise falha[0]

        logger.info("✅ Áudio: %s (%.2f MB)", audio_path.name, audio_path.stat().st_size / 1_048_576)
        self._cp.salvar("audio_gerado", {
            "arquivo": str(audio_path), "origem": "edge_tts", "texto_hash": texto_hash,
        })
        self._ajustar_velocidade_audio(audio_path)
        self._drive.upload(audio_path, self._cfg.pasta_assets_audio, "audio/wav")
        return audio_path

    # Formatos que uma narração pode chegar, e os dois jeitos de nomeá-la:
    #   40_Matt_02_audio.wav   o nome do projeto (NOME_AUDIO)
    #   40_Matt_02.mp3         o nome do estoque (biblia-audio-baixar)
    _EXTENSOES_AUDIO = (".wav", ".mp3", ".m4a", ".ogg", ".flac")

    def _trazer_audio_do_drive(self, destino: Path) -> str | None:
        """Traz pra VM uma narração que já exista no Drive, se houver.

        Duas origens, da mais específica pra mais geral:
          1. `"pasta"`   — a pasta do vídeo: gravação própria, ou o capítulo
             que você subiu à mão. Manda, porque é a escolha explícita.
          2. `"estoque"` — `assets/biblia_audio/`, o resultado do
             `biblia-audio-baixar`. É o que faz "fornecer o áudio" sumir do
             fluxo num vídeo de capítulo bíblico: se o estoque está lá, o
             pipeline acha sozinho.

        Retorna o rótulo da origem, ou None se não achou nada — e nesse caso
        o Edge TTS gera, que é o comportamento certo pra uma oração escrita.
        """
        origens = (
            ("pasta",   self._cfg.pasta_oracao,                             "pasta do vídeo"),
            ("estoque", self._cfg.pasta_base_drive / "assets" / "biblia_audio", "estoque da Bíblia"),
        )
        for rotulo, pasta, descricao in origens:
            for base in (f"{self._cfg.NOME_ORACAO}_audio", self._cfg.NOME_ORACAO):
                for ext in self._EXTENSOES_AUDIO:
                    origem = pasta / f"{base}{ext}"
                    if not origem.exists():
                        continue
                    logger.info("── Narração: achei %s no %s — nada será gerado",
                                origem.name, descricao)
                    if ext == ".wav":
                        shutil.copy2(origem, destino)
                    else:
                        converter_para_wav(origem, destino)
                    return rotulo
        return None

    def _ajustar_velocidade_audio(self, audio_path: Path) -> None:
        """Aplica VELOCIDADE_AUDIO ao áudio final, uma única vez por vídeo."""
        velocidade = self._cfg.VELOCIDADE_AUDIO
        if velocidade == 1.0:
            return
        if self._cp.fase_concluida("audio_velocidade_ajustada"):
            logger.info("── Velocidade do áudio já ajustada anteriormente (%.2fx) — pulando", velocidade)
            return

        logger.info("── Ajustando velocidade do áudio para %.2fx", velocidade)
        temp_path = audio_path.with_name(audio_path.stem + "_temp_velocidade.wav")
        ajustar_velocidade_audio(audio_path, temp_path, velocidade)
        temp_path.replace(audio_path)
        self._cp.salvar("audio_velocidade_ajustada", {"velocidade": velocidade})
        logger.info("✅ Velocidade ajustada: %s agora está a %.2fx", audio_path.name, velocidade)

    # ── Fase 6: Clipes ────────────────────────────────────────────────────────

    def baixar_clipes(self) -> list[Clipe]:
        """
        Corta clipes de DURACAO_CLIPE segundos até cobrir a duração do áudio.

        Seleção dos clipes, em ordem de prioridade:
          1. Clipes já cortados localmente (retomada de sessão) — só reaproveita
             se a duração SOMADA deles realmente cobrir o áudio atual.
          2. Pool compartilhado no Drive (assets/clipes/).
          3. Planilha Pixabay — pega as próximas linhas AINDA NÃO USADAS
             (coluna de status vazia, config.NOME_COLUNA_STATUS_PLANILHA), de
             cima para baixo, sem nenhum outro filtro — a curadoria é manual,
             na própria planilha.

        Cada clipe baixado da planilha nesta execução é marcado com a
        data/hora do momento (não mais "ok") na coluna de status da
        planilha real (Google Sheets) — ver config.NOME_COLUNA_STATUS_PLANILHA.

        Para usar imagens estáticas em vez de vídeo, veja baixar_clipes_imagem()
        (ativado via config.MODO_CLIPE="imagem").
        """
        logger.info("── Clipes: cortando")

        audio_path = Path(self._cfg.NOME_AUDIO)
        self._drive.download_se_ausente(self._cfg.pasta_assets_audio, self._cfg.NOME_AUDIO, audio_path)
        if not audio_path.exists():
            raise PipelineError("Áudio não encontrado — rode gerar_audio() primeiro.")
        duracao_total = obter_duracao(audio_path)

        num_clipes = math.ceil(duracao_total / self._cfg.DURACAO_CLIPE)
        # O último clipe raramente precisa dos DURACAO_CLIPE segundos inteiros —
        # a duração do áudio quase nunca é múltiplo exato de 5s. Corta ele já na
        # medida certa, em vez de cortar 5s inteiros e descartar a sobra depois.
        duracao_ultimo_clipe = duracao_total - (num_clipes - 1) * self._cfg.DURACAO_CLIPE
        if duracao_ultimo_clipe < 1.0:
            duracao_ultimo_clipe = self._cfg.DURACAO_CLIPE
        logger.info("   Duração total: %.1fs → %d clipes (último: %.1fs, resto: %ds)",
                     duracao_total, num_clipes, duracao_ultimo_clipe, self._cfg.DURACAO_CLIPE)

        def _duracao_do_clipe(indice: int) -> float:
            return duracao_ultimo_clipe if indice == num_clipes else self._cfg.DURACAO_CLIPE

        Path("clipes_cortados").mkdir(exist_ok=True)
        Path("temp_raw").mkdir(exist_ok=True)

        # ── 1. Clipes já cortados localmente (retomada de sessão) ────────────
        # ⚠️  clipes_cortados/ não é isolada por vídeo — se um vídeo anterior
        # deixou clipes para trás na mesma sessão/runtime, eles ficam aqui até
        # alguém limpar manualmente. Por isso NUNCA confiamos só na CONTAGEM de
        # arquivos: conferimos se a duração real, somada, cobre o áudio ATUAL
        # antes de reaproveitar — senão pode ser sobra de outro vídeo/execução.
        clipes_ja_cortados = sorted(Path("clipes_cortados").glob("clipe_*.mp4"))

        if len(clipes_ja_cortados) >= num_clipes:
            candidatos = clipes_ja_cortados[:num_clipes]
            duracao_no_disco = sum(obter_duracao(p) for p in candidatos)

            if duracao_no_disco >= duracao_total - 1.0:
                logger.info(
                    "   ✅ %d clipes já cortados localmente (%.1fs, cobre os %.1fs necessários) — nada a fazer",
                    len(candidatos), duracao_no_disco, duracao_total,
                )
                processados = [
                    Clipe(url=str(p), autor=_autor_do_nome(p), indice=i + 1, arquivo_pronto=str(p),
                          duracao_seg=_duracao_do_clipe(i + 1))
                    for i, p in enumerate(candidatos)
                ]
                self._cp.salvar("clipes_cortados", {"total": len(processados), "duracao_audio": round(duracao_total, 1)})
                return processados

            logger.warning(
                "   ⚠️  clipes_cortados/ tem %d arquivo(s), mas somam só %.1fs — menos que os "
                "%.1fs necessários. Parecem ser sobra de uma sessão/vídeo anterior — "
                "descartando e recortando do zero.",
                len(clipes_ja_cortados), duracao_no_disco, duracao_total,
            )
            for f in clipes_ja_cortados:
                f.unlink()
            clipes_ja_cortados = []

        # ── 2. Pool compartilhado no Drive (assets/clipes/) ──────────────────
        pasta_clipes_drive = self._cfg.pasta_assets_clipes
        clipes_pool = sorted(pasta_clipes_drive.glob("*.mp4")) if pasta_clipes_drive.exists() else []
        logger.info("   📁 Pool no Drive (assets/clipes/): %d clipes disponíveis", len(clipes_pool))

        n_ja_local = len(clipes_ja_cortados)
        a_processar: list[Clipe] = []

        indice = n_ja_local + 1
        for p in clipes_pool:
            if n_ja_local + len(a_processar) >= num_clipes:
                break
            a_processar.append(Clipe(url=str(p), autor=_autor_do_nome(p), indice=indice, arquivo_local=str(p),
                                      duracao_seg=_duracao_do_clipe(indice)))
            indice += 1

        # ── 3. Planilha — só se ainda faltar ─────────────────────────────────
        faltam = num_clipes - n_ja_local - len(a_processar)
        linhas_para_marcar_ok: list[int] = []
        sheet = None
        col_ok = None

        if faltam > 0:
            logger.info("   📥 Faltam %d clipes → buscando na planilha (linhas ainda não usadas, ordem aleatória)", faltam)
            sheet, linhas = self._abrir_planilha_pixabay()
            col_ok = self._coluna_planilha(sheet, self._cfg.NOME_COLUNA_STATUS_PLANILHA)

            linhas_disponiveis = [
                (num_linha, linha) for num_linha, linha in linhas
                if not str(linha.get(self._cfg.NOME_COLUNA_STATUS_PLANILHA) or "").strip()
            ]
            random.shuffle(linhas_disponiveis)  # sorteio -- não pega mais sempre a mesma ordem de cima pra baixo

            for num_linha, linha in linhas_disponiveis:
                if sum(1 for c in a_processar if not c.arquivo_local) >= faltam:
                    break
                url = str(linha.get("url") or "").strip()
                if not url or url.lower() == "nan":
                    continue
                autor = str(linha.get("Autor") or "Pixabay").strip() or "Pixabay"
                a_processar.append(Clipe(url=url, autor=autor, indice=indice, duracao_seg=_duracao_do_clipe(indice)))
                linhas_para_marcar_ok.append(num_linha)
                indice += 1

            ainda_faltam = faltam - sum(1 for c in a_processar if not c.arquivo_local)
            if ainda_faltam > 0:
                raise PipelineError(
                    f"Planilha não tem linhas suficientes ainda não usadas: "
                    f"faltam {ainda_faltam} clipes."
                )

        # ── Logo, baixada uma vez (usada no crédito de cada clipe novo) ──────
        logo_path = Path("logo_baixada.png")
        self._drive.download_se_ausente(self._cfg.pasta_assets_logo, self._cfg.NOME_ARQUIVO_LOGO, logo_path)
        if not logo_path.exists():
            logo_path = None  # type: ignore
            logger.warning("   ⚠️  Logo não encontrada — clipes novos ficarão só com o crédito em texto")

        # ── Processa (copia do pool ou baixa+corta+credita+padroniza da planilha) ──
        # Concorrência baixa de propósito — evita travar o ambiente do Colab
        processados: list[Clipe] = [
            Clipe(url=str(p), autor=_autor_do_nome(p), indice=i + 1, arquivo_pronto=str(p))
            for i, p in enumerate(clipes_ja_cortados)
        ]
        falhas: list[str] = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._processar_clipe, c, logo_path): c for c in a_processar}
            for future in as_completed(futures):
                clipe = futures[future]
                try:
                    result = future.result()
                    if result:
                        processados.append(result)
                        logger.info("   ✅ [%d/%d] %s", len(processados), num_clipes, clipe.autor)
                except Exception as exc:
                    motivo = str(exc) or type(exc).__name__
                    falhas.append(motivo)
                    logger.warning("   ❌ Clipe %d: %s", clipe.indice, motivo)

        if not processados:
            raise PipelineError(
                f"Nenhum dos {len(a_processar)} clipes da planilha pôde ser usado. "
                f"Motivos:\n{_resumo_das_falhas(falhas)}"
            )

        # 🔒 Se algum clipe falhou (download/corte) silenciosamente no loop acima,
        # 'processados' pode vir com menos clipes que o necessário — sem essa
        # checagem, o vídeo base sairia mais curto que o áudio sem avisar.
        if len(processados) < num_clipes:
            faltando = num_clipes - len(processados)
            raise PipelineError(
                f"Só {len(processados)}/{num_clipes} clipes foram processados com sucesso "
                f"({faltando} falharam). Motivos:\n{_resumo_das_falhas(falhas)}\n"
                f"Rode esta célula de novo: os clipes que já deram certo continuam em "
                f"clipes_cortados/ e não serão refeitos, só os que faltam."
            )

        # Marca data/hora na planilha real para as linhas usadas nesta execução
        if sheet is not None and linhas_para_marcar_ok:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M")
            for num_linha in linhas_para_marcar_ok:
                try:
                    sheet.update_cell(num_linha, col_ok, agora)
                except Exception as exc:
                    logger.warning("   ⚠️  Não consegui marcar a linha %d: %s", num_linha, exc)
            logger.info("   📝 %d linha(s) marcadas com data/hora (%s) na planilha",
                        len(linhas_para_marcar_ok), agora)

        self._cp.salvar("clipes_cortados", {
            "total": len(processados),
            "duracao_audio": round(duracao_total, 1),
            "clipes": [{"indice": c.indice, "arquivo": c.arquivo_pronto, "autor": c.autor} for c in processados],
        })
        return processados

    def salvar_clipes_no_drive(self, clipes: list[Clipe]) -> int:
        """
        Copia os clipes já cortados (e creditados) para o pool compartilhado
        no Drive (assets/clipes/), pra serem reaproveitados em outros vídeos.

        Totalmente opcional — sem esse backup, cada novo vídeo precisa
        baixar/cortar da planilha de novo em vez de reaproveitar clipes prontos.
        """
        salvos = 0
        try:
            self._cfg.pasta_assets_clipes.mkdir(parents=True, exist_ok=True)
            for clipe in clipes:
                if not clipe.arquivo_pronto:
                    continue
                src = Path(clipe.arquivo_pronto)
                if not src.exists():
                    continue
                autor_safe = re.sub(r"[^a-zA-Z0-9_]", "_", clipe.autor)[:30]
                dest_name = f"clipe_{clipe.indice:03d}_autor_{autor_safe}.mp4"
                dest = self._cfg.pasta_assets_clipes / dest_name
                if not dest.exists():
                    shutil.copy2(src, dest)
                    salvos += 1
                    logger.info("   💾 Clipe salvo no Drive: %s", dest_name)
        except Exception as exc:
            logger.warning("   ⚠️  Backup de clipes no Drive falhou: %s", exc)
        return salvos

    def _abrir_planilha_pixabay(self, id_planilha: Optional[str] = None):
        """Abre uma planilha Pixabay via gspread (leitura + escrita da coluna
        de status). Usa ID_PLANILHA_DRIVE (vídeos) por padrão — passe
        id_planilha explicitamente para abrir outra (ex: a de imagens)."""
        import gspread
        from google.colab import auth
        from google.auth import default

        id_planilha = id_planilha or self._cfg.ID_PLANILHA_DRIVE

        ultimo_erro = None
        for tentativa in range(1, 3):
            try:
                auth.authenticate_user()
                break
            except Exception as exc:
                ultimo_erro = exc
                logger.warning("   ⚠️  Falha na autenticação Google (tentativa %d/2): %s", tentativa, exc)
                time.sleep(3)
        else:
            raise PipelineError(
                "Não foi possível autenticar com o Google para acessar a planilha "
                f"(auth.authenticate_user() falhou 2x: {ultimo_erro}).\n"
                "Isso costuma ser uma falha temporária do ambiente Colab, não do código. Tente:\n"
                "  1. Recarregar a página do Colab (F5) e rodar esta célula de novo\n"
                "  2. Runtime → Desconectar e excluir o ambiente de execução, reconectar e rodar tudo de novo\n"
                "  3. Verificar se o navegador não está bloqueando cookies de terceiros para *.google.com"
            )

        creds, _ = default()
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(id_planilha).sheet1
        registros = sheet.get_all_records()  # linha 1 = cabeçalho
        linhas = [(i + 2, registro) for i, registro in enumerate(registros)]
        return sheet, linhas

    def _coluna_planilha(self, sheet, nome_coluna: str) -> int:
        cabecalho = sheet.row_values(1)
        if nome_coluna not in cabecalho:
            raise PipelineError(f"Coluna '{nome_coluna}' não encontrada na planilha")
        return cabecalho.index(nome_coluna) + 1

    def _processar_clipe(self, clipe: Clipe, logo_path: Optional[Path] = None) -> Optional[Clipe]:
        saida = Path(f"clipes_cortados/clipe_{clipe.indice:03d}.mp4")

        # ── Se já tem arquivo local (clipe do Drive), só copiar/cortar ────────
        # (já vem creditado E padronizado de quando foi processado pela 1ª vez —
        # não credita de novo, senão o crédito ficaria duplicado no clipe)
        if clipe.arquivo_local and Path(clipe.arquivo_local).exists():
            origem = Path(clipe.arquivo_local)
            if clipe.duracao_seg < self._cfg.DURACAO_CLIPE - 0.1:
                # Esse clipe caiu no "último slot" e precisa de menos que os
                # 5s padrão — corta na medida certa em vez de copiar inteiro.
                try:
                    cortar_video(origem, saida, clipe.duracao_seg)
                except FFmpegError:
                    shutil.copy2(origem, saida)  # fallback: usa o clipe inteiro
            else:
                shutil.copy2(origem, saida)
            if saida.exists() and saida.stat().st_size > 1000:
                clipe.arquivo_pronto = str(saida)
                logger.debug("Clipe %d: usando local %s", clipe.indice, clipe.arquivo_local)
                return clipe
            raise ClipeError(f"o clipe local {origem.name} não gerou saída utilizável")

        # ── Baixar da URL (Pixabay) ────────────────────────────────────────────
        raw = Path(f"temp_raw/raw_{clipe.indice}.mp4")
        try:
            r = requests.get(clipe.url, headers={"User-Agent": "Mozilla/5.0"},
                             timeout=30, stream=True)
            r.raise_for_status()
            with open(raw, "wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        except Exception as exc:
            raise ClipeError(f"download falhou ({type(exc).__name__}: {exc}) — {clipe.url}") from exc

        if not raw.exists():
            raise ClipeError(f"o download não gravou arquivo nenhum — {clipe.url}")
        if raw.stat().st_size < 1000:
            raise ClipeError(
                f"baixou só {raw.stat().st_size} bytes — não parece um vídeo. "
                f"A coluna tem que ser o link DIRETO do arquivo — {clipe.url}"
            )
        try:
            cortar_video(raw, saida, clipe.duracao_seg)
        except FFmpegError as exc:
            raw.unlink(missing_ok=True)
            raise ClipeError(f"o FFmpeg não cortou o vídeo: {exc}") from exc

        raw.unlink(missing_ok=True)
        if not saida.exists() or saida.stat().st_size < 1000:
            raise ClipeError("o corte terminou sem erro mas não deixou vídeo utilizável")

        # ── Crédito + logo + PADRONIZAÇÃO de resolução/fps aplicados aqui ────
        # (o vídeo base só concatena depois — não credita, corta nem padroniza
        # de novo; é essa padronização que evita a corrupção de duração)
        try:
            creditado = Path(f"clipes_cortados/clipe_{clipe.indice:03d}_creditado.mp4")
            adicionar_credito_e_logo(
                saida, creditado, f"Pixabay / {clipe.autor}", logo_path, self._cfg.TAMANHO_LOGO,
                largura=self._cfg.LARGURA_CLIPE, altura=self._cfg.ALTURA_CLIPE, fps=self._cfg.FPS_CLIPE,
            )
            creditado.replace(saida)
        except FFmpegError as exc:
            logger.warning("Crédito/logo falhou no clipe %d (usando sem crédito): %s", clipe.indice, exc)

        clipe.arquivo_local = clipe.arquivo_pronto = str(saida)
        return clipe

    # ── Fase 6b: Clipes a partir de imagens (MODO_CLIPE="imagem") ───────────

    def baixar_clipes_imagem(self) -> list[Clipe]:
        """
        Alternativa a baixar_clipes(): em vez de cortar trechos de vídeo,
        baixa fotos do Pixabay (config.ID_PLANILHA_IMAGENS_DRIVE) e
        converte cada uma num segmento de vídeo de DURACAO_CLIPE segundos
        (foto parada — sem Ken Burns/zoom, de propósito, para não competir
        com a leitura de vídeos com muitas legendas simultâneas na tela).

        Escreve nos mesmos "clipes_cortados/clipe_NNN.mp4" que baixar_clipes()
        usaria — criar_video_base() funciona igual, sem saber (nem precisar
        saber) se cada clipe veio de vídeo ou de imagem.

        Mesma lógica de resumo de sessão de baixar_clipes() (reaproveita
        clipes_cortados/ já prontos se a duração bater); não usa o pool
        compartilhado do Drive (assets/clipes/) — esse pool é só de vídeos.

        Marca a data/hora de uso na planilha de imagens (mesma coluna de
        status configurável — config.NOME_COLUNA_STATUS_PLANILHA).
        """
        logger.info("── Clipes (modo imagem): gerando")

        audio_path = Path(self._cfg.NOME_AUDIO)
        self._drive.download_se_ausente(self._cfg.pasta_assets_audio, self._cfg.NOME_AUDIO, audio_path)
        if not audio_path.exists():
            raise PipelineError("Áudio não encontrado — rode gerar_audio() primeiro.")
        duracao_total = obter_duracao(audio_path)

        num_clipes = math.ceil(duracao_total / self._cfg.DURACAO_CLIPE)
        duracao_ultimo_clipe = duracao_total - (num_clipes - 1) * self._cfg.DURACAO_CLIPE
        if duracao_ultimo_clipe < 1.0:
            duracao_ultimo_clipe = self._cfg.DURACAO_CLIPE
        logger.info("   Duração total: %.1fs → %d clipes de imagem (último: %.1fs, resto: %ds)",
                     duracao_total, num_clipes, duracao_ultimo_clipe, self._cfg.DURACAO_CLIPE)

        def _duracao_do_clipe(indice: int) -> float:
            return duracao_ultimo_clipe if indice == num_clipes else self._cfg.DURACAO_CLIPE

        Path("clipes_cortados").mkdir(exist_ok=True)
        Path("temp_raw").mkdir(exist_ok=True)

        # ── Resumo de sessão (mesmo mecanismo de baixar_clipes) ──────────────
        clipes_ja_cortados = sorted(Path("clipes_cortados").glob("clipe_*.mp4"))
        if len(clipes_ja_cortados) >= num_clipes:
            candidatos = clipes_ja_cortados[:num_clipes]
            duracao_no_disco = sum(obter_duracao(p) for p in candidatos)
            if duracao_no_disco >= duracao_total - 1.0:
                logger.info(
                    "   ✅ %d clipes já prontos localmente (%.1fs, cobre os %.1fs necessários) — nada a fazer",
                    len(candidatos), duracao_no_disco, duracao_total,
                )
                processados = [
                    Clipe(url=str(p), autor=_autor_do_nome(p), indice=i + 1, arquivo_pronto=str(p),
                          duracao_seg=_duracao_do_clipe(i + 1))
                    for i, p in enumerate(candidatos)
                ]
                self._cp.salvar("clipes_cortados", {"total": len(processados), "duracao_audio": round(duracao_total, 1), "modo": "imagem"})
                return processados
            logger.warning(
                "   ⚠️  clipes_cortados/ tem %d arquivo(s), mas somam só %.1fs — menos que os "
                "%.1fs necessários. Parecem ser sobra de uma sessão/vídeo anterior — "
                "descartando e recriando do zero.",
                len(clipes_ja_cortados), duracao_no_disco, duracao_total,
            )
            for f in clipes_ja_cortados:
                f.unlink()

        if not self._cfg.ID_PLANILHA_IMAGENS_DRIVE:
            raise PipelineError(
                "MODO_CLIPE='imagem' mas config.ID_PLANILHA_IMAGENS_DRIVE não está configurado."
            )

        logger.info("   📥 Buscando %d imagens na planilha (linhas ainda não usadas, ordem aleatória)", num_clipes)
        sheet, linhas = self._abrir_planilha_pixabay(self._cfg.ID_PLANILHA_IMAGENS_DRIVE)
        col_status = self._coluna_planilha(sheet, self._cfg.NOME_COLUNA_STATUS_PLANILHA)

        a_processar: list[Clipe] = []
        linhas_para_marcar: list[int] = []
        indice = 1

        linhas_disponiveis = [
            (num_linha, linha) for num_linha, linha in linhas
            if not str(linha.get(self._cfg.NOME_COLUNA_STATUS_PLANILHA) or "").strip()
        ]

        # Fotos em pé (formato celular) fora. A semeadura passou a pedir só
        # horizontais à API, mas as linhas já gravadas continuam lá -- e uma
        # foto 1080x1920 num quadro 16:9 perde ~2/3 da altura, sobrando o meio
        # de uma pessoa sem a cabeça.
        if self._cfg.DESCARTAR_IMAGEM_RETRATO:
            antes = len(linhas_disponiveis)
            linhas_disponiveis = [
                (n, l) for n, l in linhas_disponiveis if not _e_retrato(l)
            ]
            descartadas = antes - len(linhas_disponiveis)
            if descartadas:
                logger.info("   🚫 %d linha(s) em formato retrato descartada(s) — sobraram %d",
                            descartadas, len(linhas_disponiveis))

        random.shuffle(linhas_disponiveis)  # sorteio -- não pega mais sempre a mesma ordem de cima pra baixo

        for num_linha, linha in linhas_disponiveis:
            if len(a_processar) >= num_clipes:
                break
            url_imagem = str(linha.get("Imagem") or "").strip()
            if not url_imagem or url_imagem.lower() == "nan":
                continue
            autor = str(linha.get("Autor") or "Pixabay").strip() or "Pixabay"
            a_processar.append(Clipe(
                url=url_imagem, autor=autor, indice=indice,
                duracao_seg=_duracao_do_clipe(indice),
                # Reserva estável, derivada do thumbnail — ver
                # urls_alternativas_pixabay(). Vazia se a planilha não tiver
                # a coluna: aí só resta o link assinado.
                urls_alternativas=urls_alternativas_pixabay(str(linha.get("URL Thumbnail") or "")),
            ))
            linhas_para_marcar.append(num_linha)
            indice += 1

        if len(a_processar) < num_clipes:
            extra = ""
            if self._cfg.DESCARTAR_IMAGEM_RETRATO:
                extra = (" (fotos em retrato foram descartadas — pra aceitá-las mesmo "
                         "assim, DESCARTAR_IMAGEM_RETRATO=False na Configuração)")
            raise PipelineError(
                f"Planilha de imagens não tem linhas suficientes ainda não usadas: "
                f"faltam {num_clipes - len(a_processar)} imagens{extra}."
            )

        logo_path = Path("logo_baixada.png")
        self._drive.download_se_ausente(self._cfg.pasta_assets_logo, self._cfg.NOME_ARQUIVO_LOGO, logo_path)
        if not logo_path.exists():
            logo_path = None  # type: ignore
            logger.warning("   ⚠️  Logo não encontrada — clipes novos ficarão só com o crédito em texto")

        processados: list[Clipe] = []
        falhas: list[str] = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._processar_clipe_imagem, c, logo_path): c for c in a_processar}
            for future in as_completed(futures):
                clipe = futures[future]
                try:
                    result = future.result()
                    if result:
                        processados.append(result)
                        logger.info("   ✅ [%d/%d] %s", len(processados), num_clipes, clipe.autor)
                except Exception as exc:
                    motivo = str(exc) or type(exc).__name__
                    falhas.append(motivo)
                    logger.warning("   ❌ Imagem %d: %s", clipe.indice, motivo)

        if not processados:
            raise PipelineError(
                f"Nenhuma das {len(a_processar)} imagens da planilha pôde ser usada. "
                f"Motivos:\n{_resumo_das_falhas(falhas)}"
            )

        if len(processados) < num_clipes:
            faltando = num_clipes - len(processados)
            raise PipelineError(
                f"Só {len(processados)}/{num_clipes} imagens foram processadas com sucesso "
                f"({faltando} falharam). Motivos:\n{_resumo_das_falhas(falhas)}\n"
                f"Rode esta célula de novo: as que já deram certo continuam em "
                f"clipes_cortados/ e não serão refeitas, só as que faltam."
            )

        # Marca data/hora na planilha real para as linhas usadas nesta execução
        agora = datetime.now().strftime("%Y-%m-%d %H:%M")
        for num_linha in linhas_para_marcar:
            try:
                sheet.update_cell(num_linha, col_status, agora)
            except Exception as exc:
                logger.warning("   ⚠️  Não consegui marcar a linha %d: %s", num_linha, exc)
        logger.info("   📝 %d linha(s) marcadas com data/hora (%s) na planilha",
                    len(linhas_para_marcar), agora)

        self._cp.salvar("clipes_cortados", {
            "total": len(processados), "duracao_audio": round(duracao_total, 1), "modo": "imagem",
        })
        return processados

    def _processar_clipe_imagem(self, clipe: Clipe, logo_path: Optional[Path] = None) -> Optional[Clipe]:
        saida = Path(f"clipes_cortados/clipe_{clipe.indice:03d}.mp4")
        raw_img = Path(f"temp_raw/raw_img_{clipe.indice}.jpg")

        # A URL da planilha primeiro; depois as derivadas do thumbnail. O link
        # `pixabay.com/get/...` que a API entregou é assinado e expira, então
        # numa planilha semeada há meses ele responde 400 — e sem essa reserva
        # a planilha inteira morre de uma vez, sem nada ter mudado nela.
        erros: list[str] = []
        for tentativa, url in enumerate([clipe.url, *clipe.urls_alternativas]):
            if not url:
                continue
            try:
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
                r.raise_for_status()
                with open(raw_img, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
            except Exception as exc:
                erros.append(f"{type(exc).__name__}: {exc}")
                continue

            if not raw_img.exists():
                erros.append(f"o download não gravou arquivo nenhum — {url}")
                continue
            if raw_img.stat().st_size < 1000:
                # Página de erro, HTML de captcha ou link de página em vez do
                # JPG: tudo isso "baixa" com sucesso e vem com poucos bytes.
                erros.append(f"vieram só {raw_img.stat().st_size} bytes de {url}")
                raw_img.unlink(missing_ok=True)
                continue

            if tentativa:
                logger.info("   ↩️  Imagem %d: o link da planilha falhou, usei o estável %s",
                            clipe.indice, url)
            break
        else:
            raise ClipeError(_motivo_download_imagem(clipe, erros))

        try:
            imagem_para_clipe(
                raw_img, saida, clipe.duracao_seg,
                largura=self._cfg.LARGURA_CLIPE, altura=self._cfg.ALTURA_CLIPE, fps=self._cfg.FPS_CLIPE,
                enquadramento=self._cfg.ENQUADRAMENTO_IMAGEM,
            )
        except FFmpegError as exc:
            raw_img.unlink(missing_ok=True)
            raise ClipeError(f"o FFmpeg não converteu a imagem: {exc}") from exc

        raw_img.unlink(missing_ok=True)
        if not saida.exists() or saida.stat().st_size < 1000:
            raise ClipeError("a conversão terminou sem erro mas não deixou vídeo utilizável")

        try:
            creditado = Path(f"clipes_cortados/clipe_{clipe.indice:03d}_creditado.mp4")
            adicionar_credito_e_logo(
                saida, creditado, f"Pixabay / {clipe.autor}", logo_path, self._cfg.TAMANHO_LOGO,
                largura=self._cfg.LARGURA_CLIPE, altura=self._cfg.ALTURA_CLIPE, fps=self._cfg.FPS_CLIPE,
            )
            creditado.replace(saida)
        except FFmpegError as exc:
            logger.warning("Crédito/logo falhou na imagem %d (usando sem crédito): %s", clipe.indice, exc)

        clipe.arquivo_local = clipe.arquivo_pronto = str(saida)
        return clipe

    # ── Fase 6c: Clipes por versículo (montagem automática) ──────────────────
    # Alternativa a baixar_clipes()/baixar_clipes_imagem(): em vez de pegar as
    # próximas linhas NÃO USADAS da planilha em sequência, usa o plano de
    # segmentos já calculado por match_pipeline.calcular_segmentos_versiculo()
    # -- cada segmento já sabe EXATAMENTE qual vídeo/imagem usar (resultado do
    # match versículo↔mídia) e por quantos segundos (tempo real daquele
    # trecho na narração). Reaproveita os mesmos _processar_clipe/
    # _processar_clipe_imagem -- a única diferença é de ONDE vem a lista de
    # Clipe a processar.

    def baixar_clipes_por_versiculo(self, plano_segmentos: list[dict]) -> list[Clipe]:
        """Corta um clipe de vídeo por segmento do plano (ver
        match_pipeline.calcular_segmentos_versiculo). Não usa o pool
        compartilhado nem a seleção sequencial da planilha -- a URL de cada
        clipe já vem definida pelo match."""
        logger.info("── Clipes por versículo (modo vídeo): %d segmento(s)", len(plano_segmentos))
        Path("clipes_cortados").mkdir(exist_ok=True)
        Path("temp_raw").mkdir(exist_ok=True)

        logo_path = Path("logo_baixada.png")
        self._drive.download_se_ausente(self._cfg.pasta_assets_logo, self._cfg.NOME_ARQUIVO_LOGO, logo_path)
        if not logo_path.exists():
            logo_path = None  # type: ignore

        a_processar = [
            Clipe(url=seg["url"], autor=seg.get("autor", "Pixabay"), indice=i + 1,
                  duracao_seg=seg["duracao_seg"])
            for i, seg in enumerate(plano_segmentos)
        ]

        processados: list[Clipe] = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._processar_clipe, c, logo_path): c for c in a_processar}
            for future in as_completed(futures):
                clipe = futures[future]
                try:
                    result = future.result()
                    if result:
                        processados.append(result)
                        logger.info("   ✅ [%d/%d] versículo(s) %s — %s",
                                    len(processados), len(a_processar),
                                    plano_segmentos[clipe.indice - 1]["versiculos"], clipe.autor)
                    else:
                        seg = plano_segmentos[clipe.indice - 1]
                        raise PipelineError(
                            f"Falha ao baixar/cortar o clipe do versículo {seg['versiculos'][0]} "
                            f"(id={seg['id']}, url={seg['url']}) -- confira se a URL ainda é válida."
                        )
                except Exception as exc:
                    logger.error("   ❌ Segmento %d: %s", clipe.indice, exc)
                    raise

        if not processados:
            raise PipelineError("Nenhum clipe processado com sucesso")
        return processados

    def baixar_clipes_imagem_por_versiculo(self, plano_segmentos: list[dict]) -> list[Clipe]:
        """Mesma lógica de baixar_clipes_por_versiculo(), mas convertendo
        cada imagem escolhida pelo match num segmento de vídeo parado
        (mesma duração do trecho de narração daquele versículo)."""
        logger.info("── Clipes por versículo (modo imagem): %d segmento(s)", len(plano_segmentos))
        Path("clipes_cortados").mkdir(exist_ok=True)
        Path("temp_raw").mkdir(exist_ok=True)

        logo_path = Path("logo_baixada.png")
        self._drive.download_se_ausente(self._cfg.pasta_assets_logo, self._cfg.NOME_ARQUIVO_LOGO, logo_path)
        if not logo_path.exists():
            logo_path = None  # type: ignore

        a_processar = [
            Clipe(url=seg["url"], autor=seg.get("autor", "Pixabay"), indice=i + 1,
                  duracao_seg=seg["duracao_seg"],
                  # Mesma reserva do modo padrão. Aqui ela pesa mais: um match
                  # salvo há meses guarda o link assinado, que já venceu, e sem
                  # o thumbnail o capítulo inteiro morre com 400 sem recuperação.
                  urls_alternativas=urls_alternativas_pixabay(seg.get("url_thumbnail", "")))
            for i, seg in enumerate(plano_segmentos)
        ]

        # A campeã que VOCÊ escolheu nunca é descartada -- diferente do modo
        # padrão, onde é o sistema que sorteia e pode pular a linha seguinte.
        # Mas uma campeã em pé perde ~2/3 da altura no corte, e isso sairia
        # calado: o vídeo fica pronto, só com a imagem decapitada. Avisar é o
        # mínimo; quem troca a campeã é você, não o código.
        em_pe = [
            f"v{seg['versiculos'][0]} — {seg.get('titulo') or seg.get('id')} "
            f"({seg.get('largura')}x{seg.get('altura')})"
            for seg in plano_segmentos if _e_retrato({"Largura": seg.get("largura"),
                                                      "Altura": seg.get("altura")})
        ]
        if em_pe:
            logger.warning(
                "   ⚠️  %d campeã(s) em formato retrato — o corte pra 16:9 vai comer "
                "cerca de 2/3 da altura. Considere escolher outra no match:\n     %s",
                len(em_pe), "\n     ".join(em_pe),
            )

        processados: list[Clipe] = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._processar_clipe_imagem, c, logo_path): c for c in a_processar}
            for future in as_completed(futures):
                clipe = futures[future]
                try:
                    result = future.result()
                    if result:
                        processados.append(result)
                        logger.info("   ✅ [%d/%d] versículo(s) %s — %s",
                                    len(processados), len(a_processar),
                                    plano_segmentos[clipe.indice - 1]["versiculos"], clipe.autor)
                    else:
                        seg = plano_segmentos[clipe.indice - 1]
                        raise PipelineError(
                            f"Falha ao baixar/converter a imagem do versículo {seg['versiculos'][0]} "
                            f"(id={seg['id']}, url={seg['url']}) -- confira se a URL ainda é válida."
                        )
                except Exception as exc:
                    logger.error("   ❌ Segmento %d: %s", clipe.indice, exc)
                    raise

        if not processados:
            raise PipelineError("Nenhum clipe processado com sucesso")
        return processados

    # ── Fase 7: Vídeo base ───────────────────────────────────────────────────

    def criar_video_base(self, clipes: list[Clipe], trilha_path: Optional[Path] = None) -> Path:
        """Concatena os clipes já cortados e creditados, adiciona narração e trilha.

        Crédito, logo e padronização de resolução/fps já foram aplicados em
        baixar_clipes() — aqui só falta juntar tudo.

        `trilha_path`: quando informado, usa ESSE arquivo de áudio como
        trilha de fundo diretamente, sem passar por _resolver_trilha_sonora()
        (que só sabe pegar 1 arquivo fixo de assets/trilha/). Usado pelos
        notebooks *-trilhas.ipynb, que montam a trilha antes (ver
        trilha_pipeline.calcular_segmentos_trilha + ffmpeg_utils.
        montar_trilha_sequencial) e só entregam o resultado pronto aqui.
        Se None (padrão), comportamento inalterado -- cai no arquivo único
        de assets/trilha/, como sempre.
        """
        logger.info("── Vídeo base: concatenando")

        arquivos_prontos = [Path(c.arquivo_pronto) for c in sorted(clipes, key=lambda c: c.indice)]

        video_sem_audio = Path("video_sem_audio.mp4")
        concatenar_videos(arquivos_prontos, video_sem_audio)

        audio_path = Path(self._cfg.NOME_AUDIO)
        self._drive.download_se_ausente(self._cfg.pasta_assets_audio, self._cfg.NOME_AUDIO, audio_path)
        video_com_audio = Path("video_com_audio.mp4")
        adicionar_audio(video_sem_audio, audio_path, video_com_audio)
        video_sem_audio.unlink(missing_ok=True)

        musica_path = trilha_path if (trilha_path and Path(trilha_path).exists()) else self._resolver_trilha_sonora()
        video_base = Path(self._cfg.NOME_VIDEO_BASE)
        if musica_path and musica_path.exists():
            adicionar_trilha_fundo(
                video_com_audio, musica_path, video_base,
                volume=self._cfg.VOLUME_MUSICA,
                volume_narracao=self._cfg.VOLUME_NARRACAO,
            )
            video_com_audio.unlink(missing_ok=True)
        else:
            video_com_audio.rename(video_base)
            logger.warning("Trilha não encontrada — vídeo base sem música de fundo")

        self._drive.upload(video_base, self._cfg.pasta_assets_videos, "video/mp4")
        logger.info("✅ Vídeo base: %s (%.2f MB)", video_base.name, video_base.stat().st_size / 1_048_576)
        self._cp.salvar("video_base_criado", {
            "arquivo": str(video_base),
            "duracao_audio": round(obter_duracao(audio_path), 1),
        })
        return video_base

    def _resolver_trilha_sonora(self) -> Optional[Path]:
        """
        Resolve o arquivo de trilha sonora em assets/trilha/.

        Prioridade:
          1. Arquivo com o nome configurado em cfg.NOME_ARQUIVO_MUSICA (se existir)
          2. Único arquivo de áudio (.mp3/.wav/.m4a/.ogg) presente em assets/trilha/
        """
        pasta_trilha = self._cfg.pasta_assets_musica

        musica_path = Path(self._cfg.NOME_ARQUIVO_MUSICA)
        if self._drive.download_se_ausente(pasta_trilha, self._cfg.NOME_ARQUIVO_MUSICA, musica_path):
            if musica_path.exists():
                return musica_path

        EXTENSOES_AUDIO = {".mp3", ".wav", ".m4a", ".ogg"}
        try:
            candidatos = [
                f for f in self._drive.listar_pasta(pasta_trilha)
                if Path(f["name"]).suffix.lower() in EXTENSOES_AUDIO
            ]
        except Exception as exc:
            logger.debug("Não foi possível listar %s: %s", pasta_trilha, exc)
            candidatos = []

        if len(candidatos) == 1:
            nome = candidatos[0]["name"]
            logger.info(
                "   🎵 Trilha '%s' não encontrada — usando '%s' (único arquivo em assets/trilha/)",
                self._cfg.NOME_ARQUIVO_MUSICA, nome,
            )
            destino = Path(nome)
            if self._drive.download(pasta_trilha, nome, destino):
                return destino
        elif len(candidatos) > 1:
            logger.warning(
                "   ⚠️  assets/trilha/ tem %d arquivos de áudio e nenhum corresponde a "
                "NOME_ARQUIVO_MUSICA ('%s') — ajuste config.py ou deixe só 1 arquivo na pasta.",
                len(candidatos), self._cfg.NOME_ARQUIVO_MUSICA,
            )

        return None
