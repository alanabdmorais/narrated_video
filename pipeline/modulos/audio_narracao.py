# -*- coding: utf-8 -*-
"""
audio_narracao.py — onde procurar a narração de um capítulo, num lugar só.

O áudio de um vídeo pode estar em três lugares, e a ordem importa:

    1. o disco da VM        já trazido nesta sessão
    2. videos/<nome>/       gravação própria, ou o capítulo que você subiu
    3. assets/biblia_audio/ o estoque do biblia-audio-baixar (1.189 capítulos)

E o nome varia: a pasta do vídeo usa `<nome>_audio.wav`, o estoque usa
`<nome>.mp3`.

Este módulo existe porque a busca estava em UM lugar (`video_pipeline.
gerar_audio`) e os outros quatro consumidores olhavam só a pasta do vídeo.
O resultado foi o `caption-single-generate` parar com "Áudio não encontrado"
num capítulo cujo áudio estava no Drive o tempo todo, dois diretórios ao lado,
e mandar rodar de novo um notebook que já tinha rodado.

Regra repetida é regra que vai divergir; regra em um lugar e quatro cópias
antigas é pior, porque a versão certa existe e mesmo assim não é usada.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# O que o FFmpeg lê e o projeto aceita, na ordem em que se prefere.
EXTENSOES = (".wav", ".mp3", ".m4a", ".ogg", ".flac")


def candidatos(config) -> list[tuple[Path, str]]:
    """Todos os caminhos onde a narração pode estar, na ordem de prioridade."""
    origens = (
        (config.pasta_oracao, "pasta do vídeo"),
        (config.pasta_base_drive / "assets" / "biblia_audio", "estoque da Bíblia"),
    )
    achados = []
    for pasta, rotulo in origens:
        for base in (f"{config.NOME_ORACAO}_audio", config.NOME_ORACAO):
            for ext in EXTENSOES:
                achados.append((pasta / f"{base}{ext}", rotulo))
    return achados


def procurar(config) -> tuple[Path, str] | None:
    """O primeiro áudio que existe no Drive, e de onde ele veio."""
    for caminho, rotulo in candidatos(config):
        if caminho.exists():
            return caminho, rotulo
    return None


def trazer(config, destino: Path | None = None) -> str | None:
    """Traz a narração pra VM, venha de onde vier.

    Devolve o rótulo da origem (`"pasta do vídeo"` / `"estoque da Bíblia"`),
    ou `None` se não achou nada em lugar nenhum — e aí quem chamou decide:
    o `gerar_audio` gera com Edge TTS, os outros param com erro.

    Converte o que não for `.wav`: o pipeline inteiro espera esse formato, e
    gravar um mp3 com nome de wav é uma dívida que vence longe daqui.
    """
    destino = Path(destino or config.NOME_AUDIO)
    if destino.exists():
        return "já estava na VM"

    achado = procurar(config)
    if achado is None:
        return None

    origem, rotulo = achado
    logger.info("── Narração: %s, do %s", origem.name, rotulo)
    if origem.suffix.lower() == ".wav":
        shutil.copy2(origem, destino)
    else:
        from ffmpeg_utils import converter_para_wav
        converter_para_wav(origem, destino)
    return rotulo


def erro_nao_achei(config) -> str:
    """A mensagem de quem procurou em tudo e não achou.

    Lista os lugares de verdade. "Rode o video-base primeiro" sozinho manda
    repetir um passo que pode já ter sido feito — e foi o que aconteceu.
    """
    linhas = [f"Narração de {config.NOME_ORACAO} não encontrada. Procurei em:"]
    vistos = []
    for caminho, rotulo in candidatos(config):
        if caminho.parent not in vistos:
            vistos.append(caminho.parent)
            linhas.append(f"  · {caminho.parent}  ({rotulo})")
    linhas.append(f"  nomes: {config.NOME_ORACAO}[_audio]{{{ ','.join(EXTENSOES) }}}")
    linhas.append("")
    linhas.append("Saídas, da mais fácil pra menos:")
    linhas.append("  1. rode o biblia-audio-baixar uma vez — traz os 1.189 capítulos")
    linhas.append(f"  2. suba o arquivo à mão em {config.pasta_oracao}")
    linhas.append("  3. rode a célula de Narração de um video-base-*, que gera com Edge TTS")
    return "\n".join(linhas)
