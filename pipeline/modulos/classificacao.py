# -*- coding: utf-8 -*-
"""
classificacao.py — Mapeamento SIMPLIFICADO do Stanza (PT/EN/ES/FR/ZH) pras
11 classes do núcleo + 2 extensões do inglês.

Verbo, substantivo, pronome e artigo não têm mais
sub-classes (sem distinção de tempo verbal, gênero, número, ou
definido/indefinido) — é uma cor só por classe ampla, decisão de projeto
pra priorizar simplicidade visual sobre granularidade gramatical.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# Inglês — modais e auxiliares (mesma lista de sempre, agora todos os
# modais caem na MESMA classe "modal", sem separar futuro de condicional)
# ══════════════════════════════════════════════════════════════════════════
_EN_MODAIS = {"will", "shall", "would", "might", "could", "should", "may", "must", "can"}
_EN_AUXILIARES_DO = {"do", "does", "did"}
_EN_PART_AUXILIARES = {"to", "'s"}


def parse_feats(feats_str: str) -> dict[str, str]:
    if not feats_str or not isinstance(feats_str, str):
        return {}
    resultado = {}
    for par in feats_str.split("|"):
        if "=" in par:
            chave, valor = par.split("=", 1)
            resultado[chave] = valor
    return resultado


def classificar_palavra_stanza(palavra: str, lema: str, upos: str, xpos: str,
                                 feats_str: str, idioma: str) -> str:
    """Classe simplificada pra uma palavra analisada pelo Stanza."""
    feats = parse_feats(feats_str)
    lema_lower = (lema or "").lower()

    # ── Inglês: modal / auxiliar (checa antes do resto) ───────────────────
    if idioma == "en":
        if upos == "AUX" and lema_lower in _EN_MODAIS:
            return "modal"
        if upos == "AUX" and lema_lower in _EN_AUXILIARES_DO:
            return "auxiliar"
        if upos == "PART":
            if lema_lower in _EN_PART_AUXILIARES:
                return "auxiliar"
            if lema_lower == "not":
                return "adverbio"

    # ── Chinês: partícula (的, 了, 吗, 着, 过, 地, 得...) ────────────────────
    # PART é a classe mais frequente do chinês -- 的 sozinho é o caractere
    # mais comum da língua. Sem este branch ela cairia no fallback lá do
    # fim ("adverbio"), pintando de laranja a maior parte do texto.
    # Reaproveita a categoria "particula" que já existe pro coreano: mesma
    # função gramatical (marca relação/aspecto, sem conteúdo lexical
    # próprio) e mesma cor -- por isso o chinês não precisou de nenhuma
    # categoria de cor nova, só das 14 genéricas + particula.
    if idioma == "zh" and upos == "PART":
        return "particula"

    # ── Substantivo / nome próprio ──────────────────────────────────────────
    if upos == "PROPN":
        return "nome_proprio"
    if upos == "NOUN":
        return "substantivo"

    # ── Pronome ──────────────────────────────────────────────────────────
    if upos == "PRON":
        return "pronome"

    # ── Verbo / auxiliar (sem distinção de tempo) ────────────────────────
    if upos in ("VERB", "AUX"):
        # particípio funcionando como qualidade -> mantém como adjetivo
        # (decisão de projeto — "nascido", "perdido")
        if feats.get("VerbForm") == "Part":
            return "adjetivo"
        return "verbo"

    # ── Adjetivo ────────────────────────────────────────────────────────
    if upos == "ADJ":
        return "adjetivo"

    # ── Artigo (agora cobre TODO determinante, sem separar             ──
    # ── possessivo/demonstrativo/etc — decisão de projeto)               ──
    if upos == "DET":
        return "artigo"

    # ── Preposição ────────────────────────────────────────────────────────
    if upos == "ADP":
        return "preposicao"

    # ── Conjunção ─────────────────────────────────────────────────────────
    if upos in ("CCONJ", "SCONJ"):
        return "conjuncao"

    # ── Advérbio ──────────────────────────────────────────────────────────
    if upos == "ADV":
        return "adverbio"

    # ── Numeral — agora com classe própria (era fallback em adjetivo) ────
    if upos == "NUM":
        return "numeral"

    # ── Interjeição ───────────────────────────────────────────────────────
    if upos == "INTJ":
        return "interjeicao"

    # ── Pontuação ─────────────────────────────────────────────────────────
    if upos == "PUNCT":
        return "pontuacao"

    # ── Sobra (PART fora do inglês, X, SYM etc.) ────────────────────────
    return "adverbio"  # fallback mais neutro possível dentro do núcleo de 11
