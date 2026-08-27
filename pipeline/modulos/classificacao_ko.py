# -*- coding: utf-8 -*-
"""
classificacao_ko.py — Mapeamento das tags do Kiwi (coreano) pras classes
customizadas do projeto.

Diferente do Stanza (uma classe por PALAVRA inteira), o Kiwi já devolve a
palavra decomposta em PEÇAS (radical + partícula + terminação) — a decisão
de projeto foi manter essa granularidade (cada peça com sua própria cor),
então aqui o mapeamento é peça por peça, MAS com uma exceção importante: o
radical do verbo (VV/VA/...) não carrega a informação de tempo sozinho —
isso vem de uma peça vizinha (EP/EF) dentro da MESMA palavra original. Por
isso a função principal recebe a lista de peças de uma palavra inteira de
uma vez, não peça isolada.

As classes devolvidas aqui são mais FINAS que as 20 cores oficiais de
cores.py (ex: "particula_sujeito", "verbo_passado" -- não existem como
cor própria) -- de propósito, pra ficar informativo no JSON de
classificação salvo (ver renderizacao.salvar_classificacao_multicolor).
Quem acha a cor de fato é cores.cor_html(), que resolve essas classes
finas pras 20 oficiais via cores.MAPA_CLASSES_FINAS (documentado em
assets/central-decisao-cores.html).
"""
from __future__ import annotations

# ── Tags de radical verbal (o "conteúdo" do verbo/adjetivo funcional) ──────
_TAGS_RADICAL_VERBO = {"VV", "VV-I", "VV-R", "VA", "VA-I", "VX", "VCP", "VCN"}

# ── Formas de EP/EF que marcam tempo/honorífico — por PREFIXO da peça,     ──
# ── já que a mesma terminação pode aparecer com variações fonéticas       ──
# ── (았/었/였 são todas "passado", só mudam pela vogal da sílaba anterior) ──
_FORMAS_PASSADO = ("았", "었", "였")
_FORMAS_FUTURO = ("겠", "리")
_FORMAS_HONORIFICO_EF = (
    "습니다", "ㅂ니다", "습니까", "ㅂ니까", "세요", "십시오", "요",
    # o Kiwi às vezes representa a mesma terminação com o jamo final
    # isolado (ᆸ/ᆺ) em vez da sílaba completa (습/셨) — mesma terminação,
    # representação Unicode diferente
    "ᆸ니다", "ᆸ니까", "ᆸ시오",
)
_FORMAS_HONORIFICO_EP = ("시", "으시")

# ── Formas de EF que marcam IMPERATIVO (comando: "faça!") — categoria que
# não estava no desenho original das 15-16 classes, adicionada depois de
# achar exemplos reais no roteiro ──────────────────────────────────────────
_FORMAS_IMPERATIVO_EF = ("어라", "아라", "여라", "거라", "너라")

# ── Numerais coreanos usados como MODIFICADOR antes de um substantivo
# (tag MM no Kiwi — mesma tag de "este/esse/aquele", mas semanticamente é
# numeral, não demonstrativo). Cobre a série nativa (한/두/세...) e a
# série sino-coreana (일/이/삼...), nas formas que aparecem como
# modificador (algumas mudam de forma nessa posição: "하나"→"한",
# "둘"→"두", "셋"→"세", "넷"→"네") ──────────────────────────────────────
_NUMERAIS_COREANOS = {
    # série nativa, forma modificadora
    "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉", "열",
    "스무", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔",
    # série sino-coreana — "이" (dois) fica de fora de propósito: colide
    # com "이" (este/esse, demonstrativo) que é MUITO mais comum em texto
    # narrativo; incluir aqui trocaria um bug por outro
    "일", "삼", "사", "오", "육", "칠", "팔", "구", "십",
    "백", "천", "만", "억",
}

# ── Partículas de caso -> classe (mapeamento direto, sem ambiguidade) ──────
_MAPA_PARTICULAS = {
    "JKS": "particula_sujeito",
    "JKO": "particula_objeto",
    "JKG": "particula_possessiva",
    "JC": "conjuncao",
    # JKC/JKV/JKQ são partículas mais raras (complemento, vocativo, citação)
    # sem classe própria no núcleo de 15-16 classes do coreano — caem na
    # mais próxima funcionalmente (todas marcam relação gramatical tipo
    # "adjunta", igual JKB)
    "JKC": "particula_locativa",
    "JKV": "particula_locativa",
    "JKQ": "particula_locativa",
}

# JKB (partícula adverbial) precisa olhar a FORMA pra decidir locativo vs.
# direcional, já que a mesma tag cobre os dois papéis
_FORMAS_DIRECIONAL_JKB = ("로", "으로", "에게로", "한테로")


def _classificar_particula_jkb(forma: str) -> str:
    if any(forma.endswith(f) for f in _FORMAS_DIRECIONAL_JKB):
        return "particula_direcional"
    return "particula_locativa"


def _classificar_jx(forma: str) -> str:
    """JX cobre um grupo maior de partículas auxiliares — tratamos como
    tópico quando é 은/는 (o caso mais comum de longe em texto narrativo),
    senão cai na mesma classe por falta de categoria própria pras outras
    (도='também', 만='só', etc. — não têm classe própria no núcleo)."""
    if forma in ("은", "는"):
        return "particula_topico"
    return "particula_topico"  # fallback — ainda não temos classe pra JX genérico


def classificar_pecas_palavra_ko(pecas: list[dict]) -> list[str]:
    """
    Recebe a lista de peças de UMA palavra original (mesmo posicao_frase +
    posicao_palavra), cada peça um dict com 'peca' (forma) e 'classe_kiwi'
    (tag). Retorna a lista de classes customizadas, na mesma ordem.

    Precisa da palavra inteira de uma vez (não peça isolada) porque o
    tempo verbal do radical depende da terminação vizinha.
    """
    # primeiro, descobre se essa palavra tem marcação de passado/futuro/
    # honorífico/imperativo em alguma das peças (pra aplicar no radical do verbo)
    tempo_da_palavra = None
    modo_da_palavra = None
    honorifico_na_palavra = False
    for p in pecas:
        forma, tag = p["peca"], p["classe_kiwi"]
        if tag == "EP":
            if any(forma.startswith(f) for f in _FORMAS_PASSADO):
                tempo_da_palavra = "passado"
            elif any(forma.startswith(f) for f in _FORMAS_FUTURO):
                tempo_da_palavra = "futuro"
            if forma in _FORMAS_HONORIFICO_EP:
                honorifico_na_palavra = True
        if tag == "EF":
            if forma in _FORMAS_HONORIFICO_EF:
                honorifico_na_palavra = True
            elif forma in _FORMAS_IMPERATIVO_EF:
                modo_da_palavra = "imperativo"

    resultado = []
    for p in pecas:
        forma, tag = p["peca"], p["classe_kiwi"]

        # ── Substantivo ──────────────────────────────────────────────────
        if tag == "NNP":
            resultado.append("substantivo_proprio")
        elif tag in ("NNG", "NNB", "XSN", "XPN"):
            resultado.append("substantivo_neutro_singular")

        # ── Pronome / numeral ────────────────────────────────────────────
        elif tag == "NP":
            resultado.append("pronome_pessoal")
        elif tag == "NR":
            resultado.append("numeral")

        # ── Determinante (이/그/저 "este/esse/aquele") — mapeado pra
        # pronome_demonstrativo, categoria mais próxima do núcleo. MAS: a
        # mesma tag MM também cobre NUMERAL usado como modificador (두
        # "dois", 세 "três" em "두 사람" = "duas pessoas") — esses precisam
        # virar numeral, não demonstrativo, senão "dois" fica com a
        # mesma cor de "este/esse" (achado testando com o roteiro real). ──
        elif tag == "MM":
            if forma in _NUMERAIS_COREANOS:
                resultado.append("numeral")
            else:
                resultado.append("pronome_demonstrativo")

        # ── Advérbio ──────────────────────────────────────────────────────
        elif tag in ("MAG", "MAJ"):
            resultado.append("adverbio")

        # ── Interjeição ───────────────────────────────────────────────────
        elif tag == "IC":
            resultado.append("interjeicao")

        # ── Radical de verbo/verbo-descritivo — usa o tempo/modo detectado ──
        elif tag in _TAGS_RADICAL_VERBO or tag == "XSV" or tag == "XSA":
            if modo_da_palavra == "imperativo":
                resultado.append("verbo_imperativo")
            elif tempo_da_palavra == "passado":
                resultado.append("verbo_passado")
            elif tempo_da_palavra == "futuro":
                resultado.append("verbo_futuro")
            else:
                resultado.append("verbo_presente")  # sem marca = presente (padrão do coreano)

        # ── Partículas de caso ────────────────────────────────────────────
        elif tag in _MAPA_PARTICULAS:
            resultado.append(_MAPA_PARTICULAS[tag])
        elif tag == "JKB":
            resultado.append(_classificar_particula_jkb(forma))
        elif tag == "JX":
            resultado.append(_classificar_jx(forma))

        # ── Terminações — honorífico tem prioridade sobre passado/futuro   ──
        # ── na PRÓPRIA peça (a peça específica que carrega a marca)        ──
        elif tag == "EP":
            if forma in _FORMAS_HONORIFICO_EP:
                resultado.append("honorifico")
            elif any(forma.startswith(f) for f in _FORMAS_PASSADO):
                resultado.append("terminacao_passado")
            elif any(forma.startswith(f) for f in _FORMAS_FUTURO):
                resultado.append("terminacao_futuro")
            else:
                resultado.append("outro")
        elif tag == "EF":
            # Radical já carrega "verbo_imperativo" pro MODO (ver acima) --
            # aqui é a peça da TERMINAÇÃO em si, que mapeia pra
            # terminacao_final independente do modo (as duas subclasses
            # documentadas na central de decisão: "neutra" 다 e
            # "imperativo" 어라).
            if forma in _FORMAS_HONORIFICO_EF:
                resultado.append("honorifico")
            elif forma in _FORMAS_IMPERATIVO_EF:
                resultado.append("terminacao_final_imperativa")
            else:
                resultado.append("terminacao_final_neutra")
        elif tag == "EC":
            resultado.append("conjuncao")  # terminação conectiva — liga orações
        elif tag == "ETN":
            resultado.append("terminacao_nominal")  # transforma verbo em substantivo (기/ㅁ)
        elif tag == "ETM":
            resultado.append("terminacao_adjetival")  # transforma verbo em modificador (ㄴ/ㄹ/는)

        # ── Pontuação ─────────────────────────────────────────────────────
        elif tag in ("SF", "SP"):
            resultado.append("pontuacao")

        elif tag == "XSM":
            resultado.append("sufixo")  # sufixo raro (ex: 히) sem categoria própria

        else:
            resultado.append("outro")  # qualquer tag imprevista

    return resultado
