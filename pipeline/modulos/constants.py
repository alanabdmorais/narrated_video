# -*- coding: utf-8 -*-
"""
constants.py — Constantes imutáveis do pipeline.
BASE CORRIGIDA - Funciona para QUALQUER ORAÇÃO
"""

# ── Idiomas suportados ────────────────────────────────────────────────────────
# "zh" (chinês) NÃO entra nesta lista de propósito: ela é o default de
# config.IDIOMAS, e incluir o chinês aqui mudaria silenciosamente o
# comportamento dos fluxos de 5 idiomas que já rodam. Os dicts abaixo, sim,
# já trazem a entrada de "zh" -- são consultados por idioma (.get(lang)),
# então a entrada extra fica inerte até um notebook pedir "zh"
# explicitamente em IDIOMAS_ALVO (ver caption-*-zh-*.ipynb).
IDIOMAS: list[str] = ["en", "pt", "es", "fr", "ko"]

SIGLAS_IDIOMAS: dict[str, str] = {
    "pt": "PT-BR",
    "en": "EN-US",
    "es": "ES-ES",
    "fr": "FR-FR",
    "ko": "KO-KR",
    "zh": "ZH-CN",   # chinês simplificado (zh-Hans) -- ver NOMES_IDIOMA
}

NOMES_IDIOMA: dict[str, str] = {
    "pt": "português",
    "en": "inglês",
    "es": "espanhol",
    "fr": "francês",
    "ko": "coreano",
    "zh": "chinês",
}

# ── Posições das legendas na tela (pixels, tela 1280px) ──────────────────────
# 6 faixas de 80px: a última (zh, y=500) ainda cabe folgado nos 720px de
# altura -- a legenda fica centrada em an2 (centro-baixo) na posição dada.
#
# O INGLÊS VEM PRIMEIRO. É o idioma anfitrião do canal: é ele que o YouTube
# usa como origem da tradução automática, é a língua da narração, e é a linha
# que a maior parte do público lê. As outras cinco acompanham embaixo.
#
# Esta ordem é a MESMA na descrição do YouTube e no card de legenda -- é ela
# que o `sorted(idiomas, key=POSICOES_Y.get)` espalha pros outros lugares.
# Mudar aqui move a pilha da tela E a ordem das legendas junto, de propósito:
# ordem diferente em cada lugar obriga o espectador a reaprender.
#
# Vizinho não pode se parecer com vizinho (as cores estão em
# config.CORES_IDIOMAS). Com o inglês na frente, amarelo (pt) passa a ficar
# encostado em laranja (es): medido, ΔE*ab 52,9 -- mais folgado que o par
# rosa/roxo (ko/zh, ΔE 44,4) que já estava valendo. Nenhuma cor precisou mudar.
POSICOES_Y: dict[str, int] = {"en": 100, "pt": 180, "es": 260, "fr": 340, "ko": 420, "zh": 500}
POS_SIGLA_Y: dict[str, int] = {"en": 65, "pt": 145, "es": 225, "fr": 305, "ko": 385, "zh": 465}

# ── Dimensões da tela ─────────────────────────────────────────────────────────
LARGURA_TELA: int = 1280
ALTURA_TELA: int = 720
CENTRO_X: int = LARGURA_TELA // 2

# ── Fontes e layout ───────────────────────────────────────────────────────────
TAMANHO_FONTE_TAG: int = 24
TAMANHO_FONTE_SIGLA: int = 20
BOX_BORDER: int = 6
ESPACAMENTO_PALAVRA: int = 40
LARGURA_CHAR: int = 12

# ── CORES DAS CLASSES GRAMATICAIS (HTML #RRGGBB) ──────────────────────────────
CORES_HTML: dict[str, str] = {
    # SUBSTANTIVOS
    "substantivo_masculino_singular": "#4169E1",
    "substantivo_masculino_plural":   "#1E3A8A",
    "substantivo_feminino_singular":  "#FF1493",
    "substantivo_feminino_plural":    "#C71585",
    # PRONOMES
    "pronome_possessivo_singular":    "#006400",
    "pronome_possessivo_plural":      "#004D00",
    "pronome_relativo":               "#FFD700",
    "pronome_pessoal":                "#008080",
    "pronome_indefinido":             "#20B2AA",
    "pronome_demonstrativo":          "#9370DB",
    "pronome_interrogativo":          "#FF6347",
    "pronome_reflexivo":              "#2E8B57",
    "pronome_objeto":                 "#87CEEB",
    "pronome_obliquo":                "#000080",
    # VERBOS
    "verbo_presente":                 "#9B59B6",
    "verbo_passado":                  "#4A235A",
    "verbo_futuro":                   "#1ABC9C",
    "verbo_imperativo":               "#E67E22",
    "verbo_condicional":              "#F39C12",
    "verbo_subjuntivo":               "#8E44AD",
    "verbo_gerundio":                 "#D35400",
    "verbo_modal":                    "#E6E6FA",
    "verbo_auxiliar":                 "#3498DB",
    "verbo_futuro_proximo":           "#32CD32",
    "verbo_infinito":                 "#9B59B6",      # mesma do presente
    # ADJETIVOS
    "adjetivo_normal":                "#E74C3C",
    "adjetivo_comparativo":           "#CC5500",
    "adjetivo_superlativo":           "#B22222",
    # ADVÉRBIOS
    "advérbio_normal":                "#16A085",
    "advérbio_intensificador":        "#27AE60",
    # OUTROS
    "preposicao":                     "#FF8C00",
    "artigo_definido":                "#D3D3D3",
    "artigo_indefinido":              "#BDC3C7",
    "conjuncao":                      "#8B4513",
    "interjeicao":                    "#FF69B4",
    # PARTICULARIDADES
    "futuro_going_to":                "#32CD32",
    "comparativo_superlativo":        "#8B0000",
    "pronome_it":                     "#A9A9A9",
    "usted":                          "#DDA0DD",
    "voseo":                          "#FFA500",
    "lo_neutro":                      "#C0C0C0",
    "se_impessoal":                   "#98FB98",
    "preterito_perfecto":             "#8B008B",
    "subjuntivo_es":                  "#FF7F50",
    "imperativo_pronome":             "#CC5500",
    "passe_compose":                  "#BA55D3",
    "imparfait":                      "#C39BD3",
    "plus_que_parfait":               "#4A235A",
    "subjonctif_fr":                  "#8E44AD",      # mesma do subjuntivo
    "conditionnel":                   "#B8860B",
    "futur_proche":                   "#90EE90",
    "pronome_adverbial":              "#89CFF0",
    "artigo_partitivo":               "#EAEAEA",
    "concordancia_adjetivo":          "#FF00FF",
    "vos_portugues":                  "#009C3B",
    "colocacao_pronominal":           "#F28500",
    "futuro_subjuntivo":              "#8B0000",
    "gerundio_participio":            "#800080",
}

# ── CORES BÁSICAS (modo simplificado) ────────────────────────────────────────
# Substantivos: mesmas variações de gênero/número
# Adjetivos: variações de gênero/número
# Verbos: principal vs auxiliar/modal
# Demais classes: 1 cor única por classe

CORES_HTML_BASICO: dict[str, str] = {
    # SUBSTANTIVOS (mantém variações de gênero/número)
    "substantivo_masculino_singular": "#64B5F6",   # azul claro
    "substantivo_masculino_plural":   "#1565C0",   # azul escuro
    "substantivo_feminino_singular":  "#F48FB1",   # rosa claro
    "substantivo_feminino_plural":    "#AD1457",   # rosa escuro
    "substantivo_neutro":             "#B0BEC5",   # cinza azulado

    # ADJETIVOS (mantém variações de gênero/número)
    "adjetivo_masculino_singular":    "#A5D6A7",   # verde claro
    "adjetivo_masculino_plural":      "#2E7D32",   # verde escuro
    "adjetivo_feminino_singular":     "#FFCC80",   # laranja claro
    "adjetivo_feminino_plural":       "#E65100",   # laranja escuro
    "adjetivo_neutro_singular":       "#E0E0E0",   # cinza claro
    "adjetivo_neutro_plural":         "#757575",   # cinza escuro

    # VERBOS (principal vs auxiliar/modal)
    "verbo":                          "#EF5350",   # vermelho
    "verbo_auxiliar_modal":           "#FF8A65",   # salmão

    # DEMAIS CLASSES (1 cor por classe)
    "pronome":                        "#CE93D8",   # lilás
    "artigo":                         "#80DEEA",   # ciano claro
    "preposicao":                     "#FFF176",   # amarelo
    "conjuncao":                      "#BCAAA4",   # marrom claro
    "adverbio":                       "#C8E6C9",   # verde menta
    "interjeicao":                    "#FFFFFF",   # branco
}

# Cores básicas com texto PRETO (fundos claros)
TEXTO_PRETO_BASICO: set[str] = {
    "artigo", "preposicao", "adverbio", "interjeicao",
    "substantivo_neutro", "adjetivo_neutro_singular",
    "adjetivo_masculino_singular",
}

# Mapeamento: classes detalhadas → classes básicas
MAPA_CLASSE_BASICA: dict[str, str] = {
    # Substantivos → mantém gênero/número
    "substantivo_masculino_singular": "substantivo_masculino_singular",
    "substantivo_masculino_plural":   "substantivo_masculino_plural",
    "substantivo_feminino_singular":  "substantivo_feminino_singular",
    "substantivo_feminino_plural":    "substantivo_feminino_plural",
    # qualquer substantivo sem gênero → neutro
    "substantivo_neutro":             "substantivo_neutro",

    # Adjetivos → mantém gênero/número
    "adjetivo_normal":                "adjetivo_masculino_singular",
    "adjetivo_comparativo":           "adjetivo_masculino_singular",
    "adjetivo_superlativo":           "adjetivo_masculino_singular",
    "comparativo_superlativo":        "adjetivo_masculino_singular",
    "concordancia_adjetivo":          "adjetivo_masculino_singular",
    # com sufixo de gênero/número serão mapeados por nome abaixo

    # Verbos principais → verbo
    "verbo_presente":                 "verbo",
    "verbo_passado":                  "verbo",
    "verbo_futuro":                   "verbo",
    "verbo_imperativo":               "verbo",
    "verbo_condicional":              "verbo",
    "verbo_subjuntivo":               "verbo",
    "verbo_gerundio":                 "verbo",
    "verbo_infinito":                 "verbo",
    "verbo_futuro_proximo":           "verbo",
    "gerundio_participio":            "verbo",
    "futuro_going_to":                "verbo",
    "preterito_perfecto":             "verbo",
    "passe_compose":                  "verbo",
    "imparfait":                      "verbo",
    "plus_que_parfait":               "verbo",
    "subjonctif_fr":                  "verbo",
    "conditionnel":                   "verbo",
    "futur_proche":                   "verbo",
    "subjuntivo_es":                  "verbo",
    "imperativo_pronome":             "verbo",

    # Verbos auxiliares/modais → verbo_auxiliar_modal
    "verbo_modal":                    "verbo_auxiliar_modal",
    "verbo_auxiliar":                 "verbo_auxiliar_modal",

    # Pronomes → pronome
    "pronome_possessivo_singular":    "pronome",
    "pronome_possessivo_plural":      "pronome",
    "pronome_relativo":               "pronome",
    "pronome_pessoal":                "pronome",
    "pronome_indefinido":             "pronome",
    "pronome_demonstrativo":          "pronome",
    "pronome_interrogativo":          "pronome",
    "pronome_reflexivo":              "pronome",
    "pronome_objeto":                 "pronome",
    "pronome_obliquo":                "pronome",
    "pronome_it":                     "pronome",
    "pronome_adverbial":              "pronome",
    "usted":                          "pronome",
    "voseo":                          "pronome",
    "lo_neutro":                      "pronome",
    "se_impessoal":                   "pronome",
    "colocacao_pronominal":           "pronome",

    # Artigos → artigo
    "artigo_definido":                "artigo",
    "artigo_indefinido":              "artigo",
    "artigo_partitivo":               "artigo",

    # Preposição
    "preposicao":                     "preposicao",

    # Conjunção
    "conjuncao":                      "conjuncao",

    # Advérbio
    "advérbio_normal":                "adverbio",
    "advérbio_intensificador":        "adverbio",

    # Interjeição
    "interjeicao":                    "interjeicao",

    # Outros sem categoria clara → pronome (fallback)
    "vos_portugues":                  "pronome",
    "futuro_subjuntivo":              "verbo",
}


def classe_para_basica(classe_detalhada: str) -> str:
    """Converte classe detalhada para classe básica."""
    # Adjetivos com sufixo de gênero/número
    if "adjetivo" in classe_detalhada:
        if "masculino_singular" in classe_detalhada: return "adjetivo_masculino_singular"
        if "masculino_plural"   in classe_detalhada: return "adjetivo_masculino_plural"
        if "feminino_singular"  in classe_detalhada: return "adjetivo_feminino_singular"
        if "feminino_plural"    in classe_detalhada: return "adjetivo_feminino_plural"
        if "neutro_plural"      in classe_detalhada: return "adjetivo_neutro_plural"
        if "neutro"             in classe_detalhada: return "adjetivo_neutro_singular"
        return "adjetivo_masculino_singular"
    # Substantivo neutro
    if "substantivo_neutro" in classe_detalhada:
        return "substantivo_neutro"
    return MAPA_CLASSE_BASICA.get(classe_detalhada, "substantivo_neutro")


# Prompt para classificação básica
PROMPT_SISTEMA_CLASSIFICACAO_BASICO = (
    "Você é um especialista em linguística. "
    "Classifique cada palavra usando SOMENTE as classes abaixo.\n\n"
    "CLASSES PERMITIDAS:\n"
    "Substantivos (indique gênero e número):\n"
    "  substantivo_masculino_singular, substantivo_masculino_plural,\n"
    "  substantivo_feminino_singular, substantivo_feminino_plural, substantivo_neutro\n\n"
    "Adjetivos (indique gênero e número):\n"
    "  adjetivo_masculino_singular, adjetivo_masculino_plural,\n"
    "  adjetivo_feminino_singular, adjetivo_feminino_plural,\n"
    "  adjetivo_neutro_singular, adjetivo_neutro_plural\n\n"
    "Verbos:\n"
    "  verbo (principal), verbo_auxiliar_modal (auxiliar ou modal)\n\n"
    "Outras classes (1 classe, sem variação):\n"
    "  pronome, artigo, preposicao, conjuncao, adverbio, interjeicao\n\n"
    "REGRAS:\n"
    "1. NÃO inclua pontuação (',', '.', '-', '!', '?', ';', ':') na lista\n"
    "2. NÃO invente classes que não estejam na lista acima\n"
    "3. Verbos auxiliares e modais (will, have, être, haber, ter, poder) → verbo_auxiliar_modal\n"
    "4. Todos os outros verbos → verbo\n\n"
    'Retorne SOMENTE JSON: {"palavras": [{"texto": "palavra", "classe": "classe"}]}'
)

# Cores que usam texto PRETO (fundos claros)
TEXTO_PRETO: set[str] = {
    "pronome_relativo", "artigo_definido", "artigo_indefinido",
    "verbo_modal", "pronome_it", "usted", "lo_neutro", "se_impessoal",
    "imparfait", "futur_proche", "pronome_adverbial", "artigo_partitivo",
}

# ── MAPEAMENTO DE NORMALIZAÇÃO (inglês → português) ───────────────────────────
MAPEAMENTO_CLASSES: dict[str, str] = {
    "noun": "substantivo_masculino_singular",
    "verb": "verbo_presente",
    "pronoun": "pronome_pessoal",
    "preposition": "preposicao",
    "adjective": "adjetivo_normal",
    "adverb": "advérbio_normal",
    "conjunction": "conjuncao",
    "determiner": "artigo_definido",
    "article": "artigo_definido",
    "interjection": "interjeicao",
    "possessive_pronoun": "pronome_possessivo_singular",
    "relative_pronoun": "pronome_relativo",
    "personal_pronoun": "pronome_pessoal",
    "present_verb": "verbo_presente",
    "past_verb": "verbo_passado",
    "modal_verb": "verbo_modal",
    "auxiliary_verb": "verbo_auxiliar",
    "gerund": "verbo_gerundio",
    "participle": "gerundio_participio",
    "adverbio_normal": "advérbio_normal",
    "conjunção": "conjuncao",
    "verbo_infinito": "verbo_presente",
    "subjonctif_fr": "verbo_subjuntivo",
}

# ── CORREÇÕES AUTOMÁTICAS POR PALAVRA (QUALQUER IDIOMA) ───────────────────────
CORRECOES_GLOBAIS: dict[str, str] = {
    "que": "pronome_relativo",      # PT, ES, FR
    "qui": "pronome_relativo",      # FR
    "which": "pronome_relativo",    # EN
    "who": "pronome_relativo",      # EN
    "that": "pronome_relativo",     # EN
    "como": "conjuncao",            # PT, ES
    "as": "conjuncao",              # EN
    "comme": "conjuncao",           # FR
    "thy": "pronome_possessivo_singular",   # EN — possuidor "thou" (2ª sing.)
    "thine": "pronome_possessivo_singular", # EN — possuidor "thou" (2ª sing.)
    "our": "pronome_possessivo_plural",     # EN — possuidor "we" (1ª plural)
    "nosso": "pronome_possessivo_plural",   # PT — possuidor "nós" (1ª plural)
    "nossa": "pronome_possessivo_plural",   # PT — possuidor "nós" (1ª plural)
    "nossos": "pronome_possessivo_plural",  # PT — possuidor "nós" (1ª plural)
    "nossas": "pronome_possessivo_plural",  # PT — possuidor "nós" (1ª plural)
    "nuestro": "pronome_possessivo_plural",  # ES — possuidor "nosotros" (1ª plural)
    "nuestra": "pronome_possessivo_plural",  # ES — possuidor "nosotros" (1ª plural)
    "nuestros": "pronome_possessivo_plural", # ES — possuidor "nosotros" (1ª plural)
    "nuestras": "pronome_possessivo_plural", # ES — possuidor "nosotros" (1ª plural)
}

CORRECOES_POR_IDIOMA: dict[str, dict[str, str]] = {
    "es": {"tu": "pronome_possessivo_singular"},   # ES — possuidor "tú" (2ª sing.)
    "fr": {
        "votre": "pronome_possessivo_plural",   # FR — possuidor "vous" (2ª plural)
        "notre": "pronome_possessivo_plural",   # FR — possuidor "nous" (1ª plural)
    },
    "pt": {
        "vosso": "pronome_possessivo_plural",   # PT — possuidor "vós" (2ª plural)
        "vossa": "pronome_possessivo_plural",   # PT — possuidor "vós" (2ª plural)
    },
}

# ── FUNÇÃO DE NORMALIZAÇÃO (usa as regras acima) ──────────────────────────────
def normalizar_classe(classe: str, palavra: str = "", idioma: str = "") -> str:
    """Normaliza classe gramatical aplicando correções automáticas."""
    palavra_lower = palavra.lower()
    
    # Correção por palavra (global)
    if palavra_lower in CORRECOES_GLOBAIS:
        return CORRECOES_GLOBAIS[palavra_lower]
    
    # Correção específica por idioma
    if idioma in CORRECOES_POR_IDIOMA and palavra_lower in CORRECOES_POR_IDIOMA[idioma]:
        return CORRECOES_POR_IDIOMA[idioma][palavra_lower]
    
    # Mapeamento geral
    return MAPEAMENTO_CLASSES.get(classe, classe)

# ── PROMPTS DO GROQ (OTIMIZADOS PARA QUALQUER ORAÇÃO) ─────────────────────────
PROMPT_SISTEMA_CORRECAO_PT = (
    "Você é um especialista em português e textos religiosos. "
    "Corrija APENAS erros de transcrição, mantendo a segmentação exata. "
    "Retorne SOMENTE um JSON válido. "
    'Formato: [{"id": 1, "texto": "frase corrigida"}, ...]'
)

PROMPT_SISTEMA_REDISTRIBUICAO = (
    "Você é um especialista em alinhamento de legendas multilíngues. "
    "Redistribua o texto em exatamente {N} segmentos seguindo os cortes do idioma de origem. "
    "Mantenha o sentido litúrgico e naturalidade no idioma de destino. "
    "Retorne SOMENTE um JSON válido. "
    'Formato: [{{"id": 1, "texto": "frase em {idioma}"}}]'
)

PROMPT_SISTEMA_CLASSIFICACAO = (
    "Você é um especialista em linguística. "
    "Classifique cada palavra da legenda usando SOMENTE as classes fornecidas. "
    "\n\nREGRAS OBRIGATÓRIAS (para TODOS os idiomas):"
    "\n1. A palavra 'que' em PT/ES/FR é SEMPRE pronome_relativo (NUNCA conjuncao)."
    "\n2. 'thy'/'thine' em INGLÊS são pronome_possessivo_singular (possuidor 'thou', 2ª pessoa do singular)."
    "\n3. 'our' em INGLÊS é pronome_possessivo_plural (possuidor 'we', 1ª pessoa do plural)."
    "\n4. 'tu' em espanhol antes de substantivo é pronome_possessivo_singular (possuidor 'tú', 2ª singular)."
    "\n5. 'votre' e 'notre' em FRANCÊS são pronome_possessivo_plural (possuidores 'vous'/'nous', plural)."
    "\n6. 'vosso'/'vossa' em PORTUGUÊS são pronome_possessivo_plural (possuidor 'vós', plural)."
    "\n7. 'nosso'/'nossa'/'nossos'/'nossas' em PORTUGUÊS são pronome_possessivo_plural (possuidor 'nós', plural)."
    "\n8. 'nuestro'/'nuestra'/'nuestros'/'nuestras' em ESPANHOL são pronome_possessivo_plural (possuidor 'nosotros', plural)."
    "\n9. Verbos no infinitivo são verbo_presente."
    "\n10. Subjuntivo em francês é verbo_subjuntivo."
    "\n\nRetorne SOMENTE JSON. Formato: {{\"palavras\": [{{\"texto\": \"palavra\", \"classe\": \"classe\"}}]}}"
)

# ── FASES DO PIPELINE (checkpoint) ───────────────────────────────────────────
FASES_PIPELINE: list[str] = [
    "audio_gerado", "transcricao_whisper_gerada",
    "legendas_youtube_baixadas", "audio_idiomas_baixados", "audio_idiomas_transcritos",
    "srt_pt_bruto", "srt_pt_corrigido",
    "srt_traduzidos", "classificacoes_feitas", "clipes_cortados",
    "video_base_criado", "legendas_queimadas", "legenda_versiculo_gerada", "legendas_idiomas_queimadas",
]

# ── VOCABULÁRIO LITÚRGICO (para revisão) ─────────────────────────────────────
EXEMPLOS_LITURGICOS: dict[str, str] = {
    "en": "thy/thine/art/hallowed/trespass/forgive us our trespasses",
    "es": "santificado/venga/hágase/perdónanos/deudas/líbranos",
    "fr": "ton/que ton nom soit sanctifié/pardonne-nous/délivre-nous",
}