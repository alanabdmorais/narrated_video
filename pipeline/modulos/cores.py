# -*- coding: utf-8 -*-
"""
cores.py — Paleta oficial: uma cor por classe gramatical — 20 classes.

Paleta EMOJI-FIRST: cada cor foi escolhida por ter um emoji equivalente, pra
dar pra sinalizar a legenda na descrição do YouTube (onde só existe emoji, não
quadradinho colorido arbitrário). Por isso os nomes de cor aqui não são mais
os do CSS Color Module — o critério que manda agora é "tem emoji?".

Alinhado com o método Montessori de ensino de gramática nas 9 classes que ele
define (substantivo=preto, verbo=vermelho, pronome=roxo, advérbio=laranja,
conjunção=rosa, interjeição=dourado, artigo=azul claro, adjetivo=azul escuro,
preposição=verde). As classes que o Montessori não cobre (nome próprio,
numeral, pontuação, extensões de inglês/coreano) usam o resto da paleta.
"""
from __future__ import annotations

# ── A PALETA: 21 cores com emoji ──────────────────────────────────────────────
# hex -> (emoji, nome legível). Uma cor sobra sem classe (21 cores, 20 classes)
# -- fica de reserva pra quando surgir uma classe nova.
PALETA_EMOJI: dict[str, tuple[str, str]] = {
    "#FF0000": ("🔴", "vermelho"),
    "#FFA500": ("🟠", "laranja"),
    "#FFFF00": ("🟡", "amarelo"),
    "#0000FF": ("🔵", "azul"),
    "#800080": ("🟣", "roxo"),
    "#000000": ("🖤", "preto"),
    "#FFFFFF": ("🤍", "branco"),
    "#FFDFC4": ("🏻", "pele muito clara"),
    "#F1C27D": ("🏼", "pele clara"),
    "#E0AC69": ("🏽", "pele média"),
    "#C68642": ("🏾", "pele morena"),
    "#8D5524": ("🏿", "pele escura"),
    "#FF69B4": ("🩷", "rosa"),
    "#87CEEB": ("🩵", "azul claro"),
    "#808080": ("🩶", "cinza"),
    "#2E7D32": ("🧶", "verde escuro"),
    "#66BB6A": ("📗", "verde claro"),
    "#C8A2C8": ("🪻", "lilás"),
    "#556B2F": ("🪖", "verde oliva"),
    "#722F37": ("🍷", "vinho"),
    "#FFD700": ("🏆", "dourado"),
}

# ── CLASSE -> COR ─────────────────────────────────────────────────────────────
# As 9 do Montessori mantêm a cor dele. As outras 11 foram distribuídas no
# resto da paleta com uma regra: os 5 tons de pele são muito parecidos entre
# si, então ficam o mais longe possível UNS DOS OUTROS nas classes que podem
# aparecer lado a lado. Ajuda que várias dessas classes são exclusivas de um
# idioma -- "modal" só existe em inglês e as terminações só em coreano, então
# nunca caem na mesma linha de legenda e podem usar tons vizinhos sem risco.
CORES_HTML: dict[str, str] = {
    # ── Montessori (mesma cor do método) ──────────────────────────────────
    "substantivo":  "#000000",   # 🖤 preto
    "verbo":        "#FF0000",   # 🔴 vermelho
    "pronome":      "#800080",   # 🟣 roxo
    "adverbio":     "#FFA500",   # 🟠 laranja
    "conjuncao":    "#FF69B4",   # 🩷 rosa
    "interjeicao":  "#FFD700",   # 🏆 dourado
    "artigo":       "#87CEEB",   # 🩵 azul claro
    "adjetivo":     "#0000FF",   # 🔵 azul (o "azul escuro" do Montessori)
    "preposicao":   "#2E7D32",   # 🧶 verde escuro
    # ── Fora do Montessori — genéricas ────────────────────────────────────
    "nome_proprio": "#FFFF00",   # 🟡 amarelo
    "pontuacao":    "#808080",   # 🩶 cinza
    "numeral":      "#FFDFC4",   # 🏻 pele muito clara — o tom mais claro:
                                 #    numeral aparece em TODOS os idiomas,
                                 #    então precisa destoar de todo o resto
    # ── Extensão do inglês ────────────────────────────────────────────────
    "auxiliar":     "#FFFFFF",   # 🤍 branco
    "modal":        "#8D5524",   # 🏿 pele escura — o tom mais escuro, no
                                 #    extremo oposto do numeral (é com ele
                                 #    que pode dividir linha, em inglês)
    # ── Extensão do coreano ───────────────────────────────────────────────
    "particula":              "#C8A2C8",   # 🪻 lilás
    "terminacao_honorifica":  "#556B2F",   # 🪖 verde oliva
    "terminacao_nominal":     "#66BB6A",   # 📗 verde claro
    "terminacao_adjetival":   "#C68642",   # 🏾 pele morena
    "terminacao_final":       "#722F37",   # 🍷 vinho
    "sufixo":                 "#F1C27D",   # 🏼 pele clara
}

# 🏽 pele média (#E0AC69) fica de reserva, sem classe — de propósito: deixa
# um degrau vazio entre os tons de pele usados, aumentando a distância entre
# eles.
COR_RESERVA: str = "#E0AC69"


def _cor_texto_por_luminancia(hex_cor: str) -> str:
    """Preto ou branco, o que contrastar melhor com o fundo.

    MESMA regra (luminância > 128 -> texto preto) que ffmpeg_utils e
    renderizacao aplicam na hora de desenhar a legenda. Derivar daqui, em vez
    de manter uma tabela escrita à mão, garante que as duas nunca discordem.
    """
    r, g, b = int(hex_cor[1:3], 16), int(hex_cor[3:5], 16), int(hex_cor[5:7], 16)
    return "#000000" if (0.299 * r + 0.587 * g + 0.114 * b) > 128 else "#FFFFFF"


CORES_TEXTO: dict[str, str] = {
    classe: _cor_texto_por_luminancia(cor) for classe, cor in CORES_HTML.items()
}

# Emoji e nome de cada classe — é isso que vai pra descrição do YouTube.
EMOJI_CLASSE: dict[str, str] = {
    classe: PALETA_EMOJI[cor][0] for classe, cor in CORES_HTML.items()
}
NOMES_COR: dict[str, str] = {
    classe: PALETA_EMOJI[cor][1] for classe, cor in CORES_HTML.items()
}

# Nome legível de cada classe, pra montar a legenda da descrição do YouTube.
NOMES_CLASSE: dict[str, str] = {
    "substantivo": "Substantivo",
    "nome_proprio": "Nome próprio",
    "verbo": "Verbo",
    "pronome": "Pronome",
    "artigo": "Artigo",
    "adjetivo": "Adjetivo",
    "numeral": "Numeral",
    "preposicao": "Preposição",
    "conjuncao": "Conjunção",
    "adverbio": "Advérbio",
    "interjeicao": "Interjeição",
    "pontuacao": "Pontuação",
    "modal": "Partícula modal (inglês)",
    "auxiliar": "Partícula auxiliar (inglês)",
    "particula": "Partícula (coreano/chinês)",
    "terminacao_honorifica": "Terminação honorífica (coreano)",
    "terminacao_nominal": "Terminação nominal (coreano)",
    "terminacao_adjetival": "Terminação adjetival (coreano)",
    "terminacao_final": "Terminação final (coreano)",
    "sufixo": "Sufixo (coreano)",
}

# ── Classes finas do coreano (classificacao_ko.py) -> uma das 20 cores    ──
# ── oficiais acima. Decisão documentada em assets/central-decisao-      ──
# ── cores.html (subclasses de cada card) -- as duas exceções sem        ──
# ── subclasse documentada lá (terminacao_passado/terminacao_futuro, as  ──
# ── terminações de tempo PRÉ-final -- ver EP em classificacao_ko.py)    ──
# ── foram decididas aqui: tratadas como parte da família "verbo" (é a   ──
# ── mesma marcação de tempo que já colore o radical do verbo).          ──
MAPA_CLASSES_FINAS: dict[str, str] = {
    "substantivo_proprio": "nome_proprio",
    "substantivo_neutro_singular": "substantivo",
    "pronome_pessoal": "pronome",
    "pronome_demonstrativo": "pronome",
    "verbo_presente": "verbo",
    "verbo_passado": "verbo",
    "verbo_futuro": "verbo",
    "verbo_imperativo": "verbo",
    "particula_sujeito": "particula",
    "particula_objeto": "particula",
    "particula_possessiva": "particula",
    "particula_locativa": "particula",
    "particula_direcional": "particula",
    "particula_topico": "particula",
    "honorifico": "terminacao_honorifica",
    "terminacao_passado": "verbo",  # sem subclasse documentada -- ver comentário acima
    "terminacao_futuro": "verbo",   # sem subclasse documentada -- ver comentário acima
    "terminacao_final_neutra": "terminacao_final",
    "terminacao_final_imperativa": "terminacao_final",
}


def _resolver_classe(classe: str) -> str:
    """Traduz uma classe fina (ver MAPA_CLASSES_FINAS) pra uma das 20
    oficiais -- classes que já são oficiais (ou "outro"/desconhecidas)
    passam direto."""
    return MAPA_CLASSES_FINAS.get(classe, classe)


def cor_html(classe: str) -> str:
    return CORES_HTML.get(_resolver_classe(classe), "#808080")


def cor_texto(classe: str) -> str:
    return CORES_TEXTO.get(_resolver_classe(classe), "#000000")


def nome_cor(classe: str) -> str:
    """Nome legível da cor dessa classe (ex: "verde oliva", "lilás")."""
    return NOMES_COR.get(_resolver_classe(classe), "")


def emoji_classe(classe: str) -> str:
    """Emoji da cor dessa classe — é o que vai pra descrição do YouTube."""
    return EMOJI_CLASSE.get(_resolver_classe(classe), "")


def cor_ass(classe: str) -> str:
    """Converte pro formato ASS &H00BBGGRR (BGR, não RGB)."""
    h = cor_html(classe).replace("#", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


def emoji_por_cor(hex_cor: str) -> str:
    """Emoji da paleta pra esse hex, ou "" se a cor não faz parte dela.

    Usado pra resolver o emoji de cores que não vêm de CORES_HTML — o caso
    principal é CORES_IDIOMAS (config.py), que é 1 cor por IDIOMA, não por
    classe gramatical, mas sai da mesma paleta.
    """
    return PALETA_EMOJI.get(hex_cor.upper(), ("", ""))[0]


# Nome de cada idioma pra legenda da descrição (o mesmo NOMES_IDIOMA de
# constants.py, repetido aqui pra cores.py não depender de nada do projeto).
NOMES_IDIOMA_LEGENDA: dict[str, str] = {
    "pt": "Português", "en": "Inglês", "es": "Espanhol",
    "fr": "Francês", "ko": "Coreano", "zh": "Chinês",
}


def legenda_youtube_idiomas(cores_idiomas: dict[str, str],
                            ordem: list[str] | None = None) -> str:
    """Bloco de legenda do vídeo MULTI-IDIOMA (1 cor por idioma) pra colar na
    descrição do YouTube.

    Recebe o `config.CORES_IDIOMAS` do vídeo. `ordem` define a sequência
    (idealmente a mesma de cima pra baixo na tela, POSICOES_Y); o padrão segue
    a ordem do próprio dict. Idioma cuja cor não estiver na paleta sai com
    "⬜" e o hex, pra ficar evidente que falta emoji pra ela.
    """
    linhas = []
    for lang in (ordem if ordem is not None else cores_idiomas):
        cor = cores_idiomas.get(lang)
        if not cor:
            continue
        emoji = emoji_por_cor(cor)
        nome = NOMES_IDIOMA_LEGENDA.get(lang, lang.upper())
        linhas.append(f"{emoji} {nome}" if emoji else f"⬜ {nome} (cor {cor} sem emoji)")
    return "\n".join(linhas)


def legenda_youtube(classes: list[str] | None = None) -> str:
    """Monta o bloco de legenda pra colar na descrição do YouTube:
    uma linha por classe, com o emoji da cor.

    `classes` limita/ordena a lista (ex: só as que aparecem num vídeo sem
    coreano); o padrão traz as 20 na ordem de CORES_HTML.
    """
    linhas = []
    for classe in (classes if classes is not None else CORES_HTML):
        if classe not in CORES_HTML:
            continue
        linhas.append(f"{EMOJI_CLASSE[classe]} {NOMES_CLASSE.get(classe, classe)}")
    return "\n".join(linhas)
