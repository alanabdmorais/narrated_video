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
    "#FA8072": ("🪸", "salmão"),
    "#66BB6A": ("💚", "verde claro"),
    "#C8A2C8": ("🪻", "lilás"),
    "#556B2F": ("🪖", "verde escuro"),
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
    "preposicao":   "#66BB6A",   # 💚 verde claro (Montessori: preposição é verde)
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
    "terminacao_honorifica":  "#556B2F",   # 🪖 verde escuro
    "terminacao_nominal":    "#FA8072",   # 🪸 salmão
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

# ── Legenda poliglota: nome da classe e exemplo, em cada idioma ──────────────
# O público é poliglota, então a legenda da descrição também é. Estas duas
# tabelas são a fonte ÚNICA -- as centrais de cores injetam os exemplos daqui
# (antes eles viviam soltos dentro do HTML, sem quem os validasse).
#
# "—" = a classe não existe nesse idioma. modal/auxiliar são só do inglês; as
# terminações e o sufixo, só do coreano.

NOMES_CLASSE_IDIOMA: dict[str, dict[str, str]] = {
    "substantivo": {"pt": "substantivo", "en": "noun", "es": "sustantivo", "fr": "nom", "ko": "명사", "zh": "名词"},
    "verbo": {"pt": "verbo", "en": "verb", "es": "verbo", "fr": "verbe", "ko": "동사", "zh": "动词"},
    "pronome": {"pt": "pronome", "en": "pronoun", "es": "pronombre", "fr": "pronom", "ko": "대명사", "zh": "代词"},
    "adverbio": {"pt": "advérbio", "en": "adverb", "es": "adverbio", "fr": "adverbe", "ko": "부사", "zh": "副词"},
    "conjuncao": {"pt": "conjunção", "en": "conjunction", "es": "conjunción", "fr": "conjonction", "ko": "접속사", "zh": "连词"},
    "interjeicao": {"pt": "interjeição", "en": "interjection", "es": "interjección", "fr": "interjection", "ko": "감탄사", "zh": "叹词"},
    "artigo": {"pt": "artigo", "en": "article", "es": "artículo", "fr": "article", "ko": "관사", "zh": "冠词"},
    "adjetivo": {"pt": "adjetivo", "en": "adjective", "es": "adjetivo", "fr": "adjectif", "ko": "형용사", "zh": "形容词"},
    "preposicao": {"pt": "preposição", "en": "preposition", "es": "preposición", "fr": "préposition", "ko": "전치사", "zh": "介词"},
    "nome_proprio": {"pt": "nome próprio", "en": "proper noun", "es": "nombre propio", "fr": "nom propre", "ko": "고유명사", "zh": "专有名词"},
    "pontuacao": {"pt": "pontuação", "en": "punctuation", "es": "puntuación", "fr": "ponctuation", "ko": "문장부호", "zh": "标点"},
    "numeral": {"pt": "numeral", "en": "numeral", "es": "numeral", "fr": "numéral", "ko": "수사", "zh": "数词"},
    "auxiliar": {"pt": "auxiliar", "en": "auxiliary", "es": "auxiliar", "fr": "auxiliaire", "ko": "조동사 (do)", "zh": "助动词"},
    "modal": {"pt": "modal", "en": "modal", "es": "modal", "fr": "modal", "ko": "조동사 (will)", "zh": "情态动词"},
    "particula": {"pt": "partícula", "en": "particle", "es": "partícula", "fr": "particule", "ko": "조사", "zh": "助词"},
    "terminacao_honorifica": {"pt": "terminação honorífica", "en": "honorific ending", "es": "terminación honorífica", "fr": "terminaison honorifique", "ko": "존댓말 어미", "zh": "敬语词尾"},
    "terminacao_nominal": {"pt": "terminação nominal", "en": "nominal ending", "es": "terminación nominal", "fr": "terminaison nominale", "ko": "명사형 어미", "zh": "名词化词尾"},
    "terminacao_adjetival": {"pt": "terminação adjetival", "en": "adjectival ending", "es": "terminación adjetival", "fr": "terminaison adjectivale", "ko": "관형사형 어미", "zh": "定语词尾"},
    "terminacao_final": {"pt": "terminação final", "en": "final ending", "es": "terminación final", "fr": "terminaison finale", "ko": "종결어미", "zh": "句末词尾"},
    "sufixo": {"pt": "sufixo", "en": "suffix", "es": "sufijo", "fr": "suffixe", "ko": "접미사", "zh": "后缀"},
}

EXEMPLOS_CLASSE: dict[str, dict[str, str]] = {
    "substantivo": {"pt": "caminho", "en": "path", "es": "camino", "fr": "chemin", "ko": "길", "zh": "路"},
    "verbo": {"pt": "andar", "en": "walk", "es": "andar", "fr": "marcher", "ko": "걷다", "zh": "走"},
    "pronome": {"pt": "ela", "en": "she", "es": "ella", "fr": "elle", "ko": "그녀", "zh": "她"},
    "adverbio": {"pt": "hoje", "en": "today", "es": "hoy", "fr": "aujourd'hui", "ko": "오늘", "zh": "今天"},
    "conjuncao": {"pt": "mas", "en": "but", "es": "pero", "fr": "mais", "ko": "그러나", "zh": "但是"},
    "interjeicao": {"pt": "ah!", "en": "oh!", "es": "¡ay!", "fr": "ah!", "ko": "아", "zh": "啊"},
    "artigo": {"pt": "o", "en": "the", "es": "el", "fr": "le", "ko": "—", "zh": "这"},
    "adjetivo": {"pt": "forte", "en": "strong", "es": "fuerte", "fr": "fort", "ko": "강한", "zh": "强"},
    "preposicao": {"pt": "sobre", "en": "on", "es": "sobre", "fr": "sur", "ko": "—", "zh": "在"},
    "nome_proprio": {"pt": "Davi", "en": "David", "es": "David", "fr": "David", "ko": "다윗", "zh": "大卫"},
    "pontuacao": {"pt": ".", "en": ".", "es": ".", "fr": ".", "ko": ".", "zh": "。"},
    "numeral": {"pt": "sete", "en": "seven", "es": "siete", "fr": "sept", "ko": "일곱", "zh": "七"},
    "auxiliar": {"pt": "—", "en": "do", "es": "—", "fr": "—", "ko": "—", "zh": "—"},
    "modal": {"pt": "—", "en": "will / can / must", "es": "—", "fr": "—", "ko": "—", "zh": "—"},
    "particula": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "가/는/를", "zh": "的/了/吗"},
    "terminacao_honorifica": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "습니다", "zh": "—"},
    "terminacao_nominal": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "기/ㅁ", "zh": "—"},
    "terminacao_adjetival": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "ㄴ/ㄹ/는", "zh": "—"},
    "terminacao_final": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "다 / 어라", "zh": "—"},
    "sufixo": {"pt": "—", "en": "—", "es": "—", "fr": "—", "ko": "히", "zh": "—"},
}

SEM_EXEMPLO = "—"

assert set(NOMES_CLASSE_IDIOMA) == set(CORES_HTML), "NOMES_CLASSE_IDIOMA divergiu das classes"
assert set(EXEMPLOS_CLASSE) == set(CORES_HTML), "EXEMPLOS_CLASSE divergiu das classes"


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
    """Nome legível da cor dessa classe (ex: "verde escuro", "lilás")."""
    return NOMES_COR.get(_resolver_classe(classe), "")


def emoji_classe(classe: str) -> str:
    """Emoji da cor dessa classe — é o que vai pra descrição do YouTube."""
    return EMOJI_CLASSE.get(_resolver_classe(classe), "")


def cor_ass(classe: str) -> str:
    """Converte pro formato ASS &H00BBGGRR (BGR, não RGB)."""
    h = cor_html(classe).replace("#", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


# ── Em quais idiomas cada classe pode aparecer ────────────────────────────────
# Bate com a coluna "origem" documentada na central de cores: as 12 primeiras
# saem de tags que existem em qualquer idioma; modal/auxiliar só do inglês;
# particula do coreano E do chinês; as terminações e o sufixo, só do coreano.
# Serve pra colinha do YouTube não listar terminação coreana num vídeo que não
# tem coreano.
CLASSES_GENERICAS: tuple[str, ...] = (
    "substantivo", "nome_proprio", "verbo", "pronome", "artigo", "adjetivo",
    "numeral", "preposicao", "conjuncao", "adverbio", "interjeicao", "pontuacao",
)
CLASSES_POR_IDIOMA: dict[str, tuple[str, ...]] = {
    "en": ("modal", "auxiliar"),
    "ko": ("particula", "terminacao_honorifica", "terminacao_nominal",
           "terminacao_adjetival", "terminacao_final", "sufixo"),
    "zh": ("particula",),
}


def classes_para_idiomas(idiomas: list[str]) -> list[str]:
    """Quais das 20 classes podem aparecer num vídeo com esses idiomas.

    Mantém a ordem de CORES_HTML. Ex: um vídeo pt/en/es/fr não tem nenhuma
    das 6 extensões do coreano, então a legenda da descrição fica com 14
    linhas em vez de 20.
    """
    permitidas = set(CLASSES_GENERICAS)
    for lang in idiomas:
        permitidas.update(CLASSES_POR_IDIOMA.get(lang, ()))
    return [c for c in ORDEM_FREQUENCIA if c in permitidas]


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

#: O nome de cada idioma NA PRÓPRIA LÍNGUA. Usado onde quem lê pode não falar
#: português -- o card que abre o vídeo, por exemplo. Escrever "Coreano" pra
#: um espectador coreano é pedir que ele leia português pra descobrir que
#: aquela coluna é a dele; "한국어" ele reconhece de relance.
NOMES_IDIOMA_NATIVO: dict[str, str] = {
    "pt": "português", "en": "english", "es": "español",
    "fr": "français", "ko": "한국어", "zh": "中文",
}

assert set(NOMES_IDIOMA_NATIVO) == set(NOMES_IDIOMA_LEGENDA), \
    "NOMES_IDIOMA_NATIVO divergiu dos idiomas conhecidos"


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


def nome_classe_legenda(classe: str, idiomas: list[str] | None = None) -> str:
    """Nome da classe pra legenda, ajustado aos idiomas do vídeo.

    Só a `particula` muda: ela é a única classe de mais de um idioma
    (coreano e chinês), e anunciar "coreano/chinês" num vídeo que não tem
    chinês -- ou o contrário -- confunde quem lê a descrição. Sem `idiomas`,
    devolve o nome completo de NOMES_CLASSE.
    """
    nome = NOMES_CLASSE.get(classe, classe)
    if classe == "particula" and idiomas is not None:
        donos = [l for l in CLASSES_POR_IDIOMA if l in idiomas
                 and "particula" in CLASSES_POR_IDIOMA[l]]
        if donos:
            nome = "Partícula ({})".format(
                "/".join(NOMES_IDIOMA_LEGENDA[l].lower() for l in donos))
    return nome


# Separador entre idiomas na legenda poliglota. NÃO é "/" de propósito: vários
# exemplos já têm barra por dentro ("will / can / must", "가/는/를"), e aí a
# linha ficaria ambígua -- não dá pra saber onde termina um idioma e começa o
# outro. O "·" não aparece em exemplo nenhum.
# Nome da cor em inglês, pra legenda básica. O emoji sozinho não basta:
# plataforma que não desenha aquele emoji deixa o leitor sem nada, e emoji
# de objeto (livro, taça, capacete) não diz a cor de cara nem quando renderiza.
NOMES_COR_EN: dict[str, str] = {
    "#FF0000": "red", "#FFA500": "orange", "#FFFF00": "yellow",
    "#0000FF": "blue", "#800080": "purple", "#000000": "black",
    "#FFFFFF": "white", "#FFDFC4": "lightest skin", "#F1C27D": "light skin",
    "#E0AC69": "medium skin", "#C68642": "brown skin", "#8D5524": "dark skin",
    "#FF69B4": "pink", "#87CEEB": "light blue", "#808080": "grey",
    "#FA8072": "salmon", "#66BB6A": "light green", "#C8A2C8": "lilac",
    "#556B2F": "dark green", "#722F37": "wine", "#FFD700": "gold",
}

assert set(NOMES_COR_EN) == set(PALETA_EMOJI), "NOMES_COR_EN divergiu da paleta"

NOME_COR_EN_CLASSE: dict[str, str] = {c: NOMES_COR_EN[v] for c, v in CORES_HTML.items()}


# ── Ordem de apresentação: por frequência real ──────────────────────────────
# Medida, não chutada: contagem das 3.127 palavras já classificadas do Mateus 2
# nos 5 idiomas (videos/40_Matt_02/..._classificacao_morfologica_5idiomas.csv),
# com AUX somado a `verbo` e CCONJ+SCONJ a `conjuncao`, como o projeto mapeia.
#
#   verbo 18,3% · substantivo 14,4% · pontuacao 11,6% · preposicao 11,4%
#   pronome 10,5% · artigo 10,4% · conjuncao 9,3% · nome_proprio 5,8%
#   adverbio 5,2% · adjetivo 2,5%   -> estas dez dão 99,4%
#
# As dez últimas quase não aparecem em texto latino: são as exclusivas do
# inglês, coreano e chinês. Empate e ausência caem na ordem de CORES_HTML.
#
# É CONSTANTE, não recalculada por vídeo: se a ordem mudasse a cada capítulo, o
# espectador teria que reaprender a legenda toda vez. Uma ordem, aprendida uma
# vez, valendo na descrição, no card e na central.
ORDEM_FREQUENCIA: tuple[str, ...] = (
    "verbo", "substantivo", "pontuacao", "preposicao",
    "pronome", "artigo", "conjuncao", "nome_proprio",
    "adverbio", "adjetivo", "numeral", "particula",
    "interjeicao", "auxiliar", "modal", "terminacao_honorifica",
    "terminacao_nominal", "terminacao_adjetival", "terminacao_final", "sufixo",
)

assert set(ORDEM_FREQUENCIA) == set(CORES_HTML), "ORDEM_FREQUENCIA divergiu das classes"
assert len(ORDEM_FREQUENCIA) == len(CORES_HTML), "ORDEM_FREQUENCIA tem repetido"


# ── Sobre abreviar os nomes longos ───────────────────────────────────────────
# Tentado e descartado com medição. As quatro terminações coreanas são as
# linhas mais longas do card, mas abreviar a palavra repetida
# ("terminação/terminación/terminaison" -> "term.") faz português, espanhol e
# francês virarem a MESMA string:
#
#     term. honor. · honorific end. · term. honor. · term. honor.
#
# Economiza 32 caracteres apagando a distinção entre três idiomas -- que é
# exatamente o que o card existe pra mostrar. As quatro classes perdiam
# distinção; nenhuma escapava. O comprimento se resolve no layout (coluna
# latina mais larga e quebra de linha), não no texto.


SEPARADOR_IDIOMA = " · "

ORDEM_IDIOMAS_PADRAO = ("pt", "en", "es", "fr", "ko", "zh")


def _idiomas_validos(idiomas: list[str] | None) -> list[str]:
    ordem = list(idiomas) if idiomas else list(ORDEM_IDIOMAS_PADRAO)
    desconhecidos = [l for l in ordem if l not in NOMES_IDIOMA_LEGENDA]
    if desconhecidos:
        raise KeyError(f"idioma(s) sem nome cadastrado: {desconhecidos}")
    return ordem


def cabecalho_poliglota(idiomas: list[str] | None = None) -> str:
    """Linha que ensina a ordem dos idiomas nas linhas de baixo.

    Sem ela a legenda poliglota é ilegível: o leitor vê seis palavras separadas
    por ponto e não sabe qual é qual.
    """
    # Sigla, não o nome por extenso: "Português · Inglês · ..." só serve pra
    # quem já lê português, e a legenda é justamente pra quem não lê. A sigla
    # em maiúscula é a mesma que aparece ao lado da faixa no vídeo, então o
    # espectador liga a linha da descrição com o que está vendo na tela.
    ordem = _idiomas_validos(idiomas)
    return SEPARADOR_IDIOMA.join(l.upper() for l in ordem)


def legenda_youtube_basica(classes: list[str] | None = None,
                           idioma: str = "en") -> str:
    """Legenda curta, num idioma só -- o bloco que o YouTube tem chance de
    traduzir automaticamente pra quem assiste.

        🔴 verb
        🖤 noun

    Padrão inglês, que é a língua franca do público e a que o tradutor
    automático do YouTube costuma cobrir melhor como origem.
    """
    linhas = []
    for classe in (classes if classes is not None else ORDEM_FREQUENCIA):
        if classe not in CORES_HTML:
            continue
        nome = NOMES_CLASSE_IDIOMA[classe].get(idioma, classe)
        linhas.append(f"{EMOJI_CLASSE[classe]} {NOME_COR_EN_CLASSE[classe]} — {nome}")
    return "\n".join(linhas)


def legenda_youtube_poliglota(classes: list[str] | None = None,
                              idiomas: list[str] | None = None,
                              com_exemplo: bool = True,
                              com_cabecalho: bool = True) -> str:
    """Legenda poliglota: o nome da classe em cada idioma e, opcionalmente,
    uma palavra de exemplo em cada um.

        PT · EN · ES · FR · Coreano · Chinês
        🔴 verbo · verb · verbo · verbe · 동사 · 动词 → andar · walk · andar · marcher · 걷다 · 走

    A posição é fixa: o 3º item é sempre espanhol, tenha exemplo ou não. Por
    isso idioma sem exemplo entra como "—" em vez de sumir -- se sumisse, o
    leitor contaria errado e atribuiria a palavra ao idioma errado. E o "—" é
    informação: mostra que aquela classe não existe naquele idioma.
    """
    ordem = _idiomas_validos(idiomas)
    linhas = [cabecalho_poliglota(ordem)] if com_cabecalho else []

    for classe in (classes if classes is not None else ORDEM_FREQUENCIA):
        if classe not in CORES_HTML:
            continue
        nomes = NOMES_CLASSE_IDIOMA[classe]
        parte_nomes = SEPARADOR_IDIOMA.join(nomes.get(l, classe) for l in ordem)
        linha = f"{EMOJI_CLASSE[classe]} {parte_nomes}"

        if com_exemplo:
            ex = EXEMPLOS_CLASSE[classe]
            parte_ex = SEPARADOR_IDIOMA.join(ex.get(l, SEM_EXEMPLO) for l in ordem)
            # Classe sem exemplo em idioma nenhum não ganha metade vazia.
            if parte_ex.replace(SEM_EXEMPLO, "").strip(SEPARADOR_IDIOMA + " "):
                linha = f"{linha} → {parte_ex}"
        linhas.append(linha)

    return "\n".join(linhas)


def legenda_youtube(classes: list[str] | None = None,
                    idiomas: list[str] | None = None) -> str:
    """Monta o bloco de legenda pra colar na descrição do YouTube:
    uma linha por classe, com o emoji da cor.

    `classes` limita/ordena a lista (ex: só as que aparecem num vídeo sem
    coreano); o padrão traz as 20 na ordem de CORES_HTML. `idiomas` ajusta os
    rótulos ao vídeo (ver nome_classe_legenda).
    """
    linhas = []
    for classe in (classes if classes is not None else ORDEM_FREQUENCIA):
        if classe not in CORES_HTML:
            continue
        linhas.append(f"{EMOJI_CLASSE[classe]} {nome_classe_legenda(classe, idiomas)}")
    return "\n".join(linhas)
