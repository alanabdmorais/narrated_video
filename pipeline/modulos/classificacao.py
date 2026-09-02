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
# Onde ficam as EXCEÇÕES
# ══════════════════════════════════════════════════════════════════════════
# Aqui em baixo só mora o MAPEAMENTO BASE: o que a etiqueta do analisador
# significa. "PROPN é nome próprio", "ADP é preposição", "AUX com lema modal
# em inglês é modal".
#
# Onde a etiqueta ENGANA -- "Ao verem" vem como conjunção mas pela classe é
# preposição, "Tu, Belém" vem como interjeição mas é pronome, "para que" são
# duas palavras que formam uma conjunção só -- é caso pra central de
# correções automáticas, em dados_lexico/classes-correcoes.json, aplicada por
# revisao_classes.aplicar_correcoes().
#
# A divisão não é arbitrária: exceção precisa ver o CONTEXTO (a palavra
# vizinha, os traços dela), e uma função que recebe uma palavra por vez não
# tem como. Enquanto elas moravam aqui, cada uma exigia mais um parâmetro de
# contexto na assinatura. Na central, contexto é um campo do JSON.

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
                                 feats_str: str, idioma: str) -> str:
    """Mapeamento BASE: o que a etiqueta do Stanza significa, pra uma palavra.

    Não conhece contexto e não trata exceção — isso é da central de correções
    (ver o bloco "Onde ficam as EXCEÇÕES" acima).
    """
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
