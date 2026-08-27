# -*- coding: utf-8 -*-
"""
ffmpeg_utils.py — Operações FFmpeg e geração de subtítulos ASS.

A otimização crítica deste módulo é a função gerar_ass():
em vez de centenas de filtros drawtext (um por palavra), geramos
um único arquivo .ass por idioma e usamos -vf "ass=arquivo.ass".
Isso reduz o tempo de render em ~10×.

Funções principais:
    cortar_video(entrada, saida, duracao)
    concatenar_videos(lista, saida)
    adicionar_credito_e_logo(video, saida, credito, logo, tamanho)
    adicionar_audio(video, audio, saida)
    adicionar_trilha_fundo(video, musica, saida, volume)
    montar_trilha_sequencial(segmentos, saida) → Path
    adicionar_efeitos_pontuais(video, efeitos, saida)
    gerar_ass(legendas_por_idioma, config)     → Path   ← CRÍTICO
    queimar_legendas_ass(video, ass_path, saida)
    obter_duracao(arquivo)                     → float
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Optional

from config import PipelineConfig
from models import Legenda
from constants import CORES_HTML, TEXTO_PRETO, SIGLAS_IDIOMAS

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Erro nas operações do FFmpeg."""


# ── Helpers internos ──────────────────────────────────────────────────────────

def _run(cmd: list[str], descricao: str = "") -> subprocess.CompletedProcess:
    """Executa um comando FFmpeg e lança FFmpegError se falhar."""
    logger.debug("FFmpeg: %s", " ".join(cmd[:6]) + " ...")
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        stderr = resultado.stderr[-600:] if resultado.stderr else "(sem stderr)"
        raise FFmpegError(
            f"FFmpeg falhou ({descricao or cmd[1]}):\n{stderr}"
        )
    return resultado


def _escapar(texto: str) -> str:
    """
    Remove acentos e caracteres especiais para uso seguro em filtros FFmpeg.
    Necessário pois drawtext/ASS têm limitações de encoding.
    """
    sem_acento = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("ascii")
    # remove caracteres que quebram o filtro drawtext
    return sem_acento.replace("'", "").replace('"', "").replace(":", "").replace("\\", "")


def _ms_para_ass(ms: int) -> str:
    """Converte milissegundos para timestamp ASS (h:mm:ss.cc — centésimos)."""
    h  = ms // 3_600_000
    m  = (ms % 3_600_000) // 60_000
    s  = (ms % 60_000) // 1_000
    cc = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cc:02d}"


def _html_para_ass_cor(html_hex: str) -> str:
    """Converte #RRGGBB ou 0xRRGGBB para formato ASS &H00BBGGRR."""
    h = html_hex.replace("#", "").replace("0x", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


def _escapar_ass_texto(texto: str) -> str:
    """
    Prepara texto para uma linha de diálogo ASS SEM remover acentos.

    Diferente de `_escapar()` (usada no drawtext de créditos e no modo
    multi-idioma/palavra colorida), que remove acentos via normalização
    NFD — bom para texto ASCII simples, mas ruim para legendas em
    português/espanhol/francês, onde perder "é", "ã", "ç" etc. degrada a
    legenda de forma visível.

    ASS/libass lida bem com UTF-8 nativamente (o arquivo é salvo como
    utf-8-sig); o único cuidado real é escapar os caracteres que têm
    significado especial no formato: chaves (tags override) e quebras de
    linha reais (viram a tag \\N).
    """
    texto = texto.replace("{", "(").replace("}", ")")
    texto = texto.replace("\r\n", "\n").replace("\n", "\\N")
    return texto.strip()


def _cor_texto_ass(classe: str) -> str:
    """Retorna cor ASS do texto (preto ou branco) conforme o fundo."""
    if classe in TEXTO_PRETO:
        return "&H00000000"   # preto opaco
    return "&H00FFFFFF"       # branco opaco


# ── Operações básicas de vídeo ────────────────────────────────────────────────

def obter_duracao(arquivo: Path | str) -> float:
    """Retorna a duração do arquivo de mídia em segundos."""
    resultado = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(arquivo),
        ],
        capture_output=True, text=True,
    )
    try:
        return float(resultado.stdout.strip())
    except ValueError:
        return 0.0


def cortar_video(
    entrada: Path | str,
    saida:   Path | str,
    duracao: float,
) -> Path:
    """Corta os primeiros `duracao` segundos do vídeo, com duração exata.

    Re-codifica (não usa stream copy): com -c copy, o corte só pode acontecer
    em keyframes, então "5 segundos" pode virar 2s ou 9s dependendo de onde
    ficam os keyframes do vídeo de origem — cada clipe do Pixabay tem um
    espaçamento de keyframe diferente. Re-codificar garante duração exata.
    """
    saida = Path(saida)
    _run(
        ["ffmpeg", "-y", "-i", str(entrada),
         "-t", f"{duracao:.3f}",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
         "-c:a", "aac",
         str(saida)],
        "cortar_video",
    )
    logger.debug("cortar_video: %s → %s (%.2fs)", Path(entrada).name, saida.name, duracao)
    return saida


def concatenar_videos(lista_arquivos: list[Path | str], saida: Path | str) -> Path:
    """Concatena vídeos usando o demuxer concat do FFmpeg (stream copy)."""
    saida     = Path(saida)
    lista_txt = saida.with_suffix(".txt")

    with open(lista_txt, "w", encoding="utf-8") as fh:
        for arq in lista_arquivos:
            fh.write(f"file '{arq}'\n")

    _run(
        ["ffmpeg", "-y",
         "-f", "concat", "-safe", "0", "-i", str(lista_txt),
         "-c", "copy", str(saida)],
        "concatenar_videos",
    )
    lista_txt.unlink(missing_ok=True)
    logger.info("concatenar_videos: %d clipes → %s", len(lista_arquivos), saida.name)
    return saida


def imagem_para_clipe(
    imagem_entrada: Path | str,
    saida:          Path | str,
    duracao_seg:    float,
    largura:        int = 1280,
    altura:         int = 720,
    fps:            int = 25,
) -> Path:
    """
    Converte uma imagem estática num clipe de vídeo de `duracao_seg`
    segundos (foto parada, sem movimento — Ken Burns não aplicado de
    propósito, mantém o fundo o mais neutro possível para não competir
    com a leitura das legendas).

    Já sai padronizado (resolução/fps/pixel format) na mesma medida que
    adicionar_credito_e_logo() espera — passe a saída deste função direto
    pra ela, igual se faz com um clipe de vídeo cortado do Pixabay.
    """
    saida = Path(saida)
    filtro = (
        f"scale={largura}:{altura}:force_original_aspect_ratio=decrease,"
        f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={fps},format=yuv420p"
    )
    _run(
        ["ffmpeg", "-y",
         "-loop", "1", "-i", str(imagem_entrada),
         "-t", str(duracao_seg),
         "-vf", filtro,
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
         "-pix_fmt", "yuv420p",
         str(saida)],
        "imagem_para_clipe",
    )
    logger.info("imagem_para_clipe: %s → %s (%.1fs)", Path(imagem_entrada).name, saida.name, duracao_seg)
    return saida


def adicionar_credito_e_logo(
    video_entrada: Path | str,
    saida:         Path | str,
    texto_credito: str,
    logo_path:     Optional[Path | str],
    tamanho_logo:  int = 80,
    largura:       int = 1280,
    altura:        int = 720,
    fps:           int = 25,
) -> Path:
    """
    Adiciona crédito de texto (canto inferior esquerdo) e logo (canto inferior direito).

    CRÍTICO: também padroniza TODO clipe para a mesma resolução/fps/pixel
    format (via `largura`/`altura`/`fps`). Clipes do Pixabay vêm de autores
    diferentes, cada um com sua própria resolução e taxa de quadros — se
    forem concatenados sem padronizar, o FFmpeg corrompe silenciosamente a
    duração do vídeo final (sem erro, só um aviso de "Non-monotonic DTS" que
    passa despercebido). Padronizar aqui, uma vez por clipe, resolve isso na
    raiz e deixa a concatenação depois (stream copy) segura e exata.
    """
    saida         = Path(saida)
    credito_safe  = _escapar(texto_credito)

    filtro_base = (
        f"scale={largura}:{altura}:force_original_aspect_ratio=decrease,"
        f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={fps},"
        f"drawtext=text='{credito_safe}':"
        f"fontcolor=white:fontsize=16:"
        f"x=10:y=h-30:"
        f"box=1:boxcolor=black@0.5:boxborderw=5"
    )

    if logo_path and Path(logo_path).exists():
        filtro_combo = (
            f"[0:v]{filtro_base}[tmp];"
            f"[1:v]scale={tamanho_logo}:-1[logo];"
            f"[tmp][logo]overlay=W-w-0:H-h-0"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_entrada),
            "-i", str(logo_path),
            "-filter_complex", filtro_combo,
            "-r", str(fps), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-c:v", "libx264",
            "-preset", "ultrafast", "-crf", "23",
            str(saida),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_entrada),
            "-vf", filtro_base,
            "-r", str(fps), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-c:v", "libx264",
            "-preset", "ultrafast", "-crf", "23",
            str(saida),
        ]

    _run(cmd, "credito_e_logo")
    logger.info("adicionar_credito_e_logo: %s (%dx%d @ %dfps)", saida.name, largura, altura, fps)
    return saida


def adicionar_audio(
    video_entrada: Path | str,
    audio_entrada: Path | str,
    saida:         Path | str,
) -> Path:
    """Adiciona faixa de áudio ao vídeo (substitui qualquer áudio existente).

    Corta o resultado na duração EXATA do áudio (-t explícito), além do
    -shortest — sozinho, o -shortest se mostrou pouco confiável com -c:v copy
    em alguns casos, deixando sobrar vídeo mudo depois do fim da narração.

    🔒 Trava de segurança: se o VÍDEO for mais curto que o ÁUDIO, o -shortest
    abaixo cortaria a narração no meio, silenciosamente, no ponto em que o
    vídeo acaba. Em vez disso, falha aqui com uma mensagem clara — melhor
    parar e avisar do que entregar um vídeo com a narração cortada sem
    ninguém perceber.
    """
    saida = Path(saida)
    duracao_audio = obter_duracao(Path(audio_entrada))
    duracao_video = obter_duracao(Path(video_entrada))

    if duracao_video < duracao_audio - 0.5:
        raise FFmpegError(
            f"adicionar_audio: o vídeo ({duracao_video:.1f}s) é mais curto que o "
            f"áudio ({duracao_audio:.1f}s) — a narração seria cortada no meio pelo "
            f"-shortest. Isso normalmente significa que 'clipes_cortados/' tem "
            f"clipes insuficientes ou desatualizados (de uma oração/sessão anterior "
            f"— essa pasta não é isolada por oração). Rode a limpeza seletiva "
            f"(opção 7 — Reset Inteligente) e refaça a Fase 6 (clipes) antes de "
            f"tentar de novo."
        )

    _run(
        ["ffmpeg", "-y",
         "-i", str(video_entrada), "-i", str(audio_entrada),
         "-c:v", "copy", "-c:a", "aac",
         "-map", "0:v:0", "-map", "1:a:0",
         "-t", f"{duracao_audio:.3f}",
         "-shortest", "-af", "aresample=async=1",
         str(saida)],
        "adicionar_audio",
    )
    logger.info("adicionar_audio: %s + %s (%.1fs) → %s",
                Path(video_entrada).name, Path(audio_entrada).name, duracao_audio, saida.name)
    return saida


def adicionar_trilha_fundo(
    video_entrada:   Path | str,
    musica:          Path | str,
    saida:           Path | str,
    volume:          float = 0.25,
    volume_narracao: float = 1.0,
) -> Path:
    """
    Mistura a trilha de fundo à narração já presente no vídeo.
    A narração e a música são ajustadas de volume independentemente
    (`volume_narracao` e `volume`), e a música é recortada/repetida para
    cobrir a duração do vídeo.

    Corta o resultado na duração EXATA do vídeo de entrada (-t explícito),
    além do -shortest — mesma proteção usada em adicionar_audio.
    """
    saida = Path(saida)
    duracao_video = obter_duracao(Path(video_entrada))
    filtro = (
        f"[0:a]volume={volume_narracao}[voz];"
        f"[1:a]volume={volume},aloop=loop=-1:size=2e+09[bg];"
        f"[voz][bg]amix=inputs=2:duration=first[a]"
    )
    _run(
        ["ffmpeg", "-y",
         "-i", str(video_entrada), "-i", str(musica),
         "-filter_complex", filtro,
         "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{duracao_video:.3f}",
         "-shortest", str(saida)],
        "trilha_fundo",
    )
    logger.info("adicionar_trilha_fundo: narração=%.0f%% trilha=%.0f%% (%.1fs) → %s",
                volume_narracao * 100, volume * 100, duracao_video, saida.name)
    return saida


def montar_trilha_sequencial(
    segmentos: list[dict],
    saida: Path | str,
) -> Path:
    """
    Concatena vários trechos de trilha (cada um trimado/looped pra uma
    duração exata) numa única faixa de áudio contínua -- pensada como
    entrada de adicionar_trilha_fundo() no lugar de uma trilha única (ver
    trilha_pipeline.calcular_segmentos_trilha, que monta o plano de
    segmentos casando o clima de cada trecho de evento com um pool de
    trilhas candidatas).

    `segmentos`: lista de dicts com pelo menos "duracao_seg" (float) e
    "arquivo" (Path do áudio já baixado, ou None). Segmento com
    "arquivo": None vira SILÊNCIO daquela duração (acontece quando
    nenhuma trilha do pool bateu o clima do evento naquele trecho).

    Cada pedaço é re-codificado pro MESMO formato (PCM 44.1kHz estéreo,
    sem compressão) antes de concatenar -- os arquivos de origem vêm de
    fontes bem diferentes (Freesound, YouTube Audio Library, Pixabay),
    cada um com seu próprio sample rate/canais/codec; concatenar sem
    padronizar quebra o demuxer concat do FFmpeg (exige parâmetros
    idênticos), igual ao que já acontecia com os clipes de vídeo antes
    da padronização em adicionar_credito_e_logo().

    ⚠️ `saida` deve ter extensão `.wav` -- o passo final regrava
    explicitamente em PCM (não faz stream copy cego dos pedaços em AAC
    pra dentro do container de saída, o que gerava um arquivo com
    cabeçalho válido mas ÁUDIO CORROMPIDO -- AAC dentro de um container
    WAV via `-c copy` não é válido, e o FFmpeg não avisa na hora de
    gravar, só quando alguém tenta decodificar depois).
    """
    saida = Path(saida)
    pasta_temp = saida.parent / f"_trilha_pedacos_{saida.stem}"
    pasta_temp.mkdir(parents=True, exist_ok=True)

    pedacos: list[Path] = []
    for i, seg in enumerate(segmentos):
        pedaco = pasta_temp / f"pedaco_{i:03d}.wav"
        duracao = max(0.5, float(seg["duracao_seg"]))
        arquivo = seg.get("arquivo")

        if arquivo and Path(arquivo).exists():
            _run(
                ["ffmpeg", "-y",
                 "-stream_loop", "-1", "-i", str(arquivo),
                 "-t", f"{duracao:.3f}",
                 "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                 str(pedaco)],
                "montar_trilha_sequencial (trecho)",
            )
        else:
            _run(
                ["ffmpeg", "-y",
                 "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", f"{duracao:.3f}",
                 "-c:a", "pcm_s16le",
                 str(pedaco)],
                "montar_trilha_sequencial (silêncio)",
            )
        pedacos.append(pedaco)

    lista_txt = pasta_temp / "lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as fh:
        for p in pedacos:
            fh.write(f"file '{p.resolve()}'\n")

    # Regrava explicitamente em PCM (não usa "-c copy") -- os pedaços já
    # são todos PCM idênticos, então stream copy TAMBÉM funcionaria aqui,
    # mas ser explícito garante que `saida` sempre sai com áudio válido
    # de verdade, mesmo que o formato dos pedaços mude no futuro.
    _run(
        ["ffmpeg", "-y",
         "-f", "concat", "-safe", "0", "-i", str(lista_txt),
         "-c:a", "pcm_s16le", str(saida)],
        "montar_trilha_sequencial (concat)",
    )

    shutil.rmtree(pasta_temp, ignore_errors=True)
    logger.info("montar_trilha_sequencial: %d segmento(s) → %s", len(segmentos), saida.name)
    return saida


def adicionar_efeitos_pontuais(
    video_entrada: Path | str,
    efeitos: list[dict],
    saida: Path | str,
    volume_efeito: float = 0.8,
) -> Path:
    """
    Sobrepõe efeitos sonoros pontuais (curtos, tipo porta/trovão/cavalo)
    no áudio já existente do vídeo (narração + trilha, se houver) -- cada
    efeito entra no tempo exato do versículo que casou com ele (ver
    trilha_pipeline.calcular_efeitos_pontuais), sem cortar nem repetir o
    resto do áudio.

    `efeitos`: lista de dicts com "inicio_ms" (int) e "arquivo" (Path do
    áudio do efeito já baixado). Efeito sem "arquivo" (download falhou)
    é ignorado silenciosamente.

    Usa `amix` com `normalize=0` (soma direta, sem dividir o volume pelo
    número de entradas) -- com o normalize padrão do FFmpeg, cada efeito
    novo abafaria um pouco mais a narração/trilha, o que não é o efeito
    pretendido aqui (a narração deve continuar no mesmo volume; é o
    efeito que entra por cima, já ajustado por `volume_efeito`).

    Lista de efeitos vazia (ou nenhum com "arquivo" válido) devolve o
    vídeo de entrada copiado pra `saida`, sem re-codificar.
    """
    saida = Path(saida)
    validos = [e for e in efeitos if e.get("arquivo") and Path(e["arquivo"]).exists()]

    if not validos:
        shutil.copy2(video_entrada, saida)
        logger.info("adicionar_efeitos_pontuais: nenhum efeito válido -- vídeo copiado sem alteração")
        return saida

    entradas = ["-i", str(video_entrada)]
    for efeito in validos:
        entradas += ["-i", str(efeito["arquivo"])]

    partes_filtro = []
    rotulos_efeito = []
    for i, efeito in enumerate(validos, start=1):
        delay_ms = max(0, int(efeito["inicio_ms"]))
        rotulo = f"e{i}"
        partes_filtro.append(f"[{i}:a]adelay={delay_ms}|{delay_ms},volume={volume_efeito}[{rotulo}]")
        rotulos_efeito.append(f"[{rotulo}]")

    entradas_mix = "[0:a]" + "".join(rotulos_efeito)
    partes_filtro.append(
        f"{entradas_mix}amix=inputs={1 + len(validos)}:duration=first:dropout_transition=0:normalize=0[a]"
    )
    filtro = ";".join(partes_filtro)

    _run(
        ["ffmpeg", "-y", *entradas,
         "-filter_complex", filtro,
         "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac",
         str(saida)],
        "adicionar_efeitos_pontuais",
    )
    logger.info("adicionar_efeitos_pontuais: %d efeito(s) sobreposto(s) → %s", len(validos), saida.name)
    return saida


def ajustar_velocidade_audio(
    audio_entrada: Path | str,
    saida:         Path | str,
    velocidade:    float = 1.0,
) -> Path:
    """
    Ajusta a velocidade do áudio sem alterar o tom da voz (filtro atempo).

    `velocidade` < 1.0 deixa o áudio mais lento (ex: 0.9 = 10% mais devagar);
    > 1.0 deixa mais rápido. O filtro atempo do FFmpeg só aceita valores entre
    0.5 e 2.0 por vez — fora desse intervalo, encadeia o filtro automaticamente.
    """
    saida = Path(saida)

    # Encadeia o filtro atempo em passos de até 2x/0.5x para cobrir qualquer valor
    passos = []
    restante = velocidade
    while restante < 0.5 or restante > 2.0:
        passo = 0.5 if restante < 0.5 else 2.0
        passos.append(passo)
        restante /= passo
    passos.append(restante)
    filtro = ",".join(f"atempo={p}" for p in passos)

    _run(
        ["ffmpeg", "-y", "-i", str(audio_entrada), "-filter:a", filtro, str(saida)],
        "ajustar_velocidade",
    )
    logger.info("ajustar_velocidade_audio: %.2fx → %s", velocidade, saida.name)
    return saida


# ── Geração de ASS ─────────────────────────────────────────────────────────────

# Cabeçalho de um arquivo .ass com uma única seção de estilos
_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{tamanho_fonte},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Template de uma linha de diálogo ASS para palavra colorida
# Usa tags override: {\1c&HColor&\3c&HBorderColor&} por palavra
_LINHA_DIALOGO = "Dialogue: 0,{inicio},{fim},Default,,0,0,0,,{texto}\n"

# Header ASS para legenda única (Single Subtitle) — 1 faixa de texto simples,
# branco com contorno preto, centralizada NO MEIO da tela (vertical e
# horizontalmente). Separado de _ASS_HEADER (usado no modo multi-idioma/
# palavra colorida) porque aqui o texto é a
# ÚNICA coisa na tela, então usa fonte maior e contorno mais grosso.
_ASS_HEADER_LEGENDA_UNICA = """\
[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{tamanho_fonte},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{contorno},0,5,20,20,{margem_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def gerar_ass(
    legendas_por_idioma: dict[str, list[Legenda]],
    config: PipelineConfig,
    caminho_saida: Optional[Path | str] = None,
) -> Path:
    """
    Gera um único arquivo .ass com as legendas coloridas de TODOS os idiomas.

    Cada palavra recebe um box colorido usando tags override ASS:
      {\\1c&HCOR&\\bord4\\shad0\\p0} palavra {\\r}

    Todos os 4 idiomas ficam em posições Y diferentes no mesmo arquivo,
    eliminando a necessidade de múltiplos passes de render.

    Args:
        legendas_por_idioma: dict { "pt": [...], "en": [...], ... }
        config:              PipelineConfig com posições, cores, etc.
        caminho_saida:       Caminho do .ass (default: legendas_{NOME}.ass)

    Returns:
        Path do arquivo .ass gerado.
    """
    if caminho_saida is None:
        caminho_saida = Path(f"legendas_{config.NOME_ORACAO}.ass")
    else:
        caminho_saida = Path(caminho_saida)

    linhas: list[str] = [
        _ASS_HEADER.format(
            largura=config.LARGURA_TELA,
            altura=config.ALTURA_TELA,
            tamanho_fonte=config.TAMANHO_FONTE_TAG,
        )
    ]

    # ── siglas de idioma (sempre visíveis, sem box colorido) ──────────────────
    for lang, legendas in legendas_por_idioma.items():
        if not legendas:
            continue
        sigla   = config.SIGLAS_IDIOMAS.get(lang, lang.upper())
        y_sigla = config.POS_SIGLA_Y.get(lang, 50)
        fim_total_ms = max(leg.fim_ms for leg in legendas) + 500

        # posição Y em ASS: MarginV controla distância da borda inferior
        # com Alignment=2 (centro-baixo), MarginV é medido de baixo para cima
        margem_v = config.ALTURA_TELA - y_sigla

        inicio_ass = _ms_para_ass(0)
        fim_ass    = _ms_para_ass(fim_total_ms)
        texto_ass  = (
            f"{{\\an2\\pos({config.LARGURA_TELA // 2},{y_sigla})"
            f"\\1c&H808080&\\bord4\\shad0\\fs{config.TAMANHO_FONTE_SIGLA}}}"
            f"{sigla}"
        )
        linhas.append(_LINHA_DIALOGO.format(
            inicio=inicio_ass, fim=fim_ass, texto=texto_ass
        ))

    # ── palavras coloridas ────────────────────────────────────────────────────
    for lang, legendas in legendas_por_idioma.items():
        y_base = config.POS_SIGLA_Y.get(lang, 100)
        # calcula Y das palavras: abaixo da sigla
        y_palavras = config.POSICOES_Y.get(lang, y_base + 35)

        for leg in legendas:
            if not leg.palavras:
                # legenda sem classificação: renderiza texto plano
                _adicionar_linha_simples(linhas, leg, y_palavras, config, lang)
                continue

            _adicionar_linha_colorida(linhas, leg, y_palavras, config, lang)

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    logger.info("gerar_ass: %s (%d linhas)", caminho_saida.name, len(linhas))
    return caminho_saida


def _adicionar_linha_simples(
    linhas: list[str],
    leg: Legenda,
    y: int,
    config: PipelineConfig,
    lang: str = "",
) -> None:
    """Adiciona linha ASS com o texto da legenda sem colorização por palavra."""
    texto_safe = _escapar_ass_texto(leg.texto)
    _fonte     = config.fonte_cjk(lang)
    fonte_tag  = f"\\fn{_fonte}" if _fonte else ""
    texto_ass  = (
        f"{{\\an2\\pos({config.LARGURA_TELA // 2},{y})"
        f"\\1c&H00FFFFFF&\\bord4\\shad0{fonte_tag}}}"
        f"{texto_safe}"
    )
    linhas.append(_LINHA_DIALOGO.format(
        inicio=_ms_para_ass(leg.inicio_ms),
        fim   =_ms_para_ass(leg.fim_ms),
        texto =texto_ass,
    ))


def _adicionar_linha_colorida(
    linhas: list[str],
    leg: Legenda,
    y: int,
    config: PipelineConfig,
    lang: str = "",
) -> None:
    """
    Adiciona linha ASS com cada palavra em sua cor morfológica.

    Usa a tag \\pos() para centralizar o bloco inteiro,
    e tags override {\\1c} por palavra para mudar a cor individualmente.

    Estratégia: a linha inteira fica em uma única entrada de diálogo ASS,
    com as tags de cor inline — muito mais eficiente que uma entrada por palavra.
    """
    # ── Detectar modo idioma (1 cor por idioma) ou morfológico ──────────────
    # O conjunto de idiomas vem de CORES_IDIOMAS (é de lá que a cor sai logo
    # abaixo) em vez de uma lista fixa -- assim um idioma novo configurado
    # ali já entra no modo idioma sozinho. Com uma lista fixa, o idioma que
    # faltasse nela caía no modo morfológico e saía cinza (#666666), que era
    # exatamente o que acontecia com o chinês.
    _IDIOMAS = set(getattr(config, 'CORES_IDIOMAS', None) or {"pt", "en", "es", "fr", "ko"})
    classes = {p.classe for p in leg.palavras if p.texto.strip()}
    modo_idioma = bool(classes) and classes <= _IDIOMAS
    _fonte = config.fonte_cjk(lang)
    fonte_tag = f"\\fn{_fonte}" if _fonte else ""

    partes: list[str] = []
    for palavra in leg.palavras:
        texto_safe = _escapar_ass_texto(palavra.texto)
        if not texto_safe:
            continue
        if modo_idioma:
            # Cor única por idioma — busca em CORES_IDIOMAS
            cores_id = getattr(config, 'CORES_IDIOMAS', {})
            cor_html = cores_id.get(palavra.classe, "#FFFFFF")
        else:
            # Cor morfológica normal
            cor_html = config.CORES_HTML.get(palavra.classe, "#666666")
        cor_fundo = _html_para_ass_cor(cor_html)
        # Texto preto para fundos claros
        r, g, b = int(cor_html[1:3],16), int(cor_html[3:5],16), int(cor_html[5:7],16)
        luminancia = 0.299*r + 0.587*g + 0.114*b
        cor_texto = "&H00000000" if luminancia > 128 else "&H00FFFFFF"

        # tag override ASS:
        # \1c  = cor primária (texto)
        # \3c  = cor de borda (usamos como "fundo" com borda larga)
        # \bord = largura da borda — aumentamos para simular box
        # \shad0 = sem sombra
        # \fn   = fonte (só p/ coreano — Arial não cobre bem o Hangul)
        partes.append(
            f"{{\\1c{cor_texto}\\3c{cor_fundo}\\bord{config.BOX_BORDER}\\shad0{fonte_tag}}}"
            f"{texto_safe} "
        )

    if not partes:
        _adicionar_linha_simples(linhas, leg, y, config, lang)
        return

    texto_combinado = "".join(partes).rstrip()
    texto_ass = (
        f"{{\\an2\\pos({config.LARGURA_TELA // 2},{y})"
        f"\\fs{config.TAMANHO_FONTE_TAG}}}"
        + texto_combinado
    )

    linhas.append(_LINHA_DIALOGO.format(
        inicio=_ms_para_ass(leg.inicio_ms),
        fim   =_ms_para_ass(leg.fim_ms),
        texto =texto_ass,
    ))


def gerar_ass_simples(
    legendas: list[Legenda],
    config: PipelineConfig,
    caminho_saida: Optional[Path | str] = None,
) -> Path:
    """
    Gera um .ass de legenda única — 1 faixa de texto simples, sem cor por
    palavra nem por idioma. Usado pelo notebook Single Subtitle (Burn).

    Args:
        legendas:      lista de Legenda (timestamps + texto) — normalmente
                        vinda de ler_srt() sobre o arquivo de config.nome_legenda_mestre.
        config:        PipelineConfig com resolução e estilo da legenda única.
        caminho_saida: caminho do .ass (default: legenda_unica_{NOME}.ass)

    Returns:
        Path do arquivo .ass gerado.
    """
    if caminho_saida is None:
        caminho_saida = Path(f"legenda_unica_{config.NOME_ORACAO}.ass")
    else:
        caminho_saida = Path(caminho_saida)

    linhas: list[str] = [
        _ASS_HEADER_LEGENDA_UNICA.format(
            largura=config.LARGURA_TELA,
            altura=config.ALTURA_TELA,
            tamanho_fonte=config.TAMANHO_FONTE_LEGENDA,
            contorno=config.CONTORNO_LEGENDA,
            margem_v=config.MARGEM_V_LEGENDA,
        )
    ]

    for leg in legendas:
        texto_safe = _escapar_ass_texto(leg.texto)
        if not texto_safe:
            continue
        linhas.append(_LINHA_DIALOGO.format(
            inicio=_ms_para_ass(leg.inicio_ms),
            fim=_ms_para_ass(leg.fim_ms),
            texto=texto_safe,
        ))

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    logger.info("gerar_ass_simples: %s (%d legendas)", caminho_saida.name, len(legendas))
    return caminho_saida


# ── Queima de legendas ASS ────────────────────────────────────────────────────

def _detectar_encoder_video() -> tuple[str, list[str]]:
    """
    Detecta se há aceleração de vídeo por GPU (NVENC, NVIDIA) disponível e
    usável — não basta o ffmpeg ter o codec compilado, precisa também ter
    uma GPU NVIDIA de verdade presente no runtime (ex: Colab com GPU T4
    ativada). Sem isso, volta para libx264 (CPU) normalmente.

    Retorna (nome_do_encoder, argumentos_de_qualidade_correspondentes).
    """
    try:
        encoders = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        tem_nvenc_compilado = "h264_nvenc" in encoders.stdout
    except Exception:
        tem_nvenc_compilado = False

    if tem_nvenc_compilado:
        try:
            gpu = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
            if gpu.returncode == 0:
                logger.info("🚀 GPU NVIDIA detectada — queima de legendas vai usar h264_nvenc")
                # -cq é o equivalente ao -crf do libx264 no NVENC (menor = melhor qualidade)
                return "h264_nvenc", ["-preset", "p4", "-cq", "23"]
        except Exception:
            pass

    logger.info(
        "── Nenhuma GPU NVIDIA disponível — queima de legendas vai usar libx264 (CPU, mais lento). "
        "No Colab: Ambiente de execução → Alterar tipo de ambiente de execução → GPU."
    )
    return "libx264", ["-preset", "medium", "-crf", "23"]


def gerar_ass_versiculo(
    legendas_versiculo: list[Legenda],
    config: PipelineConfig,
    caminho_saida: Optional[Path | str] = None,
) -> Path:
    """
    Gera o .ass do indicador de livro:versículo — texto pequeno, fixo no
    canto superior esquerdo (ex: "Matt/Mt/마 2:4"), mudando só o número do
    versículo. Camada separada das legendas de idioma (meio da tela) —
    pensada para ser queimada junto via queimar_legendas_ass(video, [ass1, ass2], saida).
    """
    if caminho_saida is None:
        caminho_saida = Path(f"versiculo_{config.NOME_ORACAO}.ass")
    else:
        caminho_saida = Path(caminho_saida)

    # FONTE_CJK cobre os caracteres latinos normalmente também (fallback do
    # sistema), por isso é seguro usar sempre, mesmo com abreviações latinas.
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {config.LARGURA_TELA}
PlayResY: {config.ALTURA_TELA}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Versiculo,{config.FONTE_CJK},{config.TAMANHO_FONTE_VERSICULO},&H00FFFFFF,&H000000FF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,{config.CONTORNO_VERSICULO},0,7,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    linhas: list[str] = [header]
    for leg in legendas_versiculo:
        texto_safe = _escapar_ass_texto(leg.texto)
        if not texto_safe:
            continue
        linhas.append(
            f"Dialogue: 0,{_ms_para_ass(leg.inicio_ms)},{_ms_para_ass(leg.fim_ms)},"
            f"Versiculo,,0,0,0,,{texto_safe}\n"
        )

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    logger.info("gerar_ass_versiculo: %s (%d versículos)", caminho_saida.name, len(legendas_versiculo))
    return caminho_saida


def queimar_legendas_ass(
    video_entrada: Path | str,
    ass_path:      Path | str | list[Path | str],
    saida:         Path | str,
) -> Path:
    """
    Queima um (ou mais) arquivo(s) ASS no vídeo, encadeados no mesmo filtro
    `ass=`. Um único passe de codificação para todas as camadas (idiomas +
    indicador de versículo, por exemplo) — não custa mais que queimar uma só.

    Aceita um único caminho (compatibilidade com chamadas antigas) ou uma
    lista de caminhos, aplicados na ordem dada.
    """
    saida = Path(saida)
    caminhos = ass_path if isinstance(ass_path, (list, tuple)) else [ass_path]
    # O caminho do .ass precisa de barras normais no FFmpeg (mesmo no Windows/Colab)
    ass_strs = [str(Path(p).resolve()).replace("\\", "/") for p in caminhos]
    filtro = ",".join(f"ass={s}" for s in ass_strs)

    encoder, args_qualidade = _detectar_encoder_video()

    _run(
        ["ffmpeg", "-y",
         "-i", str(video_entrada),
         "-vf", filtro,
         "-c:a", "copy",
         "-c:v", encoder, *args_qualidade,
         str(saida)],
        "queimar_ass",
    )
    logger.info(
        "queimar_legendas_ass: %s → %s (%d camada(s), encoder=%s)",
        Path(video_entrada).name, saida.name, len(caminhos), encoder,
    )
    return saida
