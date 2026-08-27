# -*- coding: utf-8 -*-
"""
cores.py — Paleta oficial: uma cor por classe gramatical, usando nomes de
cor reconhecidos pelo padrão CSS Color Module (W3C) — 20 classes.

Alinhado com o método Montessori de ensino de gramática onde ele define
categoria própria (substantivo=preto, verbo=vermelho, pronome=roxo,
advérbio=laranja, conjunção=rosa, interjeição=dourado — 6 de 20 batendo
exato). Nas classes que o Montessori não cobre (nome próprio, numeral,
pontuação, extensões de inglês/coreano), usa as cores obrigatórias
restantes da lista aprovada.
"""
from __future__ import annotations

CORES_HTML: dict[str, str] = {
    "substantivo": "#000000",
    "nome_proprio": "#FFFF00",
    "verbo": "#FF0000",
    "pronome": "#800080",
    "artigo": "#0000FF",
    "adjetivo": "#000080",
    "numeral": "#C0C0C0",
    "preposicao": "#2E8B57",
    "conjuncao": "#FFC0CB",
    "adverbio": "#FFA500",
    "interjeicao": "#FFD700",
    "pontuacao": "#808080",
    "modal": "#A52A2A",
    "auxiliar": "#FFFFFF",
    "particula": "#7FFFD4",
    "terminacao_honorifica": "#808000",
    "terminacao_nominal": "#FA8072",
    "terminacao_adjetival": "#4B0082",
    "terminacao_final": "#DC143C",
    "sufixo": "#008080",
}

CORES_TEXTO: dict[str, str] = {
    "substantivo": "#FFFFFF",
    "nome_proprio": "#000000",
    "verbo": "#FFFFFF",
    "pronome": "#FFFFFF",
    "artigo": "#FFFFFF",
    "adjetivo": "#FFFFFF",
    "numeral": "#000000",
    "preposicao": "#FFFFFF",
    "conjuncao": "#000000",
    "adverbio": "#000000",
    "interjeicao": "#000000",
    "pontuacao": "#FFFFFF",
    "modal": "#FFFFFF",
    "auxiliar": "#000000",
    "particula": "#000000",
    "terminacao_honorifica": "#FFFFFF",
    "terminacao_nominal": "#000000",
    "terminacao_adjetival": "#FFFFFF",
    "terminacao_final": "#FFFFFF",
    "sufixo": "#FFFFFF",
}

# nome oficial (CSS Color Module / W3C) de cada cor -- útil pra documentação
# e pra bater com a Central de Decisão (central-decisao-cores.html)
NOMES_COR_OFICIAL: dict[str, str] = {
    "substantivo": "black",
    "nome_proprio": "yellow",
    "verbo": "red",
    "pronome": "purple",
    "artigo": "blue",
    "adjetivo": "navy",
    "numeral": "silver",
    "preposicao": "seagreen",
    "conjuncao": "pink",
    "adverbio": "orange",
    "interjeicao": "gold",
    "pontuacao": "gray",
    "modal": "brown",
    "auxiliar": "white",
    "particula": "aquamarine",
    "terminacao_honorifica": "olive",
    "terminacao_nominal": "salmon",
    "terminacao_adjetival": "indigo",
    "terminacao_final": "crimson",
    "sufixo": "teal",
}


def cor_html(classe: str) -> str:
    return CORES_HTML.get(classe, "#808080")


def cor_texto(classe: str) -> str:
    return CORES_TEXTO.get(classe, "#000000")


def nome_cor_oficial(classe: str) -> str:
    """Nome oficial CSS da cor dessa classe (ex: "gold", "royalblue")."""
    return NOMES_COR_OFICIAL.get(classe, "")


def cor_ass(classe: str) -> str:
    """Converte pro formato ASS &H00BBGGRR (BGR, não RGB)."""
    h = cor_html(classe).replace("#", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"
