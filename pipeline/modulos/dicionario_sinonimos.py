# -*- coding: utf-8 -*-
"""
dicionario_sinonimos.py — Grupos de palavras equivalentes, PT e EN, pra
expandir Tags_Semelhantes_PT/EN tanto do lado da Bíblia (versículo/
título/evento) quanto do lado das imagens (Tags_PT/EN da image-stock).

Cada grupo é uma lista de palavras/expressões que devem "casar" entre si
no match -- ex: uma imagem taggeada "bebê" deve aparecer como candidata
pra um versículo taggeado "criança", mesmo sem a palavra exata bater.
Os grupos PT e EN estão na MESMA ORDEM (grupo N do PT corresponde ao
grupo N do EN) -- não é usado pra tradução aqui, só mantém os dois
dicionários organizados/fáceis de conferir lado a lado.

Curado manualmente, focado em vocabulário visual/bíblico -- vai crescer
conforme aparecerem mais casos reais na revisão.
"""

GRUPOS_SINONIMOS_PT = [
    # ── pessoas / família ──────────────────────────────────────────────
    ["criança", "crianças", "bebê", "bebês", "infante", "menino", "menina", "filho", "filha", "filhos"],
    ["jovem", "jovens", "rapaz", "moça", "adolescente"],
    ["idoso", "idosos", "velho", "velha", "ancião", "anciã", "anciãos"],
    ["homem", "homens", "varão"],
    ["mulher", "mulheres"],
    ["família", "famílias", "parentes", "parentesco"],
    ["irmão", "irmãos", "irmã", "irmãs"],
    ["multidão", "multidões", "povo", "gente", "massa", "aglomeração"],
    ["pai", "pais", "progenitor"],
    ["mãe", "mães", "progenitora"],

    # ── autoridade / religião ────────────────────────────────────────
    ["rei", "reis", "monarca", "soberano", "governante"],
    ["rainha", "rainhas"],
    ["sacerdote", "sacerdotes", "padre", "clérigo", "sumo sacerdote"],
    ["profeta", "profetas", "profetisa"],
    ["anjo", "anjos", "mensageiro celestial", "ser celestial"],
    ["discípulo", "discípulos", "apóstolo", "apóstolos", "seguidor", "seguidores"],
    ["pastor", "pastores", "cuidador de ovelhas"],
    ["escriba", "escribas", "fariseu", "fariseus", "doutor da lei"],
    ["soldado", "soldados", "guerreiro", "guerreiros", "guarda", "guardas"],

    # ── natureza / lugar ────────────────────────────────────────────
    ["deserto", "deserto árido", "ermo", "terra árida", "areia"],
    ["montanha", "montanhas", "monte", "montes", "colina", "colinas"],
    ["mar", "oceano", "águas profundas"],
    ["rio", "rios", "riacho", "córrego", "ribeirão"],
    ["céu", "céus", "firmamento"],
    ["estrela", "estrelas", "astro", "constelação"],
    ["noite", "escuridão", "trevas", "anoitecer"],
    ["dia", "luz do dia", "amanhecer", "alvorecer", "aurora"],
    ["luz", "claridade", "brilho", "resplendor", "fulgor"],
    ["nuvem", "nuvens", "nevoeiro"],
    ["chuva", "tempestade", "temporal", "trovão", "trovões", "relâmpago", "relâmpagos", "raio", "raios"],
    ["árvore", "árvores", "floresta", "bosque"],
    ["campo", "campos", "plantação", "lavoura", "seara"],
    ["caverna", "gruta", "cova", "gruta rochosa"],

    # ── estruturas / lugares construídos ──────────────────────────
    ["templo", "santuário", "casa de oração", "lugar sagrado"],
    ["casa", "lar", "moradia", "residência", "habitação"],
    ["cidade", "cidades", "vila", "povoado", "vilarejo"],
    ["palácio", "palácios", "corte real"],
    ["prisão", "cárcere", "masmorra", "cadeia"],
    ["tumba", "túmulo", "sepulcro", "sepultura"],
    ["cruz", "crucifixo"],
    ["altar", "altares"],
    ["trono", "tronos"],

    # ── ações ──────────────────────────────────────────────────────
    ["caminhar", "andar", "viajar", "jornada", "peregrinação", "travessia"],
    ["orar", "rezar", "suplicar", "clamar", "invocar"],
    ["curar", "cura", "curando", "curado", "saúde restaurada"],
    ["ensinar", "ensinando", "pregar", "pregando", "prédica", "sermão"],
    ["chorar", "choro", "lágrimas", "lamento", "pranto"],
    ["celebrar", "celebração", "festa", "banquete", "festejo"],
    ["adorar", "adoração", "louvor", "louvar", "reverência"],
    ["fugir", "fuga", "fugindo", "escapar", "refúgio"],

    # ── objetos ────────────────────────────────────────────────────
    ["espada", "espadas", "arma", "armas"],
    ["coroa", "coroas", "diadema"],
    ["pão", "pães", "alimento", "comida"],
    ["vinho", "taça", "cálice"],
    ["barco", "barcos", "navio", "embarcação"],
    ["lâmpada", "lâmpadas", "candeeiro", "vela", "chama"],
    ["manjedoura", "presépio", "berço"],

    # ── animais ────────────────────────────────────────────────────
    ["ovelha", "ovelhas", "cordeiro", "cordeiros", "rebanho"],
    ["leão", "leões"],
    ["burro", "jumento", "asno"],
    ["peixe", "peixes"],
    ["pomba", "pombas", "ave", "aves", "pássaro", "pássaros"],

    # ── emoções / estados ──────────────────────────────────────────
    ["alegria", "felicidade", "contentamento", "júbilo", "regozijo"],
    ["tristeza", "dor", "sofrimento", "angústia", "aflição"],
    ["medo", "temor", "pavor", "terror"],
    ["paz", "tranquilidade", "serenidade", "calma"],
    ["esperança", "confiança", "fé"],
    ["milagre", "milagroso", "prodígio", "maravilha"],

    # ── sons / efeitos sonoros ───────────────────────────────────────
    # Objetos/ações concretas cujo interesse principal é o SOM que fazem
    # (efeito sonoro pontual) -- ver trilha_pipeline.py/efeitos_stock.
    # Trovão/relâmpago já vivem dentro do grupo "chuva" acima (mesmo
    # contexto de tempestade); os demais entram aqui por serem sons sem
    # um "lugar" natural nas categorias visuais/narrativas de cima.
    ["porta", "portas", "portão", "portões"],
    ["cavalo", "cavalos", "égua", "corcel", "carruagem", "carruagens"],
    ["vento", "ventania", "brisa", "rajada"],
    ["fogo", "chamas", "labareda", "labaredas", "incêndio", "fornalha"],
    ["trombeta", "trombetas", "shofar", "chifre de carneiro", "buzina"],
    ["passos", "passo", "pisada", "pisadas"],
    ["galo", "cantar do galo", "canto do galo"],
    ["terremoto", "tremor de terra", "abalo sísmico"],
]

GRUPOS_SINONIMOS_EN = [
    # ── people / family ──────────────────────────────────────────────
    ["child", "children", "baby", "babies", "infant", "boy", "girl", "son", "daughter", "kid", "kids"],
    ["youth", "young man", "young woman", "teenager", "adolescent"],
    ["elder", "elders", "old man", "old woman", "elderly"],
    ["man", "men"],
    ["woman", "women"],
    ["family", "families", "relatives", "kin"],
    ["brother", "brothers", "sister", "sisters"],
    ["crowd", "crowds", "people", "multitude", "throng"],
    ["father", "fathers", "dad"],
    ["mother", "mothers", "mom"],

    # ── authority / religion ────────────────────────────────────────
    ["king", "kings", "monarch", "sovereign", "ruler"],
    ["queen", "queens"],
    ["priest", "priests", "clergyman", "high priest"],
    ["prophet", "prophets", "prophetess"],
    ["angel", "angels", "heavenly messenger", "celestial being"],
    ["disciple", "disciples", "apostle", "apostles", "follower", "followers"],
    ["shepherd", "shepherds"],
    ["scribe", "scribes", "pharisee", "pharisees", "teacher of the law"],
    ["soldier", "soldiers", "warrior", "warriors", "guard", "guards"],

    # ── nature / place ────────────────────────────────────────────
    ["desert", "arid desert", "wilderness", "dry land", "sand"],
    ["mountain", "mountains", "mount", "hill", "hills"],
    ["sea", "ocean", "deep waters"],
    ["river", "rivers", "stream", "creek", "brook"],
    ["sky", "heaven", "heavens", "firmament"],
    ["star", "stars", "constellation"],
    ["night", "darkness", "dusk", "nightfall"],
    ["day", "daylight", "dawn", "sunrise"],
    ["light", "brightness", "radiance", "glow"],
    ["cloud", "clouds", "fog", "mist"],
    ["rain", "storm", "tempest", "thunder", "thunderclap", "lightning", "lightning bolt"],
    ["tree", "trees", "forest", "woods"],
    ["field", "fields", "crop", "farmland", "harvest"],
    ["cave", "grotto", "cavern", "rocky cave"],

    # ── structures / built places ──────────────────────────────
    ["temple", "sanctuary", "house of prayer", "holy place"],
    ["house", "home", "dwelling", "residence", "abode"],
    ["city", "cities", "village", "town"],
    ["palace", "palaces", "royal court"],
    ["prison", "jail", "dungeon"],
    ["tomb", "grave", "sepulcher", "sepulchre"],
    ["cross", "crucifix"],
    ["altar", "altars"],
    ["throne", "thrones"],

    # ── actions ──────────────────────────────────────────────────────
    ["walk", "walking", "travel", "journey", "pilgrimage", "crossing"],
    ["pray", "praying", "plead", "beg", "invoke"],
    ["heal", "healing", "healed", "restored health"],
    ["teach", "teaching", "preach", "preaching", "sermon"],
    ["cry", "crying", "tears", "weeping", "mourning"],
    ["celebrate", "celebration", "feast", "banquet", "festivity"],
    ["worship", "adoration", "praise", "reverence"],
    ["flee", "flight", "fleeing", "escape", "refuge"],

    # ── objects ────────────────────────────────────────────────────
    ["sword", "swords", "weapon", "weapons"],
    ["crown", "crowns", "diadem"],
    ["bread", "loaves", "food"],
    ["wine", "cup", "chalice", "goblet"],
    ["boat", "boats", "ship", "vessel"],
    ["lamp", "lamps", "candle", "candlestick", "flame"],
    ["manger", "nativity crib", "cradle"],

    # ── animals ────────────────────────────────────────────────────
    ["sheep", "lamb", "lambs", "flock"],
    ["lion", "lions"],
    ["donkey", "colt", "ass"],
    ["fish", "fishes"],
    ["dove", "doves", "bird", "birds"],

    # ── emotions / states ──────────────────────────────────────────
    ["joy", "happiness", "gladness", "delight", "rejoicing"],
    ["sadness", "sorrow", "suffering", "anguish", "distress"],
    ["fear", "dread", "terror"],
    ["peace", "tranquility", "serenity", "calm"],
    ["hope", "trust", "faith"],
    ["miracle", "miraculous", "wonder", "marvel"],

    # ── sounds / sound effects ───────────────────────────────────────
    ["door", "doors", "gate", "gates"],
    ["horse", "horses", "mare", "steed", "chariot", "chariots"],
    ["wind", "windstorm", "breeze", "gust"],
    ["fire", "flames", "blaze", "inferno", "furnace"],
    ["trumpet", "trumpets", "shofar", "ram's horn", "horn"],
    ["footsteps", "footstep", "steps", "walking sound"],
    ["rooster", "rooster crow", "cock crow"],
    ["earthquake", "tremor", "seismic shock"],
]


def _construir_mapa(grupos):
    import unicodedata

    def normalizar(s):
        nfkd = unicodedata.normalize("NFD", s.lower().strip())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    mapa = {}
    for grupo in grupos:
        for palavra in grupo:
            mapa[normalizar(palavra)] = grupo  # guarda o grupo ORIGINAL (com acento, pra exibir bonito)
    return mapa


MAPA_SINONIMOS_PT = _construir_mapa(GRUPOS_SINONIMOS_PT)
MAPA_SINONIMOS_EN = _construir_mapa(GRUPOS_SINONIMOS_EN)


def expandir_tags_semelhantes(tags, idioma="pt"):
    """
    Recebe uma lista (ou string separada por vírgula) de tags e devolve
    a lista expandida -- cada tag que tem sinônimo conhecido traz o
    GRUPO INTEIRO junto (a tag original sempre continua incluída).

    idioma: "pt" ou "en" -- escolhe qual dicionário usar.

    Determinístico, sem IA -- só dicionário. Pode rodar pra Bíblia
    inteira (título/evento) de uma vez, sem custo de API nem espera.
    """
    import unicodedata

    def normalizar(s):
        nfkd = unicodedata.normalize("NFD", s.lower().strip())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    mapa = MAPA_SINONIMOS_EN if idioma == "en" else MAPA_SINONIMOS_PT

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    expandido = list(dict.fromkeys(tags))  # preserva original, remove duplicata mantendo ordem
    for tag in tags:
        chaves_a_testar = [normalizar(tag)]
        # tag pode ser uma FRASE ("rei Herodes", "cidade de Jerusalém") -- o
        # dicionário é de PALAVRA SOLTA ("rei", "cidade"), então só testar a
        # frase inteira quase nunca bate. Testa cada palavra da frase também
        # (sem duplicar o teste se a "frase" já for uma palavra só).
        palavras = normalizar(tag).split()
        if len(palavras) > 1:
            chaves_a_testar += palavras
        for chave in chaves_a_testar:
            grupo = mapa.get(chave)
            if grupo:
                for sinonimo in grupo:
                    if sinonimo not in expandido:
                        expandido.append(sinonimo)
    return expandido
