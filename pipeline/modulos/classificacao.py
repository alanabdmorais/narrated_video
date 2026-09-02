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

# ═══════════════════════════════════════════════════════════════════════════
# Preposição que introduz infinitivo, e que o Stanza rotula como conjunção
# ══════════════════════════════════════════════════════════════════════════
# "Ao verem a estrela", "passou a viver numa cidade": o Stanza olha a FUNÇÃO
# (a palavra abre uma oração) e devolve SCONJ. Pela classe, porém, é
# preposição -- e é assim que a legenda tem que pintar, porque a cor é por
# classe, não por função sintática.
#
# Só vale quando o que vem depois é infinitivo. "Vou ao mercado" não entra
# aqui: ali o Stanza já devolve ADP e nada precisa ser corrigido.
_PREP_ANTES_DE_INFINITIVO = {
    "pt": {"a", "ao", "aos", "à", "às"},
    "es": {"a", "al"},
    "fr": {"à", "au", "aux", "de", "du", "des"},
}

# ═══════════════════════════════════════════════════════════════════════════
# Pronome no vocativo, que o Stanza rotula como interjeição
# ══════════════════════════════════════════════════════════════════════════
# "Tu, Belém, terra de Judá": chamar alguém faz o Stanza ler a palavra como
# interjeição. Defensável pela função, errado pela classe -- "Tu" é pronome
# em qualquer análise de classe de palavra.
_PRONOMES_QUE_VIRAM_VOCATIVO = {
    "pt": {"tu", "vós", "você", "vocês", "senhor", "senhora"},
    "es": {"tú", "vosotros", "usted", "ustedes"},
    "fr": {"tu", "toi", "vous"},
    "en": {"thou", "ye", "you"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Clítico colado ao verbo por hífen
# ══════════════════════════════════════════════════════════════════════════
# "prostraram-se", "adorá-lo", "Levanta-te": o Stanza devolve UM token, com
# duas palavras sintáticas dentro (o verbo e o pronome). O notebook usa o
# token pra não exibir a forma subjacente ("em os dias" no lugar de "nos
# dias") -- mas aqui a forma subjacente e a escrita são a MESMA coisa: o
# hífen já separa as duas na tela. Sem separar, "prostraram-se" sai vermelho
# inteiro e o pronome nunca ganha o roxo dele. São 13 casos só no Mateus 2.
#
# A contração NÃO entra aqui, e é por isso que a regra pede hífen: "da" é
# de+a sem nenhuma fronteira visível, então tem que continuar sendo uma peça
# só, com a cor da preposição.


def separar_por_hifen(texto: str, n_palavras: int) -> list[str] | None:
    """Reparte o texto de um token nas partes que o hífen já separa, uma por
    palavra sintática. Devolve None quando não dá pra casar -- e aí quem chama
    segue com a peça inteira, como antes.

    O hífen fica no fim da parte anterior, que é onde ele está escrito:

        separar_por_hifen("prostraram-se", 2)  -> ["prostraram-", "se"]
        separar_por_hifen("dá-lo-ei", 3)       -> ["dá-", "lo-", "ei"]
        separar_por_hifen("da", 2)             -> None   (contração)
        separar_por_hifen("guarda-chuva", 1)   -> None   (uma palavra só)
    """
    if n_palavras < 2 or "-" not in texto:
        return None
    partes = texto.split("-")
    if len(partes) != n_palavras or not all(p.strip() for p in partes):
        return None
    return [p + "-" for p in partes[:-1]] + [partes[-1]]


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
                                 feats_str: str, idioma: str,
                                 upos_seguinte: str | None = None,
                                 feats_seguinte: str = "") -> str:
    """Classe simplificada pra uma palavra analisada pelo Stanza.

    `upos_seguinte`/`feats_seguinte` são a análise da PRÓXIMA palavra, e são
    opcionais: só duas regras precisam delas (ver
    _PREP_ANTES_DE_INFINITIVO). Sem elas a função se comporta como antes.
    """
    feats = parse_feats(feats_str)
    lema_lower = (lema or "").lower()
    forma_lower = (palavra or "").strip().lower()

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
        # ...a não ser que seja preposição introduzindo infinitivo.
        if forma_lower in _PREP_ANTES_DE_INFINITIVO.get(idioma, ()):
            seguinte = parse_feats(feats_seguinte)
            if upos_seguinte in ("VERB", "AUX") and seguinte.get("VerbForm") == "Inf":
                return "preposicao"
        return "conjuncao"

    # ── Advérbio ──────────────────────────────────────────────────────────
    if upos == "ADV":
        return "adverbio"

    # ── Numeral — agora com classe própria (era fallback em adjetivo) ────
    if upos == "NUM":
        return "numeral"

    # ── Interjeição ───────────────────────────────────────────────────────
    if upos == "INTJ":
        # ...a não ser que seja pronome sendo usado pra chamar alguém.
        if forma_lower in _PRONOMES_QUE_VIRAM_VOCATIVO.get(idioma, ()):
            return "pronome"
        return "interjeicao"

    # ── Pontuação ─────────────────────────────────────────────────────────
    if upos == "PUNCT":
        return "pontuacao"

    # ── Sobra (PART fora do inglês, X, SYM etc.) ────────────────────────
    return "adverbio"  # fallback mais neutro possível dentro do núcleo de 11
