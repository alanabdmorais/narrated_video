# -*- coding: utf-8 -*-
"""
match_pipeline.py — Match cena↔roteiro (versículo → vídeo/imagem da biblioteca)

Fluxo (híbrido léxico + IA — padrão usado por sistemas profissionais de MAM/DAM:
vocabulário controlado primeiro, IA só de reforço, revisão humana no final):
    1. carregar_lexico_biblico() — carrega titulos-biblicos.js/eventos-biblicos.js
                                    (convertidos pra JSON) do projeto Glossário
    2. buscar_contexto_biblico() — pra um livro/capítulo/versículo, acha o
                                    título de seção (ARC) e o evento + personagens
                                    -- sem IA, busca determinística e grátis
    3. sugerir_tags_lexico()     — tenta montar tags_biblia + palavras_chave
                                    SÓ com esse contexto (sem chamar IA)
    4. sugerir_tags_versiculo()  — IA sugere palavras-chave + tags_biblia pra
                                    um versículo -- usada só quando o léxico não
                                    achou nada, ou como contexto extra no prompt
                                    quando achou pouco (ver gerar_sugestoes_match)
    5. carregar_biblioteca()     — lê a planilha (vídeos OU imagens, mesma
                                    estrutura de colunas) e monta candidatos
    6. pontuar_candidatos()      — pontua cada candidato pela sobreposição
                                    de tags_biblia com o que foi sugerido
    7. gerar_sugestoes_match()   — orquestra tudo, versículo por versículo,
                                    com anti-repetição entre versículos
                                    próximos

Funciona igual pra vídeo ou imagem — só muda qual planilha/coluna de URL
é passada pra carregar_biblioteca().
"""
from __future__ import annotations

import json
import re
import time
import unicodedata


def carregar_lexico_biblico(caminho_titulos, caminho_eventos):
    """
    Carrega titulos-biblicos.json e eventos-biblicos.json (convertidos do
    titulos-biblicos.js/eventos-biblicos.js do projeto Glossário via Node --
    ver notebook: json.dump(require('titulos-biblicos.js')) num script .js
    à parte, já que são arquivos JS, não JSON puros).

    Retorna (titulos_biblicos, eventos_biblicos) prontos pra
    buscar_contexto_biblico().
    """
    with open(caminho_titulos, encoding="utf-8") as f:
        titulos_biblicos = json.load(f)
    with open(caminho_eventos, encoding="utf-8") as f:
        eventos_biblicos = json.load(f)
    return titulos_biblicos, eventos_biblicos


def _parse_referencia_evento(referencia, livro_pt):
    """
    Extrai (cap_inicio, cap_fim) de uma referência tipo "Mateus 1–2",
    "Mateus 4", "Mateus 13:1–23", "Lucas 7:18–50" -- só quando o livro bate
    com livro_pt. Ignora granularidade de versículo (eventos-biblicos.js é
    por CAPÍTULO/bloco, não por versículo -- isso é papel do
    titulos-biblicos.js). Retorna None se o livro não bate ou o formato é
    inesperado demais pra confiar.
    """
    if not referencia.startswith(livro_pt):
        return None
    resto = referencia[len(livro_pt):].strip()
    if not resto:
        return None
    # corta na primeira ":" (info de versículo, que aqui a gente ignora)
    resto = resto.split(":")[0].strip()
    # separador de range pode ser "–" (en dash) ou "-" (hifen comum)
    partes = re.split(r"[–—-]", resto)
    try:
        cap_inicio = int(re.sub(r"\D", "", partes[0]))
        cap_fim = int(re.sub(r"\D", "", partes[1])) if len(partes) > 1 and partes[1].strip() else cap_inicio
        return (cap_inicio, cap_fim)
    except (ValueError, IndexError):
        return None


def buscar_contexto_biblico(livro_pt, capitulo, versiculo, titulos_biblicos, eventos_biblicos):
    """
    Busca o contexto estruturado (léxico, sem IA) pra um versículo
    específico: o título de seção ARC (granularidade de versículo, vem de
    titulos-biblicos.js) e o evento/personagens (granularidade de
    capítulo/bloco, vem de eventos-biblicos.js).

    Retorna dict {"titulo_id":, "titulo_versiculo":, "evento_id":,
    "titulo_evento":, "personagens": []} -- qualquer campo pode vir
    None/vazio se não achou cobertura ali. Os campos "_id" são a CHAVE
    usada pela biblioteca de match (buscar_na_biblioteca_match) -- o
    mesmo título/evento sempre gera a mesma chave, então uma vez que um
    vídeo/imagem foi escolhido pra ele, fica salvo pra sempre.
    """
    contexto = {"titulo_id": None, "titulo_versiculo": None, "titulo_referencia": None,
                "evento_id": None, "titulo_evento": None, "evento_referencia": None,
                "personagens": []}

    # ── titulos-biblicos.js: granularidade de versículo ───────────────────
    for chave_id, entrada in titulos_biblicos.items():
        if (entrada.get("livro") == livro_pt and entrada.get("capitulo") == capitulo
                and entrada.get("vIni", 0) <= versiculo <= entrada.get("vFim", 0)):
            contexto["titulo_id"] = entrada.get("id", chave_id)
            contexto["titulo_versiculo"] = entrada.get("titulo")
            contexto["titulo_referencia"] = entrada.get("referencia")
            break

    # ── eventos-biblicos.js: granularidade de capítulo/bloco ──────────────
    for evento in eventos_biblicos:
        faixa = _parse_referencia_evento(evento.get("referencia", ""), livro_pt)
        if faixa and faixa[0] <= capitulo <= faixa[1]:
            contexto["evento_id"] = evento.get("id")
            contexto["titulo_evento"] = evento.get("titulo")
            contexto["evento_referencia"] = evento.get("referencia")
            contexto["personagens"] = evento.get("personagens", [])
            break

    return contexto


_STOPWORDS_PT = {"de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "em", "no", "na", "um", "uma"}


def _sem_acento(texto):
    """Remove acentos (NFD + descarta marcas combinantes) -- pra não depender
    de digitação idêntica entre a lista de tags e os títulos do léxico
    (ex: 'matança' vs 'matanca' devem casar)."""
    nfkd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokens_significativos(texto):
    return set(re.findall(r"\w+", _sem_acento(texto).lower())) - _STOPWORDS_PT


def _tags_com_match_estrito(texto, lista_tags_biblia):
    """
    Só considera a tag batida se TODAS as palavras significativas dela
    aparecem no texto (não só uma) -- evita falso positivo por causa de
    palavra genérica isolada (ex: "jesus", "deus", "anjo" aparecem em
    quase todo personagem e contaminavam o match quando bastava 1 palavra
    em comum).
    """
    palavras_texto = _tokens_significativos(texto)
    tags_batidas = []
    for tag in (t.strip() for t in lista_tags_biblia.split(",")):
        palavras_tag = _tokens_significativos(tag)
        if palavras_tag and palavras_tag.issubset(palavras_texto):
            tags_batidas.append(tag)
    return tags_batidas


def sugerir_tags_lexico(contexto, lista_tags_biblia):
    """
    Tenta montar tags_biblia + palavras_chave SÓ com o contexto do léxico
    (sem chamar IA) -- match estrito (todas as palavras da tag precisam
    aparecer) contra o título específico do versículo primeiro; só usa o
    título do evento/capítulo como plano B, e nunca usa `personagens`
    sozinho pra decidir tag (é genérico demais -- "Jesus"/"Deus" aparecem
    em quase toda cena e geram falso positivo).

    Retorna None se nada bateu com confiança (nesse caso quem chama deve
    cair pro caminho da IA). Quando acha, é grátis, instantâneo, e
    determinístico -- não gasta cota de API.
    """
    tags_batidas = []
    if contexto.get("titulo_versiculo"):
        tags_batidas = _tags_com_match_estrito(contexto["titulo_versiculo"], lista_tags_biblia)
    if not tags_batidas and contexto.get("titulo_evento"):
        tags_batidas = _tags_com_match_estrito(contexto["titulo_evento"], lista_tags_biblia)

    if not tags_batidas:
        return None  # nada bateu com confiança -- IA assume

    # palavras_chave: personagens (termos visuais concretos, aqui SÃO úteis
    # -- é só pra tag_biblia que são genéricos demais) + o título do
    # versículo, se houver (mais específico que o do evento)
    palavras_chave = list(dict.fromkeys(
        contexto.get("personagens", [])
        + ([contexto["titulo_versiculo"]] if contexto.get("titulo_versiculo") else [])
    ))[:4]

    return {"tags_biblia": tags_batidas, "palavras_chave": palavras_chave, "fonte": "lexico"}


def sugerir_tags_versiculo(texto_versiculo, lista_tags_biblia, groq_client, mistral_client,
                             estado_provedor, modelo_groq, modelo_mistral, max_tokens=300,
                             contexto=None):
    """
    Pede pra IA (texto só, sem imagem) sugerir palavras-chave visuais +
    tags da lista fechada de Bíblia pra um versículo específico.

    Usa a mesma rotação Groq↔Mistral do notebook de descrição de cena —
    reaproveita o padrão já testado (tenta o provedor da vez, cai pro
    outro só em erro de cota).

    `contexto` (opcional): dict de buscar_contexto_biblico() -- quando
    presente, informa o título de seção/evento e os personagens à IA como
    contexto adicional (grounding), mesmo que o léxico sozinho não tenha
    batido nenhuma tag da lista fechada (ver gerar_sugestoes_match).
    """
    contexto_extra = ""
    if contexto and (contexto.get("titulo_versiculo") or contexto.get("titulo_evento")):
        partes = []
        if contexto.get("titulo_evento"):
            partes.append(f"Este capítulo narra: \"{contexto['titulo_evento']}\"")
        if contexto.get("titulo_versiculo"):
            partes.append(f"Este versículo especificamente: \"{contexto['titulo_versiculo']}\"")
        if contexto.get("personagens"):
            partes.append(f"Personagens envolvidos: {', '.join(contexto['personagens'])}")
        contexto_extra = "\n\nContexto de referência (use como apoio, não é obrigatório seguir à risca):\n" + "\n".join(partes)

    prompt = f"""Você vai receber um versículo bíblico (tradução World English Bible, em inglês).
Sugira palavras-chave visuais e temas que uma cena de vídeo poderia ilustrar
para esse versículo, numa narração bíblica.

Versículo:
{texto_versiculo}
{contexto_extra}

Retorne JSON estrito com os campos:
- palavras_chave: 2 a 4 palavras/expressões CURTAS em português, elementos
  visuais concretos que poderiam aparecer numa cena para esse versículo
  (ex: "estrela", "recém-nascido", "deserto", "anjo", "cidade antiga").
- tags_biblia: 1 a 4 itens da LISTA FECHADA abaixo que esse versículo
  especificamente narra ou referencia. Copie exatamente como está escrito
  na lista. Se nada combinar bem, deixe a lista vazia — não force.
  LISTA FECHADA: {lista_tags_biblia}

Responda SÓ o JSON, sem texto antes ou depois."""

    def _chamar(provedor):
        if provedor == "groq":
            res = groq_client.chat.completions.create(
                model=modelo_groq,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return json.loads(res.choices[0].message.content)
        else:
            res = mistral_client.chat.complete(
                model=modelo_mistral,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return json.loads(res.choices[0].message.content)

    primeiro = estado_provedor["atual"]
    segundo = "mistral" if primeiro == "groq" else "groq"
    ultimo_erro = None

    for provedor in (primeiro, segundo):
        cliente = groq_client if provedor == "groq" else mistral_client
        if not cliente:
            continue
        try:
            dados = _chamar(provedor)
            estado_provedor["atual"] = segundo if provedor == primeiro else primeiro
            return dados
        except Exception as e:
            # tenta o OUTRO provedor pra QUALQUER erro (cota, JSON malformado,
            # timeout, etc.) -- antes só tentava o outro em erro de cota, e
            # desistia na hora em qualquer outro tipo (foi assim que metade
            # dos versículos de um capítulo se perderam por causa de um
            # json_validate_failed pontual do Groq, que o Mistral teria
            # resolvido de boa na tentativa seguinte)
            ultimo_erro = e

    estado_provedor["atual"] = segundo
    raise ultimo_erro or RuntimeError("Nenhum provedor de IA disponível")


def _normalizar_tags(texto_tags):
    """Converte uma string 'tag1, tag2, tag3' (ou lista) num set de tags
    normalizadas (minúsculas, sem espaço extra) pra comparação."""
    if not texto_tags:
        return set()
    if isinstance(texto_tags, str):
        itens = texto_tags.split(",")
    else:
        itens = texto_tags
    return {t.strip().lower() for t in itens if t.strip()}


def carregar_biblioteca(linhas_planilha, coluna_id="ID", coluna_titulo="Título",
                          coluna_url="url", coluna_tags_biblia="Tags_Biblia_PT",
                          coluna_autor="Autor"):
    """
    Recebe as linhas da planilha (formato dict, tipo sheet.get_all_records())
    e monta a lista de candidatos pro match — cada item com suas
    tags_biblia já normalizadas num set, pronto pra comparar.

    Funciona igual pra vídeo (coluna_url="url") ou imagem
    (coluna_url="Imagem") — só muda o nome da coluna passado.
    """
    biblioteca = []
    for linha in linhas_planilha:
        tags = _normalizar_tags(linha.get(coluna_tags_biblia, ""))
        if not tags:
            continue  # sem tags_biblia preenchida ainda -- nao entra no match
        autor = str(linha.get(coluna_autor, "") or "").strip() or "Pixabay"
        biblioteca.append({
            "id": linha.get(coluna_id, ""),
            "titulo": linha.get(coluna_titulo, ""),
            "url": linha.get(coluna_url, ""),
            "autor": autor,
            "tags_biblia": tags,
        })
    return biblioteca


class PipelineNaoCoberto(Exception):
    """Levantada quando existem versículos sem match -- a montagem automática
    para aqui de propósito (ver verificar_cobertura_match)."""
    pass


def verificar_cobertura_match(resultados, caminho_relatorio=None):
    """
    Verifica se TODOS os versículos tiveram match (nenhum "sem_opcao").

    A montagem automática por versículo exige cobertura 100% -- não
    escolhe um segundo-melhor-score nem repete o clipe do vizinho por
    conta própria (decisão do projeto: buracos são preenchidos manualmente
    via pixabay_downloader, não por fallback automático).

    Se faltar algum, levanta PipelineNaoCoberto com a lista de versículos +
    palavras-chave sugeridas (prontas pra colar na busca do
    pixabay_downloader). Se `caminho_relatorio` for passado, também salva
    esse mesmo conteúdo num .txt, pra consulta sem precisar rodar de novo.
    """
    lacunas = [r for r in resultados if r.get("sem_opcao")]
    if not lacunas:
        return

    linhas = [f"{len(lacunas)} versículo(s) SEM MATCH -- busque no pixabay_downloader antes de montar:\n"]
    for r in sorted(lacunas, key=lambda x: x["versiculo"]):
        palavras = ", ".join(r.get("palavras_chave", [])) or "(nenhuma sugestão)"
        linhas.append(f"  v{r['versiculo']:>3}: {palavras}")
    relatorio = "\n".join(linhas)

    if caminho_relatorio:
        with open(caminho_relatorio, "w", encoding="utf-8") as f:
            f.write(relatorio + "\n")

    raise PipelineNaoCoberto(relatorio)


def calcular_segmentos_versiculo(resultados, tempos_versiculo, duracao_total_ms, duracao_minima_seg=2.0):
    """
    Monta o plano de segmentos pra montagem automática: um item por trecho
    de vídeo/imagem a cortar, com a mídia escolhida (match) e a duração
    exata daquele trecho no áudio.

    Versículos mais curtos que `duracao_minima_seg` são fundidos com o
    vizinho anterior (ou o seguinte, se for o primeiro versículo) -- evita
    trocar de cena a cada 1-2s (flicker). O segmento fundido usa a mídia
    do versículo que "absorveu" o tempo, não uma mistura dos dois.

    Pressupõe cobertura 100% -- rode verificar_cobertura_match() antes.

    Retorna lista de dicts: [{"versiculos": [1,2], "inicio_ms":, "fim_ms":,
    "duracao_seg":, "url":, "autor":, "id":, "titulo":}, ...]
    """
    por_versiculo = {r["versiculo"]: r for r in resultados}
    versos_ordenados = sorted(tempos_versiculo.keys())

    # ── 1. limites brutos de cada versículo (sem fusão ainda) ────────────
    brutos = []
    for i, v in enumerate(versos_ordenados):
        inicio = tempos_versiculo[v]
        fim = tempos_versiculo[versos_ordenados[i + 1]] if i + 1 < len(versos_ordenados) else duracao_total_ms
        brutos.append({"versiculos": [v], "inicio_ms": inicio, "fim_ms": fim})

    # ── 2. funde os curtos demais com o vizinho ──────────────────────────
    segmentos = []
    for seg in brutos:
        duracao_seg = (seg["fim_ms"] - seg["inicio_ms"]) / 1000.0
        curto = duracao_seg < duracao_minima_seg
        if curto and segmentos:
            # funde no anterior (estende o fim dele, mantém a mídia dele)
            segmentos[-1]["fim_ms"] = seg["fim_ms"]
            segmentos[-1]["versiculos"].extend(seg["versiculos"])
        else:
            segmentos.append(seg)

    # segunda passada: se o PRIMEIRO segmento ainda ficou curto (não tinha
    # anterior pra fundir), funde ele pra frente, no segundo
    if len(segmentos) >= 2:
        primeiro_dur = (segmentos[0]["fim_ms"] - segmentos[0]["inicio_ms"]) / 1000.0
        if primeiro_dur < duracao_minima_seg:
            segmentos[1]["inicio_ms"] = segmentos[0]["inicio_ms"]
            segmentos[1]["versiculos"] = segmentos[0]["versiculos"] + segmentos[1]["versiculos"]
            segmentos.pop(0)

    # ── 3. anexa a mídia escolhida (usa o match do PRIMEIRO versículo do
    # segmento fundido -- é o que dá o tom da cena) ──────────────────────
    plano = []
    for seg in segmentos:
        v_ref = seg["versiculos"][0]
        match = por_versiculo.get(v_ref)
        if not match or match.get("sem_opcao"):
            raise PipelineNaoCoberto(
                f"Versículo {v_ref} sem match ao montar o segmento -- rode "
                f"verificar_cobertura_match() antes de calcular_segmentos_versiculo()."
            )
        plano.append({
            "versiculos": seg["versiculos"],
            "inicio_ms": seg["inicio_ms"],
            "fim_ms": seg["fim_ms"],
            "duracao_seg": max(0.5, (seg["fim_ms"] - seg["inicio_ms"]) / 1000.0),
            "url": match["url"],
            "autor": match.get("autor", "Pixabay"),
            "id": match["id"],
            "titulo": match["titulo"],
        })

    return plano


def pontuar_candidatos(tags_sugeridas, biblioteca):
    """Retorna a biblioteca ordenada por quantas tags_biblia batem com as
    sugeridas (score = tamanho da interseção), maior primeiro."""
    tags_sugeridas_norm = _normalizar_tags(tags_sugeridas)
    pontuados = []
    for item in biblioteca:
        score = len(tags_sugeridas_norm & item["tags_biblia"])
        if score > 0:
            pontuados.append((score, item))
    pontuados.sort(key=lambda x: x[0], reverse=True)
    return pontuados


COLUNAS_BIBLIOTECA_MATCH = [
    "chave_id", "tipo_chave", "livro_pt", "capitulo", "versiculo", "referencia", "titulo", "tipo_fonte",
    "id_midia", "url_midia", "autor", "revisado_manualmente", "data_criacao", "origem",
]

NOME_PLANILHA_BIBLIOTECA_MATCH_PADRAO = "Biblioteca de Match — Narrated Video"


def _extrair_livro_de_referencia(referencia):
    """
    Extrai o nome do livro de uma referência tipo "Mateus 1–2" ou
    "1 Coríntios 15:1–29" -- pega tudo antes do ÚLTIMO token que começa
    com dígito (o capítulo/versículo), então funciona mesmo com livros
    que começam com número ("1 Coríntios", "2 Reis" etc.).

    Retorna None se não conseguir separar com confiança.
    """
    m = re.match(r"^(.*)\s+(\d[\d:–—-]*)$", referencia.strip())
    return m.group(1).strip() if m else None


def abrir_ou_criar_biblioteca_match(gc, id_planilha=None, nome_aba="biblioteca_match"):
    """
    Abre a planilha INDEPENDENTE da biblioteca de match (não fica mais
    dentro da planilha de vídeos/imagens) -- se id_planilha vier vazio,
    cria uma nova do zero e IMPRIME o ID pra você salvar no config.

    Retorna (spreadsheet, worksheet, id_planilha_usado).
    """
    if id_planilha and id_planilha.strip():
        spreadsheet = gc.open_by_key(id_planilha.strip())
    else:
        spreadsheet = gc.create(NOME_PLANILHA_BIBLIOTECA_MATCH_PADRAO)
        print(f"🆕 Planilha nova criada: '{NOME_PLANILHA_BIBLIOTECA_MATCH_PADRAO}'")
        print(f"   ID: {spreadsheet.id}")
        print(f"   👉 Copie esse ID pra ID_PLANILHA_BIBLIOTECA_MATCH na Configuração, "
              f"pra usar essa mesma planilha nas próximas vezes (senão cria uma nova toda vez!)")

    try:
        aba = spreadsheet.worksheet(nome_aba)
    except Exception:
        # se acabou de criar a planilha, ela vem com uma aba padrão "Sheet1" --
        # renomeia em vez de deixar as duas (mais limpo)
        abas = spreadsheet.worksheets()
        if len(abas) == 1 and abas[0].get_all_values() in ([], [[]]):
            aba = abas[0]
            aba.update_title(nome_aba)
        else:
            aba = spreadsheet.add_worksheet(title=nome_aba, rows=1000, cols=len(COLUNAS_BIBLIOTECA_MATCH))
        aba.append_row(COLUNAS_BIBLIOTECA_MATCH)

    return spreadsheet, aba, spreadsheet.id


def carregar_biblioteca_match(aba_biblioteca_match):
    """
    Lê a aba de biblioteca de match e monta um dict {(livro_pt, capitulo,
    versiculo, tipo_fonte): linha} pra consulta O(1) -- a chave agora é o
    VERSÍCULO específico (não mais o título/evento inteiro), porque cada
    versículo pode ter sua própria mídia escolhida, mesmo que vários
    versículos pertençam ao mesmo título/evento (ver painel de revisão).
    """
    linhas = aba_biblioteca_match.get_all_records()
    biblioteca = {}
    for linha in linhas:
        livro_pt = str(linha.get("livro_pt", "")).strip()
        capitulo = str(linha.get("capitulo", "")).strip()
        versiculo = str(linha.get("versiculo", "")).strip()
        tipo_fonte = str(linha.get("tipo_fonte", "")).strip()
        if livro_pt and capitulo and versiculo and tipo_fonte:
            biblioteca[(livro_pt, capitulo, versiculo, tipo_fonte)] = linha
    return biblioteca


def buscar_na_biblioteca_match(livro_pt, capitulo, versiculo, tipo_fonte, biblioteca_match):
    """
    Verifica se ESSE VERSÍCULO específico já tem um vencedor salvo --
    seja porque você escolheu manualmente no painel de revisão (Apps
    Script), seja porque o léxico/IA já resolveu antes pra ele. Se achar,
    usa DIRETO, sem checar nada (decisão do projeto: confia no que já foi
    validado/revisado).

    Retorna a linha salva (dict) ou None se não tem match ainda.
    """
    return biblioteca_match.get((str(livro_pt), str(capitulo), str(versiculo), tipo_fonte))


def registrar_na_biblioteca_match(aba_biblioteca_match, chave_id, tipo_chave, livro_pt, capitulo, versiculo,
                                     referencia, titulo, tipo_fonte, id_midia, url_midia, autor, origem):
    """
    Salva o vencedor de UM VERSÍCULO na biblioteca -- da próxima vez que
    esse mesmo versículo aparecer (neste vídeo ou em qualquer outro),
    buscar_na_biblioteca_match() acha na hora, sem gastar IA nem re-rodar
    o léxico. chave_id (titulo_id/evento_id) viaja junto só como
    referência/contexto -- não faz mais parte da chave de busca.
    """
    from datetime import datetime
    aba_biblioteca_match.append_row([
        chave_id, tipo_chave, livro_pt, str(capitulo), str(versiculo), referencia, titulo, tipo_fonte,
        str(id_midia), url_midia, autor, False,
        datetime.now().strftime("%Y-%m-%d %H:%M"), origem,
    ])


def _col_letra(indice_1_based):
    """Converte índice de coluna (1=A, 2=B, ..., 27=AA) pra letra --
    usado pra montar um range EXPLÍCITO (ex: "A1:J1") na migração de
    cabeçalho. Importante: NÃO usar só "A1" sozinho como range_name num
    update() multi-coluna -- em alguns casos reais isso não expandiu
    pras colunas seguintes (só escreveu a 1ª célula), deixando o
    cabeçalho "migrado" só de mentirinha -- foi exatamente esse bug que
    causou um KeyError('tags_clima') depois de 191 lotes de IA já
    processados (a escrita dos resultados falhou, o trabalho da IA não
    -- ver gravar_tags_clima, que agora também se autocura)."""
    letras = ""
    n = indice_1_based
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def garantir_aba_versiculo_tags(spreadsheet, nome_aba="versiculo_tags"):
    """
    Acha (ou cria) a aba de tags por versículo, na MESMA planilha da
    biblioteca_match/biblia_texto -- cada versículo ganha suas próprias
    palavras-chave (extraídas do texto dele, via léxico/IA -- reaproveita
    o que gerar_sugestoes_match já calcula pro match, sem gastar IA de
    novo). É essa tag que o painel de revisão usa pra RANQUEAR os
    candidatos por relevância, em vez de só filtrar por capítulo (ver
    Code.gs).
    """
    try:
        aba = spreadsheet.worksheet(nome_aba)
    except Exception:
        aba = spreadsheet.add_worksheet(title=nome_aba, rows=1000, cols=len(COLUNAS_VERSICULO_TAGS))
        aba.append_row(COLUNAS_VERSICULO_TAGS)
        return aba

    # aba já existe -- confere se o cabeçalho está desatualizado (schema
    # mudou depois que essa aba foi criada, ex: tags_sugeridas foi
    # adicionada no meio). Sem essa checagem, append_row grava por
    # POSIÇÃO, não por nome -- e cada linha nova fica desalinhada do
    # cabeçalho antigo (foi exatamente esse bug que apareceu quando
    # tags_sugeridas entrou no esquema).
    cabecalho_atual = aba.row_values(1)
    if cabecalho_atual != COLUNAS_VERSICULO_TAGS:
        if len(COLUNAS_VERSICULO_TAGS) > aba.col_count:
            aba.add_cols(len(COLUNAS_VERSICULO_TAGS) - aba.col_count)
        aba.update(values=[COLUNAS_VERSICULO_TAGS], range_name=f"A1:{_col_letra(len(COLUNAS_VERSICULO_TAGS))}1")
    return aba


COLUNAS_EVENTO_TAGS = ["livro_pt", "capitulo_ini", "capitulo_fim", "evento_id", "titulo", "tags", "tags_semelhantes",
                        "tags_clima", "tags_clima_semelhantes"]
COLUNAS_TITULO_TAGS = ["livro_pt", "capitulo", "versiculo_ini", "versiculo_fim", "titulo_id", "titulo", "tags", "tags_semelhantes",
                        "tags_clima", "tags_clima_semelhantes"]


def garantir_aba_evento_tags(spreadsheet, nome_aba="evento_tags"):
    """Acha (ou cria) a aba de tags por EVENTO -- mesma planilha da
    biblioteca_match/versiculo_tags. Guarda o intervalo (capitulo_ini/fim)
    junto, pra ficar visível na planilha (antes só existia dentro do
    eventos-biblicos.json, escondido). Migra o cabeçalho sozinha se o
    esquema mudou depois que a aba foi criada (ex: tags_clima entrou
    depois) -- mesma proteção que garantir_aba_versiculo_tags já tem."""
    try:
        aba = spreadsheet.worksheet(nome_aba)
    except Exception:
        aba = spreadsheet.add_worksheet(title=nome_aba, rows=600, cols=len(COLUNAS_EVENTO_TAGS))
        aba.append_row(COLUNAS_EVENTO_TAGS)
        return aba

    cabecalho_atual = aba.row_values(1)
    if cabecalho_atual != COLUNAS_EVENTO_TAGS:
        if len(COLUNAS_EVENTO_TAGS) > aba.col_count:
            aba.add_cols(len(COLUNAS_EVENTO_TAGS) - aba.col_count)
        aba.update(values=[COLUNAS_EVENTO_TAGS], range_name=f"A1:{_col_letra(len(COLUNAS_EVENTO_TAGS))}1")
    return aba


def garantir_aba_titulo_tags(spreadsheet, nome_aba="titulo_tags"):
    """Igual garantir_aba_evento_tags, mas pra TÍTULO (granularidade de
    versículo -- guarda versiculo_ini/fim, não capitulo_ini/fim). Migra
    o cabeçalho sozinha se o esquema mudou."""
    try:
        aba = spreadsheet.worksheet(nome_aba)
    except Exception:
        aba = spreadsheet.add_worksheet(title=nome_aba, rows=3000, cols=len(COLUNAS_TITULO_TAGS))
        aba.append_row(COLUNAS_TITULO_TAGS)
        return aba

    cabecalho_atual = aba.row_values(1)
    if cabecalho_atual != COLUNAS_TITULO_TAGS:
        if len(COLUNAS_TITULO_TAGS) > aba.col_count:
            aba.add_cols(len(COLUNAS_TITULO_TAGS) - aba.col_count)
        aba.update(values=[COLUNAS_TITULO_TAGS], range_name=f"A1:{_col_letra(len(COLUNAS_TITULO_TAGS))}1")
    return aba


def _parse_referencia_evento_publica(referencia):
    """Wrapper público de _parse_referencia_evento -- extrai o livro
    sozinho antes de chamar (a função original pede o livro como
    parâmetro, aqui não sabemos ele de antemão)."""
    livro = _extrair_livro_de_referencia(referencia)
    if not livro:
        return None
    return _parse_referencia_evento(referencia, livro)


def carregar_evento_tags(aba_evento_tags):
    """Dict {evento_id: {"tags": [...], "tags_semelhantes": [...]}} lido
    DIRETO da planilha (não do JSON) -- se você editar uma tag na aba
    evento_tags, é isso que passa a valer no próximo match."""
    resultado = {}
    for linha in aba_evento_tags.get_all_records():
        evento_id = str(linha.get("evento_id", "")).strip()
        if not evento_id:
            continue
        resultado[evento_id] = {
            "tags": [t.strip() for t in str(linha.get("tags", "")).split(",") if t.strip()],
            "tags_semelhantes": [t.strip() for t in str(linha.get("tags_semelhantes", "")).split(",") if t.strip()],
        }
    return resultado


def carregar_titulo_tags(aba_titulo_tags):
    """Dict {titulo_id: {"tags": [...], "tags_semelhantes": [...]}} lido
    DIRETO da planilha (não do JSON) -- mesma ideia de carregar_evento_tags."""
    resultado = {}
    for linha in aba_titulo_tags.get_all_records():
        titulo_id = str(linha.get("titulo_id", "")).strip()
        if not titulo_id:
            continue
        resultado[titulo_id] = {
            "tags": [t.strip() for t in str(linha.get("tags", "")).split(",") if t.strip()],
            "tags_semelhantes": [t.strip() for t in str(linha.get("tags_semelhantes", "")).split(",") if t.strip()],
        }
    return resultado


def sincronizar_evento_titulo_tags(aba_evento_tags, aba_titulo_tags, eventos_biblicos, titulos_biblicos):
    """
    Copia as tags de evento/título (já calculadas no léxico, sem IA --
    ver dados_lexico/eventos-biblicos.json e titulos-biblicos.json) pras
    abas evento_tags/titulo_tags -- só pra ficarem VISÍVEIS na planilha
    (antes só existiam escondidas dentro do JSON). Não gasta IA nem
    Pixabay, é só uma cópia.

    Roda a Bíblia INTEIRA de uma vez (é grátis) -- pula quem já foi
    sincronizado antes (não duplica se rodar de novo).
    """
    existentes_evento = {str(l.get("evento_id", "")) for l in aba_evento_tags.get_all_records()}
    linhas_evento = []
    for evento in eventos_biblicos:
        if evento.get("id") in existentes_evento:
            continue
        faixa = _parse_referencia_evento_publica(evento.get("referencia", ""))
        cap_ini, cap_fim = faixa if faixa else ("", "")
        linhas_evento.append([
            _extrair_livro_de_referencia(evento.get("referencia", "")) or "",
            cap_ini, cap_fim, evento.get("id", ""), evento.get("titulo", ""),
            ", ".join(evento.get("tags", [])), ", ".join(evento.get("tags_semelhantes", [])),
            "", "",  # tags_clima/tags_clima_semelhantes -- preenchidas depois via IA (ver trilha_pipeline.py)
        ])
    if linhas_evento:
        aba_evento_tags.append_rows(linhas_evento, value_input_option="USER_ENTERED")

    existentes_titulo = {str(l.get("titulo_id", "")) for l in aba_titulo_tags.get_all_records()}
    linhas_titulo = []
    for chave_id, titulo in titulos_biblicos.items():
        if chave_id in existentes_titulo:
            continue
        linhas_titulo.append([
            titulo.get("livro", ""), titulo.get("capitulo", ""), titulo.get("vIni", ""), titulo.get("vFim", ""),
            chave_id, titulo.get("titulo", ""),
            ", ".join(titulo.get("tags", [])), ", ".join(titulo.get("tags_semelhantes", [])),
            "", "",  # tags_clima/tags_clima_semelhantes -- preenchidas depois via IA
        ])
    if linhas_titulo:
        aba_titulo_tags.append_rows(linhas_titulo, value_input_option="USER_ENTERED")

    return len(linhas_evento), len(linhas_titulo)


def carregar_versiculo_tags(aba_versiculo_tags):
    """Dict {(livro_pt, capitulo, versiculo): linha} -- pra saber quais
    versículos já têm tag salva, e não escrever duplicado numa rodada
    nova pro mesmo capítulo."""
    linhas = aba_versiculo_tags.get_all_records()
    tags = {}
    for linha in linhas:
        chave = (str(linha.get("livro_pt", "")).strip(), str(linha.get("capitulo", "")).strip(),
                 str(linha.get("versiculo", "")).strip())
        if all(chave):
            tags[chave] = linha
    return tags


def versiculos_para_semear(aba_versiculo_tags, livro_pt, capitulo_ini=None, capitulo_fim=None):
    """Lê versiculo_tags e converte pro formato que
    pixabay_seed_pipeline.semear_por_versiculo espera -- uma lista de
    dicts {item_id, livro_pt, capitulo, versiculo, tags_pt,
    tags_sugeridas, tags_semelhantes} (as 3 últimas já viram LISTA, não
    mais string separada por vírgula).

    Filtra por livro (e por faixa de capítulo, se informada -- capitulo_ini=None
    pega o LIVRO INTEIRO, igual eventos_para_semear())."""
    def _para_lista(valor):
        return [t.strip() for t in str(valor or "").split(",") if t.strip()]

    linhas = aba_versiculo_tags.get_all_records()
    alvo = []
    for linha in linhas:
        if linha.get("livro_pt") != livro_pt:
            continue
        capitulo = linha.get("capitulo")
        if capitulo_ini is not None:
            fim = capitulo_fim if capitulo_fim is not None else capitulo_ini
            if not (capitulo_ini <= int(capitulo) <= fim):
                continue
        alvo.append({
            "item_id": f"{livro_pt}:{capitulo}:{linha.get('versiculo')}",
            "livro_pt": livro_pt,
            "capitulo": capitulo,
            "versiculo": linha.get("versiculo"),
            "tags_pt": _para_lista(linha.get("tags_pt")),
            "tags_sugeridas": _para_lista(linha.get("tags_sugeridas")),
            "tags_semelhantes": _para_lista(linha.get("tags_semelhantes")),
        })
    return alvo


COLUNAS_VERSICULO_TAGS = ["livro_pt", "capitulo", "versiculo", "tags_pt", "tags_sugeridas", "tags_semelhantes", "origem", "data_criacao",
                            "tags_clima"]


def registrar_tags_versiculo(aba_versiculo_tags, livro_pt, capitulo, versiculo, tags_pt, origem,
                                tags_extras=None, tags_sugeridas=None):
    """Salva as palavras-chave de UM versículo -- chamado uma vez só por
    versículo (gerar_sugestoes_match já evita duplicar, ver
    versiculo_tags_existentes).

    tags_pt fica ENXUTO (só as palavras-chave do próprio versículo) --
    é isso que pixabay_seed_pipeline.semear_por_versiculo usa pra BUSCAR,
    então não pode incluir tag de evento/título (senão a busca por
    versículo repetiria a busca que evento/título já fizeram sozinhos,
    voltando pro "problema N+1" que já resolvemos).

    tags_sugeridas (tags_biblia_sugeridas do sugerir_tags_versiculo) SÃO
    específicas de CADA versículo -- não vêm compartilhadas de
    evento/título, então incluir na busca não reintroduz repetição
    nenhuma. Ficam numa coluna própria (rastreável, igual
    Tags_Descricao_PT do lado da imagem) e TAMBÉM entram no
    tags_semelhantes (estoque de match).

    tags_semelhantes é o ESTOQUE RICO pro painel de revisão comparar
    (comparar tag não gasta API/IA, então aqui pode encher à vontade):
    expande tags_pt + tags_sugeridas por sinônimo, e também soma
    tags_extras (as tags do evento/título que cobrem esse versículo,
    já prontas no léxico -- ver gerar_sugestoes_match)."""
    from datetime import datetime
    from dicionario_sinonimos import expandir_tags_semelhantes
    tags_sugeridas = tags_sugeridas or []
    tags_semelhantes = expandir_tags_semelhantes(list(tags_pt) + list(tags_sugeridas))
    if tags_extras:
        for tag in tags_extras:
            if tag not in tags_semelhantes:
                tags_semelhantes.append(tag)
    aba_versiculo_tags.append_row([
        livro_pt, str(capitulo), str(versiculo), ", ".join(tags_pt), ", ".join(tags_sugeridas),
        ", ".join(tags_semelhantes), origem, datetime.now().strftime("%Y-%m-%d %H:%M"),
        "",  # tags_clima -- SEMPRE vazio aqui, é override 100% manual (você preenche na mão se quiser)
    ])


def gerar_sugestoes_match(versiculos_texto, biblioteca, lista_tags_biblia,
                            groq_client, mistral_client, modelo_groq, modelo_mistral,
                            dist_min_repeticao=3, margem_para_repetir=2,
                            delay_segundos=2, max_tokens=300,
                            livro_pt=None, capitulo=None, titulos_biblicos=None, eventos_biblicos=None,
                            tipo_fonte=None, biblioteca_match=None, aba_biblioteca_match=None,
                            provedor_inicial="mistral", aba_versiculo_tags=None,
                            evento_tags_dict=None, titulo_tags_dict=None):
    """
    Orquestra o match completo: pra cada versículo (em ordem), sugere tags,
    pontua contra a biblioteca, e escolhe o melhor candidato — evitando
    repetir o mesmo vídeo/imagem em versículos muito próximos, a não ser
    que ele seja bem melhor que a segunda opção (margem definida por
    margem_para_repetir).

    Cascata pra decidir a mídia de cada versículo (ver docstring do módulo):
    1. BIBLIOTECA DE MATCH -- se aquele título/evento já tem um match salvo
       (de um vídeo anterior ou de uma rodada anterior deste mesmo vídeo),
       usa DIRETO -- sem léxico, sem IA, sem pontuar de novo. Precisa de
       tipo_fonte + biblioteca_match (carregar_biblioteca_match()).
    2. LÉXICO -- se não tem na biblioteca ainda, tenta sugerir_tags_lexico()
       -- se achar tag da lista fechada, usa direto, SEM CHAMAR IA.
    3. IA (com contexto) -- se o léxico não bateu tag nenhuma mas achou
       algum título/evento, chama a IA passando isso como contexto extra.
    4. IA (sem contexto) -- se não tem léxico configurado, ou não achou
       contexto nenhum, cai no caminho antigo: só IA.

    Toda vez que os passos 2-4 resolvem um versículo (e ele tem
    titulo_id/evento_id do léxico), o resultado é registrado na biblioteca
    de match automaticamente (se aba_biblioteca_match foi passada) -- da
    próxima vez que esse título/evento aparecer (neste vídeo ou em
    qualquer outro), cai direto no passo 1.

    Cada resultado tem "fonte": "biblioteca", "lexico" ou "ia", pra você
    saber de onde veio na revisão.

    Retorna uma lista de dicts, um por versículo, com o resultado do match
    (ou "sem_opcao": True + palavras_chave, se nada bateu).
    """
    usar_contexto = bool(livro_pt and capitulo and titulos_biblicos and eventos_biblicos)
    usar_biblioteca_match = bool(usar_contexto and tipo_fonte and biblioteca_match is not None)
    usar_versiculo_tags = bool(aba_versiculo_tags is not None and livro_pt and capitulo)
    versiculo_tags_existentes = carregar_versiculo_tags(aba_versiculo_tags) if usar_versiculo_tags else {}
    estado_provedor = {"atual": provedor_inicial}  # Mistral por padrão -- cota mais folgada que a do Groq
    ultimo_uso = {}  # id_video -> numero do ultimo versiculo em que foi usado
    resultados = []
    contagem_fonte = {"biblioteca": 0, "lexico": 0, "ia": 0}

    for v in sorted(versiculos_texto.keys()):
        texto = versiculos_texto[v]
        contexto = buscar_contexto_biblico(livro_pt, capitulo, v, titulos_biblicos, eventos_biblicos) if usar_contexto else None

        # ── 1. já tem match salvo pra ESSE VERSÍCULO? usa direto ──────────
        if usar_biblioteca_match:
            salvo = buscar_na_biblioteca_match(livro_pt, capitulo, v, tipo_fonte, biblioteca_match)
            if salvo:
                contagem_fonte["biblioteca"] += 1
                if salvo.get("id_midia"):
                    ultimo_uso[salvo["id_midia"]] = v  # conta pra anti-repetição de quem vier depois
                resultados.append({
                    "versiculo": v, "texto": texto,
                    "sem_opcao": False, "fonte": "biblioteca",
                    "id": salvo.get("id_midia"), "titulo": salvo.get("titulo"), "url": salvo.get("url_midia"),
                    "autor": salvo.get("autor", "Pixabay"),
                    "score": None, "tags_batidas": [],
                    "palavras_chave": [],
                })
                continue

        # ── 2-4. léxico -> IA (com/sem contexto) ──────────────────────────
        fonte = "ia"
        sugestao = None
        if usar_contexto:
            sugestao = sugerir_tags_lexico(contexto, lista_tags_biblia)
            if sugestao:
                fonte = "lexico"

        if fonte != "lexico":
            try:
                sugestao = sugerir_tags_versiculo(
                    texto, lista_tags_biblia, groq_client, mistral_client,
                    estado_provedor, modelo_groq, modelo_mistral, max_tokens,
                    contexto=contexto,
                )
            except Exception as e:
                resultados.append({
                    "versiculo": v, "texto": texto, "erro": str(e),
                    "sem_opcao": True, "palavras_chave": [],
                })
                time.sleep(delay_segundos)
                continue

        contagem_fonte[fonte] += 1
        tags_biblia_sugeridas = sugestao.get("tags_biblia", [])
        palavras_chave = sugestao.get("palavras_chave", [])

        # ── tags do título/evento que cobrem esse versículo -- já prontas
        # no léxico (sem IA). Usadas TANTO pro match quanto pro estoque
        # gravado em versiculo_tags -- calculadas uma vez só, aqui. ──────
        # tags do título/evento que cobrem esse versículo -- prioriza o
        # que está NA PLANILHA (evento_tags_dict/titulo_tags_dict, se
        # passados -- editável por você, ver carregar_evento_tags()) e só
        # cai pro JSON do léxico se essas abas não foram carregadas.
        tags_extras = []
        if contexto:
            titulo_id = contexto.get("titulo_id")
            if titulo_id and titulo_tags_dict is not None and titulo_id in titulo_tags_dict:
                tags_extras += titulo_tags_dict[titulo_id]["tags"] + titulo_tags_dict[titulo_id]["tags_semelhantes"]
            elif titulo_id and titulos_biblicos:
                titulo_entrada = titulos_biblicos.get(titulo_id)
                if titulo_entrada:
                    tags_extras += titulo_entrada.get("tags", []) + titulo_entrada.get("tags_semelhantes", [])

            evento_id = contexto.get("evento_id")
            if evento_id and evento_tags_dict is not None and evento_id in evento_tags_dict:
                tags_extras += evento_tags_dict[evento_id]["tags"] + evento_tags_dict[evento_id]["tags_semelhantes"]
            elif evento_id and eventos_biblicos:
                evento_entrada = next((e for e in eventos_biblicos if e.get("id") == evento_id), None)
                if evento_entrada:
                    tags_extras += evento_entrada.get("tags", []) + evento_entrada.get("tags_semelhantes", [])

        # tags_semelhantes: o MESMO estoque rico que vai pra versiculo_tags
        # (versículo + sugeridas, expandido por sinônimo, + evento/título)
        # -- reaproveitado aqui como entrada do match, no lugar da lista
        # fechada antiga (tags_biblia_sugeridas sozinha). É estritamente
        # mais rico (tags_biblia_sugeridas já está incluída dentro dele),
        # e compara contra Tags_Semelhantes_PT da image-stock (ver
        # carregar_biblioteca com coluna_tags_biblia="Tags_Semelhantes_PT"
        # no notebook) -- o MESMO comparador que o painel de revisão usa.
        from dicionario_sinonimos import expandir_tags_semelhantes
        tags_semelhantes = expandir_tags_semelhantes(list(palavras_chave) + list(tags_biblia_sugeridas))
        for tag in tags_extras:
            if tag not in tags_semelhantes:
                tags_semelhantes.append(tag)

        # ── grava as palavras-chave do versículo (efeito colateral, de graça --
        # já foram calculadas acima pra decidir o match; usadas depois pelo
        # painel de revisão pra ranquear candidatos por relevância) ──────────
        if usar_versiculo_tags and palavras_chave:
            chave_versiculo = (str(livro_pt), str(capitulo), str(v))
            if chave_versiculo not in versiculo_tags_existentes:
                try:
                    registrar_tags_versiculo(
                        aba_versiculo_tags, livro_pt, capitulo, v, palavras_chave, fonte,
                        tags_extras=tags_extras, tags_sugeridas=tags_biblia_sugeridas,
                    )
                    versiculo_tags_existentes[chave_versiculo] = {"tags_pt": ", ".join(palavras_chave)}
                except Exception as e:
                    print(f"   ⚠️  Não consegui gravar tags do versículo {v}: {e}")

        candidatos = pontuar_candidatos(tags_semelhantes, biblioteca)


        escolhido = None
        for score, candidato in candidatos:
            ultima_vez = ultimo_uso.get(candidato["id"])
            usado_recentemente = ultima_vez is not None and (v - ultima_vez) < dist_min_repeticao
            if not usado_recentemente:
                escolhido = (score, candidato)
                break
            # esta na "zona de espera" -- so aceita se for MUITO melhor
            # que o proximo candidato nao-recente
            if candidatos[0][0] - score >= margem_para_repetir:
                continue
            escolhido = (score, candidato)  # aceita repetir, a diferenca nao compensa pular
            break

        if escolhido:
            score, candidato = escolhido
            ultimo_uso[candidato["id"]] = v
            resultados.append({
                "versiculo": v, "texto": texto,
                "sem_opcao": False, "fonte": fonte,
                "id": candidato["id"], "titulo": candidato["titulo"], "url": candidato["url"],
                "autor": candidato.get("autor", "Pixabay"),
                "score": score, "tags_batidas": sorted(_normalizar_tags(tags_semelhantes) & candidato["tags_biblia"]),
                "palavras_chave": palavras_chave,
            })

            # ── registra na biblioteca de match (por VERSÍCULO), pra reusar da próxima vez ──
            if aba_biblioteca_match is not None and tipo_fonte:
                if contexto and contexto.get("titulo_id"):
                    chave_id, tipo_chave = contexto["titulo_id"], "titulo"
                    referencia, titulo_lexico = contexto["titulo_referencia"], contexto["titulo_versiculo"]
                elif contexto and contexto.get("evento_id"):
                    chave_id, tipo_chave = contexto["evento_id"], "evento"
                    referencia, titulo_lexico = contexto["evento_referencia"], contexto["titulo_evento"]
                else:
                    chave_id, tipo_chave, referencia, titulo_lexico = "", "", "", candidato["titulo"]
                try:
                    registrar_na_biblioteca_match(
                        aba_biblioteca_match, chave_id, tipo_chave, livro_pt, capitulo, v,
                        referencia, titulo_lexico, tipo_fonte,
                        candidato["id"], candidato["url"], candidato.get("autor", "Pixabay"), fonte,
                    )
                    biblioteca_match[(str(livro_pt), str(capitulo), str(v), tipo_fonte)] = {
                        "id_midia": candidato["id"], "url_midia": candidato["url"],
                        "autor": candidato.get("autor", "Pixabay"), "titulo": candidato["titulo"],
                    }
                except Exception as e:
                    print(f"   ⚠️  Não consegui registrar na biblioteca de match (v{v}): {e}")
        else:
            resultados.append({
                "versiculo": v, "texto": texto,
                "sem_opcao": True, "fonte": fonte,
                "palavras_chave": palavras_chave,
                "tags_biblia_sugeridas": tags_biblia_sugeridas,
            })

        if fonte == "ia":
            time.sleep(delay_segundos)  # só espera quando chamou API de verdade

    if usar_contexto:
        print(f"   📊 Fonte das tags: {contagem_fonte['biblioteca']} já na biblioteca (grátis) "
              f"+ {contagem_fonte['lexico']} via léxico (grátis) + {contagem_fonte['ia']} via IA")

    return resultados
