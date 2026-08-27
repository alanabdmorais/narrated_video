# -*- coding: utf-8 -*-
"""
renderizacao.py — Geração de legenda ASS com a classificação nova
(núcleo compartilhado + extensões EN/KO).

Adaptado de ffmpeg_utils.gerar_ass() do sistema antigo — MESMA técnica de
caixa colorida (texto preto/branco por contraste + borda grossa com a cor
da classe), só com duas correções necessárias pro nosso caso:

  1. _escapar() do sistema antigo remove acentos e caracteres não-ASCII
     (normalização NFD + encode ascii) — destruiria o texto coreano por
     completo e degradaria acentos de PT/FR. Aqui só escapamos os
     caracteres que o formato ASS exige (chaves, barra invertida).

  2. O coreano tem PEDAÇOS dentro da mesma palavra escrita (sem espaço
     entre eles) — a função antiga sempre bota espaço depois de cada
     "palavra". Aqui cada item pode marcar `colado_anterior=True` pra
     não ter espaço antes dele (usado só nos pedaços 2+ de uma palavra
     coreana).

Não modifica nenhum arquivo do sistema antigo — é um módulo novo, próprio
pro notebook novo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple, Optional

from config import PipelineConfig
from cores import cor_html as cor_html_classe


class PecaColorida(NamedTuple):
    """Um pedaço de texto com sua classe gramatical, pronto pra renderizar.
    `colado_anterior=True` = sem espaço antes desse pedaço (só pro coreano,
    pedaços 2+ da mesma palavra escrita)."""
    texto: str
    classe: str
    colado_anterior: bool = False


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{tamanho_fonte},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
_LINHA_DIALOGO = "Dialogue: 0,{inicio},{fim},Default,,0,0,0,,{texto}\n"


def _ms_para_ass(ms: int) -> str:
    h  = ms // 3_600_000
    m  = (ms % 3_600_000) // 60_000
    s  = (ms % 60_000) // 1_000
    cc = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cc:02d}"


def _escapar(texto: str) -> str:
    """Escapa só o que o ASS exige (chave, barra invertida) — preserva
    acentos e qualquer script (coreano incluído)."""
    return texto.replace("\\", "").replace("{", "").replace("}", "")


def _html_para_ass_cor(html_hex: str) -> str:
    h = html_hex.replace("#", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


def _linha_colorida_ass(pecas: list[PecaColorida], box_border: int, tamanho_fonte: int,
                          x: int, y: int, fonte_tag: str = "") -> str:
    """Monta a string de conteúdo ASS (com as tags override) pra uma linha
    inteira de pedaços coloridos — mesma técnica do sistema antigo: \\1c
    (texto, preto/branco por contraste) + \\3c (borda grossa = cor da
    classe, simula caixa preenchida).

    `fonte_tag` (ex: "\\\\fnNoto Sans CJK KR") — usado pros idiomas CJK
    (coreano e chinês, ver config.fonte_cjk), cuja fonte padrão (Arial) não
    tem os caracteres Hangul/Han e mostraria quadradinhos (□) no lugar do
    texto."""
    partes: list[str] = []
    for peca in pecas:
        texto_safe = _escapar(peca.texto)
        if not texto_safe.strip():
            continue
        cor_html = cor_html_classe(peca.classe)
        cor_fundo = _html_para_ass_cor(cor_html)
        r, g, b = int(cor_html[1:3], 16), int(cor_html[3:5], 16), int(cor_html[5:7], 16)
        luminancia = 0.299 * r + 0.587 * g + 0.114 * b
        cor_texto = "&H00000000" if luminancia > 128 else "&H00FFFFFF"

        espaco_antes = "" if peca.colado_anterior else " "
        partes.append(
            f"{espaco_antes}{{\\1c{cor_texto}\\3c{cor_fundo}\\bord{box_border}\\shad0{fonte_tag}}}{texto_safe}"
        )

    texto_combinado = "".join(partes).strip()
    return f"{{\\an2\\pos({x},{y})\\fs{tamanho_fonte}}}{texto_combinado}"


def gerar_ass(
    blocos_por_idioma: dict[str, list[dict]],
    config: PipelineConfig,
    caminho_saida: Optional[Path | str] = None,
    box_border: int = 6,
) -> Path:
    """
    Gera o .ass com a classificação nova.

    Args:
        blocos_por_idioma: { "pt": [bloco, ...], "ko": [...], ... } — cada
            bloco é um dict com "inicio_ms", "fim_ms", e "pecas" (lista de
            PecaColorida).
        config: PipelineConfig — usa LARGURA_TELA/ALTURA_TELA/POSICOES_Y/
            TAMANHO_FONTE_TAG (mesmos campos do sistema antigo).
        box_border: largura da borda em px (a "espessura" da caixa).
    """
    if caminho_saida is None:
        caminho_saida = Path(f"legendas_{config.NOME_ORACAO}.ass")
    else:
        caminho_saida = Path(caminho_saida)

    linhas = [_ASS_HEADER.format(
        largura=config.LARGURA_TELA, altura=config.ALTURA_TELA,
        tamanho_fonte=config.TAMANHO_FONTE_TAG,
    )]

    for idioma, blocos in blocos_por_idioma.items():
        y = config.POSICOES_Y.get(idioma, 100)
        x = config.LARGURA_TELA // 2
        # Arial (fonte padrão) não tem os caracteres Hangul — sem isso, o
        # coreano aparece como quadradinhos (□) em ambientes sem fallback
        # automático de fonte (ex: Colab sem a Noto Sans CJK instalada
        # visível pro libass)
        _fonte = config.fonte_cjk(idioma)
        fonte_tag = f"\\fn{_fonte}" if _fonte else ""
        for bloco in blocos:
            pecas = bloco.get("pecas", [])
            if not pecas:
                continue
            texto_ass = _linha_colorida_ass(pecas, box_border, config.TAMANHO_FONTE_TAG, x, y, fonte_tag)
            linhas.append(_LINHA_DIALOGO.format(
                inicio=_ms_para_ass(bloco["inicio_ms"]),
                fim=_ms_para_ass(bloco["fim_ms"]),
                texto=texto_ass,
            ))

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    return caminho_saida


def salvar_classificacao_multicolor(blocos: list[dict], caminho_saida: Path | str) -> Path:
    """Salva a classificação (Stanza/Kiwi já filtrada, ver classificacao.py/
    classificacao_ko.py) de UM idioma como JSON -- disponível pra baixar,
    corrigir manualmente (trocar a "classe" de alguma peça errada) e subir
    de volta com o mesmo nome, antes de gerar o .ass (ver
    carregar_classificacao_multicolor)."""
    caminho_saida = Path(caminho_saida)
    bruto = [
        {
            "inicio_ms": bloco["inicio_ms"],
            "fim_ms": bloco["fim_ms"],
            "pecas": [
                {"texto": p.texto, "classe": p.classe, "colado_anterior": p.colado_anterior}
                for p in bloco.get("pecas", [])
            ],
        }
        for bloco in blocos
    ]
    caminho_saida.write_text(json.dumps(bruto, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho_saida


def carregar_classificacao_multicolor(caminho: Path | str) -> list[dict]:
    """Carrega de volta o JSON salvo por salvar_classificacao_multicolor()
    -- reconstrói as PecaColorida a partir dos dicts, no formato que
    gerar_ass() espera em blocos_por_idioma[idioma]."""
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return [
        {
            "inicio_ms": bloco["inicio_ms"],
            "fim_ms": bloco["fim_ms"],
            "pecas": [
                PecaColorida(p["texto"], p["classe"], p.get("colado_anterior", False))
                for p in bloco.get("pecas", [])
            ],
        }
        for bloco in bruto
    ]
