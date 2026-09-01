# -*- coding: utf-8 -*-
"""
language_captions_pipeline.py — Pipeline de legendas multi-idioma (Language
Subtitles).

Módulo próprio, separado de caption_pipeline.py (Single Subtitle) e de
video_pipeline.py (vídeo base). Cobre 3 notebooks:

    caption-multilang-sources-gather.ipynb    → baixar_legendas_youtube()
                                        baixar_audio_e_transcrever()
    caption-multilang-generate.ipynb → redistribuir_idiomas()
    caption-multilang-burn.ipynb     → carregar_idiomas_finais()
                                        queimar_idiomas()

Conceito de "legenda mestre" (ver config.nome_legenda_mestre): o SRT que
define a SEGMENTAÇÃO e os TEMPOS que todos os idiomas-alvo devem seguir —
por padrão, reaproveita o SRT já corrigido do Single Subtitle. Os idiomas-
alvo NÃO usam os tempos do próprio Whisper/YouTube deles: o texto bruto de
cada idioma é redistribuído nos MESMOS blocos/tempos da legenda mestre,
para que todos os idiomas fiquem sincronizados entre si na tela.

Por idioma-alvo, há duas fontes possíveis de texto bruto (ver
config.fonte_texto): a legenda do YouTube (nome_srt_yt) ou a transcrição do
Whisper sobre o áudio dublado (nome_srt_whisper). Ambas podem ser corrigidas
manualmente (baixe, corrija, reenvie ao Drive) antes da redistribuição.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from checkpoint import Checkpoint
from config import PipelineConfig
from drive_utils import DriveClient
from ffmpeg_utils import gerar_ass, gerar_ass_versiculo, queimar_legendas_ass
from groq_client import GroqClient, GroqError
from models import Legenda, Palavra
from srt_utils import (
    ajustar_para_n_partes,
    conferir_redistribuicao,
    alinhar_versiculos,
    extrair_texto_unico,
    gerar_legendas_versiculo,
    ler_srt,
    salvar_srt,
    texto_corrido,
)
from youtube_utils import (
    baixar_audio_idioma,
    baixar_legenda_youtube,
    garantir_runtime_js,
    garantir_yt_dlp_atualizado,
    resolver_cookies,
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Erro geral do pipeline de legendas multi-idioma."""


class LanguageCaptionsPipeline:
    """Coleta, redistribui e queima legendas em múltiplos idiomas."""

    def __init__(self, config: PipelineConfig, groq_client: Optional[GroqClient] = None) -> None:
        config.validate()
        self._cfg   = config
        self._drive = DriveClient.get()
        self._cp    = Checkpoint(nome_oracao=config.NOME_ORACAO)
        self._groq  = groq_client  # só necessário para redistribuir_idiomas()

    # ── Estágio 1: coleta (caption-multilang-sources-gather.ipynb) ──────────────────────

    def baixar_legendas_youtube(self, url: str, idiomas: list[str]) -> dict[str, Path]:
        """Baixa a legenda do YouTube (manual ou automática) para cada idioma
        e salva como {NOME}_yt_{lang}.srt no Drive.

        Pula automaticamente o IDIOMA_MESTRE, se estiver na lista — a
        legenda mestre já é tratada pelo caption-single-generate.ipynb e nunca deve
        ser baixada/sobrescrita por esta função.
        """
        garantir_yt_dlp_atualizado()
        extra_args = garantir_runtime_js()
        cookies    = resolver_cookies(self._cfg)

        resultados: dict[str, Path] = {}
        for lang in idiomas:
            if lang == self._cfg.IDIOMA_MESTRE:
                logger.info(
                    "   ⏭️  [%s] É o idioma mestre — pulando (já tratado pelo caption-single-generate.ipynb, "
                    "veja config.nome_legenda_mestre).", lang,
                )
                continue

            bruto = Path(f"raw_yt_{lang}.srt")
            codigo_yt = self._cfg.codigo_legenda_youtube(lang)
            ok = baixar_legenda_youtube(url, lang, bruto, extra_args, cookies, codigo_youtube=codigo_yt)
            if not ok:
                continue

            legendas = ler_srt(bruto)  # já limpa [Music]/[Applause] etc.
            bruto.unlink(missing_ok=True)
            if not legendas:
                logger.warning("   ⚠️  [%s] Legenda baixada mas vazia após limpeza — pulando", lang)
                continue

            destino = Path(self._cfg.nome_srt_yt(lang))
            salvar_srt(legendas, destino)
            self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")
            resultados[lang] = destino
            logger.info("   ✅ [%s] %s (%d blocos)", lang.upper(), destino.name, len(legendas))

        self._cp.salvar("legendas_youtube_baixadas", {"idiomas": list(resultados.keys())})
        return resultados

    def baixar_audio_idiomas(self, url: str, idiomas: list[str]) -> dict[str, Path]:
        """Baixa (só baixa, sem transcrever) o áudio dublado automático de
        cada idioma e salva como {NOME}_audio_{lang}.wav no Drive.

        Pula automaticamente o IDIOMA_MESTRE, se estiver na lista — o
        áudio mestre já vem de um dos video-base-*.ipynb (config.NOME_AUDIO), não
        do YouTube, e não deve ser sobrescrito aqui.
        """
        garantir_yt_dlp_atualizado()
        extra_args = garantir_runtime_js()
        cookies    = resolver_cookies(self._cfg)

        resultados: dict[str, Path] = {}
        for lang in idiomas:
            if lang == self._cfg.IDIOMA_MESTRE:
                logger.info(
                    "   ⏭️  [%s] É o idioma mestre — pulando (o áudio mestre já vem de "
                    "video-base-*.ipynb, não do YouTube).", lang,
                )
                continue

            audio_dest = Path(self._cfg.nome_audio_idioma(lang))
            formato_manual = self._cfg.formato_manual_audio(lang)
            ok = baixar_audio_idioma(url, lang, audio_dest, extra_args, cookies, formato_manual=formato_manual)
            if not ok:
                continue
            self._drive.upload(audio_dest, self._cfg.pasta_oracao, "audio/wav")
            resultados[lang] = audio_dest
            logger.info(
                "   ✅ [%s] %s (%.1f MB)",
                lang.upper(), audio_dest.name, audio_dest.stat().st_size / 1_048_576,
            )

        self._cp.salvar("audio_idiomas_baixados", {"idiomas": list(resultados.keys())})
        return resultados

    def transcrever_audio_idiomas(self, idiomas: list[str], modelo: str = "small") -> dict[str, Path]:
        """Transcreve com Whisper o áudio de cada idioma (já baixado por
        baixar_audio_idiomas() — se não estiver local, baixa do Drive antes)
        e salva como {NOME}_whisper_{lang}.srt no Drive.

        Pula automaticamente o IDIOMA_MESTRE, se estiver na lista — a
        transcrição mestre já é feita pelo caption-single-generate.ipynb (e
        normalmente já foi corrigida manualmente); nunca deve ser refeita
        nem sobrescrita por esta função.
        """
        from whisper_utils import carregar_modelo_whisper

        idiomas_a_processar = []
        for lang in idiomas:
            if lang == self._cfg.IDIOMA_MESTRE:
                logger.info(
                    "   ⏭️  [%s] É o idioma mestre — pulando (transcrição já feita pelo "
                    "caption-single-generate.ipynb, veja config.nome_legenda_mestre).", lang,
                )
                continue
            idiomas_a_processar.append(lang)

        if not idiomas_a_processar:
            logger.info("Nenhum idioma para transcrever (só o mestre estava na lista).")
            self._cp.salvar("audio_idiomas_transcritos", {"idiomas": []})
            return {}

        model = carregar_modelo_whisper(modelo)

        resultados: dict[str, Path] = {}
        for lang in idiomas_a_processar:
            nome_audio  = self._cfg.nome_audio_idioma(lang)
            audio_local = Path(nome_audio)
            self._drive.download_se_ausente(self._cfg.pasta_oracao, nome_audio, audio_local)
            if not audio_local.exists():
                logger.warning(
                    "   ⚠️  [%s] Áudio não encontrado (nem local, nem no Drive) — pulando. "
                    "Rode baixar_audio_idiomas() primeiro para este idioma.", lang,
                )
                continue

            logger.info("── Whisper: transcrevendo %s (idioma: %s)", audio_local.name, lang)
            resultado_whisper = model.transcribe(str(audio_local), language=lang)

            legendas: list[Legenda] = []
            for seg in resultado_whisper.get("segments", []):
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
                logger.warning("   ⚠️  [%s] Whisper não retornou texto — pulando", lang)
                continue

            destino = Path(self._cfg.nome_srt_whisper(lang))
            salvar_srt(legendas, destino)
            self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")
            resultados[lang] = destino
            logger.info("   ✅ [%s] %s (%d blocos)", lang.upper(), destino.name, len(legendas))

        self._cp.salvar("audio_idiomas_transcritos", {"idiomas": list(resultados.keys())})
        return resultados

    def baixar_audio_e_transcrever(
        self, url: str, idiomas: list[str], modelo: str = "small"
    ) -> dict[str, Path]:
        """Atalho que combina baixar_audio_idiomas() + transcrever_audio_idiomas()
        em uma única chamada (mantido por compatibilidade — prefira as duas
        funções separadas quando quiser rodar cada etapa isoladamente)."""
        self.baixar_audio_idiomas(url, idiomas)
        return self.transcrever_audio_idiomas(idiomas, modelo=modelo)

    # ── Estágio 2: redistribuição (caption-multilang-generate.ipynb) ──────────

    def carregar_legenda_mestre(self) -> list[Legenda]:
        """Carrega a legenda mestre do Drive — sempre a versão mais recente."""
        nome    = self._cfg.nome_legenda_mestre
        destino = Path(nome)
        self._drive.download(self._cfg.pasta_oracao, nome, destino)
        if not destino.exists():
            raise PipelineError(
                f"Legenda mestre não encontrada no Drive: {self._cfg.pasta_oracao / nome}. "
                f"Rode o caption-single-generate.ipynb primeiro (ou confira NOME_LEGENDA_MESTRE)."
            )
        legendas = ler_srt(destino)
        if not legendas:
            raise PipelineError(f"Legenda mestre encontrada mas vazia: {destino}")
        logger.info("── Legenda mestre carregada: %s (%d blocos)", destino.name, len(legendas))
        return legendas

    def redistribuir_idiomas(self, idiomas: list[str]) -> dict[str, list[Legenda]]:
        """
        Para cada idioma: carrega o texto bruto (YouTube ou Whisper, conforme
        config.fonte_texto), pede à IA para redistribuir nos mesmos blocos da
        legenda mestre, e salva o SRT final ({NOME}_{lang}.srt).

        Sempre salva algum resultado por idioma bem-sucedido — se a IA
        retornar um número de partes diferente do esperado, ajusta
        automaticamente em vez de descartar (ver ajustar_para_n_partes).
        """
        if self._groq is None:
            raise PipelineError(
                "GroqClient não configurado — construa o pipeline com "
                "LanguageCaptionsPipeline(config, groq_client=...)."
            )

        legendas_mestre  = self.carregar_legenda_mestre()
        n                = len(legendas_mestre)
        textos_referencia = [leg.texto for leg in legendas_mestre]

        resultado: dict[str, list[Legenda]] = {}
        for lang in idiomas:
            fonte = self._cfg.fonte_texto(lang)
            nome_bruto = self._cfg.nome_srt_yt(lang) if fonte == "yt" else self._cfg.nome_srt_whisper(lang)
            bruto_local = Path(nome_bruto)
            self._drive.download(self._cfg.pasta_oracao, nome_bruto, bruto_local)

            if not bruto_local.exists():
                logger.warning(
                    "   ⚠️  [%s] Fonte bruta '%s' não encontrada no Drive — pulando "
                    "(rode caption-multilang-sources-gather.ipynb primeiro, ou ajuste FONTE_TEXTO_IDIOMA)",
                    lang, nome_bruto,
                )
                continue

            legendas_brutas = ler_srt(bruto_local)
            if not legendas_brutas:
                logger.warning("   ⚠️  [%s] Fonte bruta '%s' vazia — pulando", lang, nome_bruto)
                continue

            texto = extrair_texto_unico(legendas_brutas) if fonte == "yt" else texto_corrido(legendas_brutas)

            try:
                partes = self._groq.redistribuir_texto(texto, textos_referencia, lang)
            except GroqError as exc:
                logger.warning("   ❌ [%s] IA falhou (%s) — pulando", lang, exc)
                continue

            partes, houve_ajuste = ajustar_para_n_partes(partes, n)
            if houve_ajuste:
                logger.warning(
                    "   ⚠️  [%s] IA retornou número diferente de %d partes — ajustado "
                    "automaticamente. Revise o resultado com atenção.",
                    lang, n,
                )

            # A contagem estar certa não quer dizer que o conteúdo esteja.
            for _problema in conferir_redistribuicao(partes):
                logger.warning("   🚩 [%s] %s", lang, _problema)

            legendas_final = [
                Legenda(id=i + 1, inicio_ms=leg_m.inicio_ms, fim_ms=leg_m.fim_ms, texto=texto_parte)
                for i, (leg_m, texto_parte) in enumerate(zip(legendas_mestre, partes))
            ]

            destino = Path(self._cfg.nome_srt(lang))
            salvar_srt(legendas_final, destino)
            self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")
            resultado[lang] = legendas_final
            logger.info(
                "   ✅ [%s] %s (%d blocos, fonte=%s)",
                lang.upper(), destino.name, len(legendas_final), fonte,
            )

        self._cp.salvar("srt_traduzidos", {"idiomas": list(resultado.keys())})
        return resultado

    # ── Estágio 3: queima (caption-multilang-burn.ipynb) ───────────────────────

    def carregar_idiomas_finais(self, idiomas: list[str]) -> dict[str, list[Legenda]]:
        """Carrega, do Drive, o SRT final de cada idioma — sempre a versão
        mais recente (pode já estar corrigida manualmente).

        Regra do idioma mestre: se um dos `idiomas` pedidos for o próprio
        IDIOMA_MESTRE (ex: "en"), usa config.nome_legenda_mestre em vez de
        config.nome_srt(lang) — a legenda mestre JÁ É a legenda desse
        idioma (mesmo texto, mesmos tempos), não precisa de nenhuma cópia
        manual duplicada com outro nome só para "entrar" na queima.
        """
        resultado: dict[str, list[Legenda]] = {}
        for lang in idiomas:
            if lang == self._cfg.IDIOMA_MESTRE:
                nome = self._cfg.nome_legenda_mestre
            else:
                nome = self._cfg.nome_srt(lang)
            destino = Path(nome)
            self._drive.download(self._cfg.pasta_oracao, nome, destino)
            if not destino.exists():
                logger.warning("   ⚠️  [%s] %s não encontrado no Drive — pulando", lang, nome)
                continue
            legendas = ler_srt(destino)
            if not legendas:
                logger.warning("   ⚠️  [%s] %s vazio — pulando", lang, nome)
                continue
            resultado[lang] = legendas
            logger.info("   ✅ [%s] %s (%d blocos)", lang.upper(), nome, len(legendas))
        return resultado

    def gerar_legenda_versiculo(self, texto_com_versiculos: str) -> Path:
        """
        Gera o SRT do indicador de livro:versículo COMBINANDO TODOS OS
        IDIOMAS — alinha o texto fornecido (com números de versículo
        isolados no meio do fluxo, ex: "1 Now when Jesus... 2 Where is
        he...") contra a legenda mestre, e salva como
        config.nome_srt_versiculo_multilingue no Drive.

        As abreviações do livro (config.ABREVIACOES_LIVRO, uma por idioma)
        e o capítulo (config.CAPITULO) definem o texto de cada bloco —
        ex: "Matt/Mt/마 2:4" — combinando as abreviações únicas na ordem
        configurada, trocando só o número do versículo. Faz sentido aqui
        porque já tem vários idiomas empilhados na tela ao mesmo tempo
        (pro vídeo de legenda única, ver caption_pipeline.py -- só 1
        idioma, usa nome_srt_versiculo sem a combinação).
        """
        legendas_mestre = self.carregar_legenda_mestre()
        tempos = alinhar_versiculos(texto_com_versiculos, legendas_mestre)
        if not tempos:
            raise PipelineError(
                "Nenhum versículo encontrado no texto fornecido — confira se os "
                "números de versículo aparecem isolados por espaço no texto."
            )

        fim_video_ms = legendas_mestre[-1].fim_ms
        abreviacoes = list(self._cfg.ABREVIACOES_LIVRO.values())
        legendas_versiculo = gerar_legendas_versiculo(tempos, self._cfg.CAPITULO, abreviacoes, fim_video_ms)

        destino = Path(self._cfg.nome_srt_versiculo_multilingue)
        salvar_srt(legendas_versiculo, destino)
        self._drive.upload(destino, self._cfg.pasta_oracao, "text/plain")
        self._cp.salvar("legenda_versiculo_gerada", {
            "arquivo": str(destino), "total_versiculos": len(legendas_versiculo),
        })
        logger.info("✅ Legenda de versículo: %s (%d versículos)", destino.name, len(legendas_versiculo))
        return destino

    def queimar_idiomas(self, legendas_idiomas: dict[str, list[Legenda]], incluir_versiculo: bool = False) -> Path:
        """Queima os idiomas (modo simples — 1 cor por idioma, sem
        classificação morfológica) empilhados no vídeo base.

        Se incluir_versiculo=True, também queima o indicador de
        livro:versículo (config.nome_srt_versiculo_multilingue, gerado antes
        via gerar_legenda_versiculo()) no canto superior esquerdo — camada
        separada das legendas empilhadas, no mesmo passe de codificação.
        """
        if not legendas_idiomas:
            raise PipelineError("Nenhum idioma carregado para queimar.")

        video_base = Path(self._cfg.NOME_VIDEO_BASE)
        self._drive.download_se_ausente(self._cfg.pasta_oracao, self._cfg.NOME_VIDEO_BASE, video_base)
        if not video_base.exists():
            raise PipelineError(f"Vídeo base não encontrado: {video_base}. Rode um dos notebooks video-base-*.ipynb primeiro.")

        # gerar_ass() usa .palavras para decidir o "modo idioma" (1 cor por
        # idioma) — sem isso, cairia no modo texto simples sem cor.
        for lang, legendas in legendas_idiomas.items():
            for leg in legendas:
                leg.palavras = [Palavra(texto=w, classe=lang) for w in leg.texto.split()]

        ass_paths: list[Path] = [gerar_ass(
            legendas_idiomas, self._cfg,
            caminho_saida=Path(f"legendas_idiomas_{self._cfg.NOME_ORACAO}.ass"),
        )]

        if incluir_versiculo:
            nome_versiculo = self._cfg.nome_srt_versiculo_multilingue
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

        video_final = Path(self._cfg.NOME_VIDEO_FINAL_IDIOMAS)
        queimar_legendas_ass(video_base, ass_paths, video_final)

        self._drive.upload(video_final, self._cfg.pasta_oracao, "video/mp4")
        self._cp.salvar("legendas_idiomas_queimadas", {
            "arquivo": str(video_final),
            "idiomas": list(legendas_idiomas.keys()),
            "com_versiculo": incluir_versiculo,
        })
        logger.info(
            "✅ Vídeo final (idiomas): %s (%.2f MB)",
            video_final.name, video_final.stat().st_size / 1_048_576,
        )
        return video_final
