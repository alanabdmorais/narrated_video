# -*- coding: utf-8 -*-
"""
dicionario_sinonimos_clima.py — Grupos de palavras de CLIMA/EMOÇÃO
equivalentes (PT), pra expandir Tags_Clima na hora de casar trilha
sonora com evento/título bíblico.

É um dicionário SEPARADO do dicionario_sinonimos.py (visual) --
"tranquilo"/"calmo" não tem nada a ver com sinônimo visual, é outra
dimensão inteira (como a cena SOA, não como ela PARECE).

Curado a partir do que apareceu nas suas duas fontes de trilha
(Freesound + lista manual do YouTube Audio Library) -- vai crescer
conforme aparecer palavra nova.
"""

GRUPOS_CLIMA_PT = [
    ["calmo", "calma", "tranquilo", "tranquila", "sereno", "serena", "pacífico", "pacífica", "relax", "relaxante"],
    ["alegre", "alegria", "feliz", "felicidade", "festivo", "festiva", "animado", "animada", "jovial"],
    ["triste", "tristeza", "melancólico", "melancólica", "melancolia", "pesar", "sad", "sadness"],
    ["dramático", "dramática", "intenso", "intensa", "tenso", "tensa", "grave"],
    ["suspense", "suspenso", "misterioso", "misteriosa", "mistério", "inquietante", "sombrio", "sombria"],
    ["épico", "épica", "grandioso", "grandiosa", "heroico", "heroica", "triunfante"],
    ["esperançoso", "esperançosa", "esperança", "hope", "otimista", "inspirador", "inspiradora", "inspiração", "oportunidade", "oportunidades"],
    ["desafio", "desafios", "desafiador", "desafiadora", "obstáculo", "obstáculos"],
    ["solene", "reverente", "sagrado", "sagrada", "espiritual", "contemplativo", "contemplativa"],
    ["urgente", "urgência", "agitado", "agitada", "acelerado", "acelerada", "correria"],
    ["romântico", "romântica", "terno", "terna", "carinhoso", "carinhosa", "afetuoso", "afetuosa"],
    ["assustador", "assustadora", "medo", "temor", "aterrorizante", "tenebroso", "tenebrosa"],
    ["nostálgico", "nostálgica", "nostalgia", "saudade", "saudoso", "saudosa"],
    ["triunfal", "vitorioso", "vitoriosa", "vitória", "conquista", "celebração", "celebratório"],
    ["pastoral", "bucólico", "bucólica", "campestre", "idílico", "idílica"],
    ["majestoso", "majestosa", "real", "regal", "nobre", "imponente"],
]


def _construir_mapa(grupos):
    import unicodedata

    def normalizar(s):
        nfkd = unicodedata.normalize("NFD", s.lower().strip())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    mapa = {}
    for grupo in grupos:
        for palavra in grupo:
            mapa[normalizar(palavra)] = grupo
    return mapa


MAPA_CLIMA_PT = _construir_mapa(GRUPOS_CLIMA_PT)


def expandir_tags_clima(tags):
    """
    Mesma lógica de expandir_tags_semelhantes (dicionario_sinonimos.py),
    só que pro dicionário de CLIMA -- também testa palavra por palavra
    dentro de frases (ex: "trilha calma e serena" bate em "calma" E
    "serena" separadamente).
    """
    import unicodedata

    def normalizar(s):
        nfkd = unicodedata.normalize("NFD", s.lower().strip())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    expandido = list(dict.fromkeys(tags))
    for tag in tags:
        chaves_a_testar = [normalizar(tag)]
        palavras = normalizar(tag).split()
        if len(palavras) > 1:
            chaves_a_testar += palavras
        for chave in chaves_a_testar:
            grupo = MAPA_CLIMA_PT.get(chave)
            if grupo:
                for sinonimo in grupo:
                    if sinonimo not in expandido:
                        expandido.append(sinonimo)
    return expandido
