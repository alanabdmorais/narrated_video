# -*- coding: utf-8 -*-
"""
caption_pipeline.py — Pipeline de legenda única (Single Subtitle).

Módulo próprio, separado de video_pipeline.py (que fica só com o vídeo
base — ver docstring de video_pipeline.py). Cobre os dois notebooks desta
etapa:

    caption-single-generate.ipynb        → CaptionPipeline.transcrever_whisper()
    caption-single-burn.ipynb   → CaptionPipeline.carregar_legenda_unica()
                                   CaptionPipeline.queimar_legenda_unica()

Conceito importante — NÃO confundir com "legenda mestre" (que só vai
existir quando Language Subtitles for construído, como o molde de
segmentação/palavras que os outros idiomas devem seguir). Aqui é mais
simples: config.nome_legenda_unica só diz "qual arquivo SRT, já salvo na
pasta deste vídeo, o pipeline usa como legenda única no vídeo final".

Fluxo:
    1. caption-single-generate.ipynb roda o Whisper sobre o áudio e salva o
       resultado como SRT em config.pasta_oracao / config.NOME_SRT_PT_WHISPER
       (esse é o nome padrão que config.nome_legenda_unica aponta, a menos
       que você preencha NOME_LEGENDA_UNICA com outro nome).
    2. (opcional, fora do Colab) você baixa esse SRT, corrige manualmente,
       e reenvia para o Drive — seja substituindo o mesmo arquivo, seja
       salvando com outro nome e apontando NOME_LEGENDA_UNICA para ele.
    3. caption-single-burn.ipynb lê o que estiver em config.nome_legenda_unica
       nesse momento e queima no vídeo base — sempre baixa a versão mais
       recente do Drive, nunca reaproveita uma cópia local desatualizada de
       uma sessão anterior.
"""
from __future__ import annotations

import logging
from pathlib import Path

from checkpoint import Checkpoint
from config import PipelineConfig
from drive_utils import DriveClient
from ffmpeg_utils import gerar_ass_simples, gerar_ass_versiculo, queimar_legendas_ass
from models import Legenda
from srt_utils import alinhar_versiculos, gerar_legendas_versiculo, ler_srt, salvar_srt

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Erro geral do pipeline de legenda única."""


def resolver_texto_versiculos(config: PipelineConfig, texto_colado: str = "",
                              drive: DriveClient | None = None,
                              salvar_na_pasta: bool = True) -> tuple[str, str]:
    """O texto por versículo do capítulo -> (texto, de onde veio).

    Três fontes, da mais específica pra mais geral:

      1. `texto_colado`  -- o que você escreveu na Configuração, se escreveu
      2. `<nome>_roteiro_versiculos.txt` na pasta do vídeo no Drive
      3. `dados_lexico/web-biblia.json` -- a Bíblia inteira

    A do meio existe porque o roteiro de um vídeo pode ter sido EDITADO (versículo
    mesclado, palavra que a dublagem falou diferente do escrito) -- e essa edição
    tem que ganhar da Bíblia crua. A terceira é o que faz o roteiro deixar de ser
    algo que você fornece e virar algo que o sistema busca: com o web-biblia.json
    no lugar, qualquer capítulo dos 1.189 sai sem você colar nada.

    Quando cai na fonte 3, grava o resultado como o roteiro do vídeo: da próxima
    vez sai pela fonte 2, e fica um arquivo pra você corrigir se algo estiver
    torto. Passe `salvar_na_pasta=False` pra só ler.

    Vive aqui, e não dentro de um notebook, porque os TRÊS notebooks de burn
    (single, multilang e multilang-zh) precisam exatamente disto -- e a versão
    copiada em três lugares é a que diverge no primeiro conserto.
    """
    if texto_colado.strip():
        return texto_colado, "Configuração (TEXTO_VERSICULOS)"

    import biblia_texto as bt

    drive = drive or DriveClient.get()
    roteiro = Path(config.nome_roteiro_versiculos)

    if drive.download_se_ausente(config.pasta_oracao,
                                 config.nome_roteiro_versiculos, roteiro):
        return roteiro.read_text(encoding="utf-8"), roteiro.name

    if config.caminho_web_biblia.exists():
        texto = bt.roteiro_do_capitulo(config.NOME_ORACAO, config.caminho_web_biblia)
        if salvar_na_pasta:
            roteiro.write_text(texto, encoding="utf-8")
            drive.upload(roteiro, config.pasta_oracao, "text/plain")
            logger.info("   ↳ salvo como %s na pasta do vídeo", roteiro.name)
        return texto, bt.NOME_BIBLIA_JSON

    raise PipelineError(
        f"Nenhuma fonte de texto por versículo pra {config.NOME_ORACAO}:\n"
        f"  1. TEXTO_VERSICULOS está vazio na Configuração\n"
        f"  2. {config.nome_roteiro_versiculos} não está em {config.pasta_oracao}\n"
        f"  3. {config.caminho_web_biblia} não existe "
        f"— rode o biblia-texto-baixar.ipynb uma vez e nunca mais precise "
        f"fornecer roteiro de capítulo bíblico.")


def _sha1(caminho: Path) -> str:
    """Impressão digital de um arquivo, pra saber se ele mudou."""
    import hashlib
    return hashlib.sha1(Path(caminho).read_bytes()).hexdigest()


class CaptionPipeline:
    """Gera (via Whisper) e queima a legenda única (1 faixa, texto simples)."""

    def __init__(self, config: PipelineConfig) -> None:
        config.validate()
        self._cfg   = config
        self._drive = DriveClient.get()
        self._cp    = Checkpoint(nome_oracao=config.NOME_ORACAO)

    # ── Geração (caption-single-generate.ipynb) ────────────────────────────────────────

    def _e_transcricao_intocada(self, caminho: Path) -> bool:
        """O SRT no Drive é exatamente o que este notebook gerou da última vez?

        A guarda de legenda mestre existe pra não apagar correção manual. Mas
        "o arquivo existe" não é o mesmo que "foi corrigido": trocar o modelo
        do Whisper e rodar de novo esbarrava na guarda, protegendo uma
        transcrição ruim que ninguém tinha revisado — e a saída oferecida era
        desligar a proteção, que depois fica desligada.

        Com o sha1 do que foi gerado guardado no checkpoint, dá pra separar os
        dois casos: se bate, é nosso e pode ser refeito; se não bate, alguém
        mexeu e aí sim a guarda vale.

        Sem checkpoint (sessão nova, ou primeira vez), devolve False -- na
        dúvida, protege. Perder uma correção é caro; refazer uma transcrição
        custa um minuto.
        """
        meta = self._cp.metadados("transcricao_whisper_gerada") or {}
        sha_registrado = meta.get("sha1")
        if not sha_registrado:
            return False
        return sha_registrado == _sha1(caminho)

    def transcrever_whisper(self, modelo: str = "small") -> Path:
        """
        Transcreve o áudio com Whisper e salva o resultado como SRT.

        Salva sempre em config.NOME_SRT_PT_WHISPER (o nome padrão de
        transcrição) — se você quiser que essa transcrição seja a legenda
        escolhida para queimar, deixe NOME_LEGENDA_UNICA em branco (usa o
        padrão automaticamente). Se preferir manter várias transcrições
        /versões, ajuste NOME_LEGENDA_UNICA para escolher qual usar depois.

        Usa os timestamps de SEGMENTO do Whisper (não palavra-a-palavra —
        suficiente para uma legenda única de texto corrido).

        Idempotente por conteúdo: roda de novo sem problema, sempre
        sobrescreve o arquivo com uma nova transcrição — EXCETO se o
        destino for a legenda mestre atual (config.nome_legenda_mestre) e
        config.PROTEGER_LEGENDA_MESTRE estiver True (padrão): nesse caso,
        recusa rodar para não apagar uma correção manual já feita. Veja
        PROTEGER_LEGENDA_MESTRE em config.py.
        """
        destino = Path(self._cfg.NOME_SRT_PT_WHISPER)

        if self._cfg.PROTEGER_LEGENDA_MESTRE and destino.name == self._cfg.nome_legenda_mestre:
            destino_drive = self._cfg.pasta_oracao / destino.name
            if destino_drive.exists() and not self._e_transcricao_intocada(destino_drive):
                anterior = (self._cp.metadados("transcricao_whisper_gerada") or {})
                modelo_anterior = anterior.get("modelo_whisper")
                raise PipelineError(
                    f"'{destino.name}' já existe no Drive e NÃO bate com a última "
                    f"transcrição que este notebook gerou"
                    + (f" (modelo '{modelo_anterior}')" if modelo_anterior else "")
                    + ".\n"
                    f"Ou seja: alguém editou o arquivo — provavelmente você, corrigindo "
                    f"à mão. Recusei sobrescrever pra não jogar essa correção fora.\n\n"
                    f"Se quiser mesmo re-transcrever do zero, rode com\n"
                    f"  PipelineConfig(..., PROTEGER_LEGENDA_MESTRE=False)"
                )

        audio_path = Path(self._cfg.NOME_AUDIO)
        # Procura nos três lugares, não só na pasta do vídeo -- ver
        # audio_narracao. A versão anterior parava com "rode o video-base
        # primeiro" num capítulo cujo áudio estava no estoque o tempo todo.
        import audio_narracao
        audio_narracao.trazer(self._cfg, audio_path)
        if not audio_path.exists():
            raise PipelineError(audio_narracao.erro_nao_achei(self._cfg))

        from whisper_utils import carregar_modelo_whisper
        model = carregar_modelo_whisper(modelo)

        logger.info(
            "── Whisper: transcrevendo %s (idioma: %s)",
            audio_path.name, self._cfg.IDIOMA_MESTRE,
        )
        resultado = model.transcribe(str(audio_path), language=self._cfg.IDIOMA_MESTRE)

        legendas: list[Legenda] = []
        for seg in resultado.get("segments", []):
            texto = str(seg.get("text", "")).strip()
            if not texto:
                continue
            legendas.append(Legenda(
                id=len(legendas) + 1,
                inicio_ms=int(round(seg["start"] * 1000)),
                fim_ms=int(round(seg["end"] * 1000)),
                texto=texto,
            ))

        if not legendas:
            raise PipelineError(
                "Whisper não retornou nenhum segmento com texto — confira o "
                "áudio e o IDIOMA_MESTRE configurado."
            )

        salvar_srt(legendas, destino)
        self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")

        self._cp.salvar("transcricao_whisper_gerada", {
            "arquivo": str(destino),
            "total_legendas": len(legendas),
            "modelo_whisper": modelo,
            "idioma": self._cfg.IDIOMA_MESTRE,
            # Guarda a impressão digital do que ACABAMOS de gerar. É por ela que
            # a próxima execução distingue "SRT que eu mesmo produzi" de "SRT que
            # você corrigiu à mão" -- ver _e_transcricao_intocada.
            "sha1": _sha1(destino),
        })
        logger.info("✅ Transcrição: %s (%d legendas)", destino.name, len(legendas))
        return destino

    # ── Queima (caption-single-burn.ipynb) ─────────────────────────────────────

    def carregar_legenda_unica(self) -> list[Legenda]:
        """
        Carrega, do Drive, o SRT apontado por config.nome_legenda_unica —
        sempre a versão mais recente.

        Propositalmente NÃO usa download_se_ausente: se você corrigiu o SRT
        manualmente e reenviou ao Drive, uma cópia local antiga (de uma
        sessão anterior no mesmo runtime) não pode "vencer" por engano.
        """
        nome    = self._cfg.nome_legenda_unica
        destino = Path(nome)
        self._drive.download(self._cfg.pasta_oracao, nome, destino)

        if not destino.exists():
            raise PipelineError(
                f"Legenda não encontrada no Drive: {self._cfg.pasta_oracao / nome}. "
                f"Rode o caption-single-generate.ipynb primeiro (ou confira NOME_LEGENDA_UNICA)."
            )

        legendas = ler_srt(destino)
        if not legendas:
            raise PipelineError(f"Legenda encontrada mas vazia: {destino}")

        logger.info("── Legenda escolhida carregada: %s (%d legendas)", destino.name, len(legendas))
        return legendas

    def gerar_legenda_versiculo(self, texto_com_versiculos: str) -> Path:
        """
        Gera o SRT do indicador de livro:versículo NUM SÓ IDIOMA (o mestre)
        — alinha o texto fornecido (com números de versículo isolados no
        meio do fluxo, ex: "1 Now when Jesus... 2 Where is he...") contra a
        legenda única (que aqui faz o papel de referência de tempo), e
        salva como config.nome_srt_versiculo no Drive.

        Só 1 idioma na tela aqui (legenda única) — por isso a abreviação
        usada é só a do IDIOMA_MESTRE, não a combinação de todos os
        idiomas (isso é o vídeo de legendas multi-idioma, ver
        language_captions_pipeline.py).

        Opcional — só use em vídeos de estudo bíblico por versículo. Para
        vídeos de oração/conteúdo livre, sem citação bíblica, não chame
        este método nem passe incluir_versiculo=True em queimar_legenda_unica().
        """
        legendas_referencia = self.carregar_legenda_unica()
        tempos = alinhar_versiculos(texto_com_versiculos, legendas_referencia)
        if not tempos:
            raise PipelineError(
                "Nenhum versículo encontrado no texto fornecido — confira se os "
                "números de versículo aparecem isolados por espaço no texto."
            )

        fim_video_ms = legendas_referencia[-1].fim_ms
        abreviacao_mestre = self._cfg.ABREVIACOES_LIVRO.get(self._cfg.IDIOMA_MESTRE, self._cfg.IDIOMA_MESTRE)
        legendas_versiculo = gerar_legendas_versiculo(tempos, self._cfg.CAPITULO, [abreviacao_mestre], fim_video_ms)

        destino = Path(self._cfg.nome_srt_versiculo)
        salvar_srt(legendas_versiculo, destino)
        self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")
        self._cp.salvar("legenda_versiculo_gerada", {
            "arquivo": str(destino), "total_versiculos": len(legendas_versiculo),
        })
        logger.info("✅ Legenda de versículo: %s (%d versículos)", destino.name, len(legendas_versiculo))
        return destino

    def queimar_legenda_unica(self, legendas: list[Legenda], incluir_versiculo: bool = False) -> Path:
        """Gera o .ass de legenda única e queima no vídeo base → vídeo final.

        Se incluir_versiculo=True, também queima o indicador de
        livro:versículo (config.nome_srt_versiculo, gerado antes via
        gerar_legenda_versiculo()) no canto superior esquerdo — opcional,
        só faz sentido para vídeos de estudo bíblico por versículo (não
        para vídeos de oração/conteúdo livre sem citação).
        """
        video_base = Path(self._cfg.NOME_VIDEO_BASE)
        self._drive.download_se_ausente(self._cfg.pasta_oracao, self._cfg.NOME_VIDEO_BASE, video_base)
        if not video_base.exists():
            raise PipelineError(
                f"Vídeo base não encontrado: {video_base}. "
                f"Rode um dos notebooks video-base-*.ipynb primeiro."
            )

        ass_paths: list[Path] = [gerar_ass_simples(
            legendas, self._cfg,
            caminho_saida=Path(f"legenda_unica_{self._cfg.NOME_ORACAO}.ass"),
            # Sem isso, IDIOMA_MESTRE coreano ou chinês sai em quadradinhos:
            # o estilo padrão deste .ass é Arial, que não tem Hangul nem Han.
            lang=self._cfg.IDIOMA_MESTRE,
        )]

        if incluir_versiculo:
            nome_versiculo = self._cfg.nome_srt_versiculo
            destino_versiculo = Path(nome_versiculo)
            self._drive.download(self._cfg.pasta_oracao, nome_versiculo, destino_versiculo)
            if not destino_versiculo.exists():
                raise PipelineError(
                    f"Legenda de versículo não encontrada no Drive: "
                    f"{self._cfg.pasta_oracao / nome_versiculo}. Rode "
                    f"gerar_legenda_versiculo() primeiro, ou chame com incluir_versiculo=False."
                )
            legendas_versiculo = ler_srt(destino_versiculo)
            ass_paths.append(gerar_ass_versiculo(
                legendas_versiculo, self._cfg,
                caminho_saida=Path(f"versiculo_{self._cfg.NOME_ORACAO}.ass"),
            ))

        video_final = Path(self._cfg.NOME_VIDEO_FINAL)
        queimar_legendas_ass(video_base, ass_paths, video_final)

        self._drive.upload(video_final, self._cfg.pasta_oracao, "video/mp4")
        self._cp.salvar("legendas_queimadas", {"arquivo": str(video_final)})
        logger.info(
            "✅ Vídeo final (legenda única): %s (%.2f MB)",
            video_final.name, video_final.stat().st_size / 1_048_576,
        )
        return video_final
