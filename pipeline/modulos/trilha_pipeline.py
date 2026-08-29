# -*- coding: utf-8 -*-
"""
trilha_pipeline.py — Normaliza as fontes de trilha sonora (Freesound
automático + lista manual) numa coluna comum Tags_Clima_PT, e faz o
match por clima contra evento/título bíblico.

Duas fontes, formatos bem diferentes:
- Freesound_Audio_Manager (automático, via API): coluna "Tags" crua,
  mistura clima ("sad", "relax", "hope") com termo técnico ("wav",
  "arp", "loop", "synth") -- filtra usando o dicionário de clima como
  peneira (só entra o que bate em algum grupo).
- Lista manual (Dark_NPOS_Temas_Trilhas_Sonoras, YouTube Audio Library):
  coluna "Gênero" já vem limpa, um clima só por faixa (ex: "Dramático").

As duas viram o MESMO formato de saída (id, titulo, url, autor,
tags_clima) -- prontas pra comparar contra tags_clima do evento/título,
mesmo mecanismo de tag em comum que já usamos pra imagem.
"""
from __future__ import annotations

import json

from dicionario_sinonimos_clima import expandir_tags_clima, MAPA_CLIMA_PT, GRUPOS_CLIMA_PT


def _normalizar_palavra(s):
    import unicodedata
    nfkd = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extrair_tags_clima_de_lista_bruta(tags_brutas):
    """Filtra uma lista de tags CRUAS (pode vir misturada com termo
    técnico) e devolve só as que são de CLIMA de verdade, já expandidas
    por sinônimo. Usado pro Freesound, onde a coluna Tags vem suja."""
    tags_clima = [t for t in tags_brutas if _normalizar_palavra(t) in MAPA_CLIMA_PT]
    return expandir_tags_clima(tags_clima)


def carregar_trilha_stock_freesound(linhas_planilha, coluna_tags="Tags", coluna_id="ID",
                                       coluna_titulo="Título", coluna_url="URL Preview", coluna_autor="Autor"):
    """Lê a aba Página1 do Freesound_Audio_Manager (linhas já como
    dict, via worksheet.get_all_records()) e devolve uma lista no
    formato comum {id, titulo, url, autor, tags_clima, categoria, fonte}
    -- categoria="trilha", pronta pra sincronizar_estoque_som()."""
    resultado = []
    for linha in linhas_planilha:
        tags_brutas = [t.strip() for t in str(linha.get(coluna_tags, "")).split(",") if t.strip()]
        tags_clima = extrair_tags_clima_de_lista_bruta(tags_brutas)
        if not tags_clima:
            continue  # sem clima identificado -- nao serve pro match, ignora
        resultado.append({
            "id": str(linha.get(coluna_id, "")),
            "titulo": linha.get(coluna_titulo, ""),
            "url": linha.get(coluna_url, ""),
            "autor": linha.get(coluna_autor, ""),
            "tags_clima": tags_clima,
            "categoria": "trilha",
            "fonte": "freesound",
        })
    return resultado


def carregar_trilha_stock_manual(linhas_planilha, coluna_genero="Gênero", coluna_genero_colab="Gênero Colab",
                                    coluna_tema="Tema ", coluna_creditos=" Créditos"):
    """Lê a lista manual (Dark_NPOS_Temas_Trilhas_Sonoras) e devolve no
    MESMO formato comum -- Gênero (+ Gênero Colab, se preenchido) já é
    limpo, só expande por sinônimo."""
    resultado = []
    for i, linha in enumerate(linhas_planilha):
        genero = str(linha.get(coluna_genero, "") or "").strip()
        genero_colab = str(linha.get(coluna_genero_colab, "") or "").strip()
        tags_base = [t for t in [genero, genero_colab] if t]
        if not tags_base:
            continue
        tags_clima = expandir_tags_clima(tags_base)
        resultado.append({
            "id": f"manual-{i}",
            "titulo": linha.get(coluna_tema, ""),
            "url": "",  # arquivo local (YouTube Audio Library) -- sem URL, so o nome/creditos
            "autor": linha.get(coluna_creditos, ""),
            "tags_clima": tags_clima,
            "categoria": "trilha",
            "fonte": "manual",
        })
    return resultado


def pontuar_trilhas(tags_clima_alvo, trilha_stock):
    """Mesma lógica de match_pipeline.pontuar_candidatos, mas pro
    universo de trilha -- pontua cada trilha do estoque pela
    sobreposição de tags_clima contra o alvo (evento/título), ordena do
    melhor pro pior."""
    alvo_normalizado = {_normalizar_palavra(t) for t in tags_clima_alvo}
    candidatos = []
    for trilha in trilha_stock:
        tags_trilha_normalizadas = {_normalizar_palavra(t) for t in trilha["tags_clima"]}
        batidas = alvo_normalizado & tags_trilha_normalizadas
        if batidas:
            candidatos.append({**trilha, "score": len(batidas), "tags_batidas": sorted(batidas)})
    return sorted(candidatos, key=lambda c: -c["score"])


# ==============================================
# MATCH DE TRILHA POR EVENTO -- agrupa versículos consecutivos do MESMO
# evento bíblico sob a MESMA trilha (o clima muda quando a cena muda, não
# verso a verso -- diferente do match de cena/imagem, que é por versículo).
# Mesma ideia de match_pipeline.calcular_segmentos_versiculo, só que a
# CHAVE de agrupamento é o evento, e o candidato vem de um pool pequeno
# escolhido à mão (não a trilha_stock inteira) -- ver notebook
# video-base-imagem-versiculo-trilhas.ipynb.
# ==============================================


def carregar_evento_clima(aba_evento_tags):
    """Dict {evento_id: {"tags_clima": [...], "tags_clima_semelhantes": [...]}}
    lido DIRETO da planilha evento_tags -- diferente de
    match_pipeline.carregar_evento_tags (que só lê tags/tags_semelhantes,
    a dimensão VISUAL, não a de clima)."""
    resultado = {}
    for linha in aba_evento_tags.get_all_records():
        evento_id = str(linha.get("evento_id", "")).strip()
        if not evento_id:
            continue
        resultado[evento_id] = {
            "tags_clima": [t.strip() for t in str(linha.get("tags_clima", "")).split(",") if t.strip()],
            "tags_clima_semelhantes": [t.strip() for t in str(linha.get("tags_clima_semelhantes", "")).split(",") if t.strip()],
        }
    return resultado


def carregar_titulo_clima(aba_titulo_tags):
    """Dict {titulo_id: {"tags_clima": [...], "tags_clima_semelhantes": [...]}}
    -- mesma ideia de carregar_evento_clima, granularidade de versículo
    (mais fina que evento). Usado como PRIMEIRA tentativa em
    calcular_segmentos_trilha -- só cai pro clima do evento se o título
    que cobre aquele trecho não tiver clima próprio (mesmo cascata
    título→evento já usado no match visual, ver match_pipeline.py)."""
    resultado = {}
    for linha in aba_titulo_tags.get_all_records():
        titulo_id = str(linha.get("titulo_id", "")).strip()
        if not titulo_id:
            continue
        resultado[titulo_id] = {
            "tags_clima": [t.strip() for t in str(linha.get("tags_clima", "")).split(",") if t.strip()],
            "tags_clima_semelhantes": [t.strip() for t in str(linha.get("tags_clima_semelhantes", "")).split(",") if t.strip()],
        }
    return resultado


def calcular_segmentos_trilha(versiculos_texto, tempos_versiculo, duracao_total_ms,
                                 livro_pt, capitulo, titulos_biblicos, eventos_biblicos,
                                 evento_clima_dict, trilha_pool, titulo_clima_dict=None):
    """
    Monta o plano de segmentos de TRILHA: um item por trecho contínuo de
    versículos do MESMO evento bíblico, com a trilha escolhida (melhor
    candidato do `trilha_pool` pelo clima) e a duração exata daquele
    trecho no áudio.

    O AGRUPAMENTO em segmentos é sempre por EVENTO (é o que dá o "vários
    versículos seguidos com a mesma trilha, depois troca" -- clima muda
    quando a cena muda, não verso a verso). Já as TAGS de clima usadas
    pra escolher a trilha de cada segmento seguem a mesma cascata do
    match visual: tenta primeiro o TÍTULO do primeiro versículo do
    segmento (mais específico, se `titulo_clima_dict` foi passado e
    tiver clima cadastrado) -- só cai pro clima do EVENTO como um todo
    se o título não tiver clima próprio.

    `trilha_pool`: lista pequena e curada à mão (não o estoque inteiro)
    -- ver carregar_estoque_som_da_planilha(aba, "trilha") + filtro
    pelos ids/urls colados na Configuração do notebook.

    Segmento sem evento reconhecido no léxico, ou sem clima cadastrado
    (nem no título nem no evento), ou sem nenhuma trilha do pool batendo
    tag nenhuma, fica com "trilha": None -- SILÊNCIO nesse trecho, não é
    erro (ver relatorio_lacunas_trilha pra revisar depois; normalmente
    resolve ampliando o trilha_pool ou preenchendo tags_clima do
    evento/título em sincronizar-evento-titulo-tags.ipynb).

    Retorna lista de dicts: [{"evento_id", "titulo_evento", "versiculos":
    [1,2,3], "inicio_ms", "fim_ms", "duracao_seg", "trilha": {...} ou None}]
    """
    from match_pipeline import buscar_contexto_biblico

    titulo_clima_dict = titulo_clima_dict or {}
    versos_ordenados = sorted(tempos_versiculo.keys())

    # ── 1. evento/título de cada versículo (mesma busca léxica do match de cena) ──
    contexto_por_verso = {}
    for v in versos_ordenados:
        contexto_por_verso[v] = buscar_contexto_biblico(livro_pt, capitulo, v, titulos_biblicos, eventos_biblicos)

    # ── 2. limites brutos de cada versículo ─────────────────────────────
    brutos = []
    for i, v in enumerate(versos_ordenados):
        inicio = tempos_versiculo[v]
        fim = tempos_versiculo[versos_ordenados[i + 1]] if i + 1 < len(versos_ordenados) else duracao_total_ms
        contexto = contexto_por_verso[v]
        brutos.append({"versiculos": [v], "inicio_ms": inicio, "fim_ms": fim,
                        "evento_id": contexto.get("evento_id"), "titulo_evento": contexto.get("titulo_evento"),
                        "titulo_id": contexto.get("titulo_id")})

    # ── 3. funde versículos consecutivos do MESMO evento num só segmento ──
    segmentos = []
    for seg in brutos:
        anterior = segmentos[-1] if segmentos else None
        if anterior and anterior["evento_id"] == seg["evento_id"]:
            anterior["fim_ms"] = seg["fim_ms"]
            anterior["versiculos"].extend(seg["versiculos"])
        else:
            segmentos.append(seg)

    # ── 4. casa a trilha de cada segmento (título → evento) ─────────────
    plano = []
    for seg in segmentos:
        tags_clima = []
        if seg["titulo_id"] and seg["titulo_id"] in titulo_clima_dict:
            tags_clima = titulo_clima_dict[seg["titulo_id"]]["tags_clima_semelhantes"] \
                or titulo_clima_dict[seg["titulo_id"]]["tags_clima"]
        if not tags_clima and seg["evento_id"] and seg["evento_id"] in evento_clima_dict:
            tags_clima = evento_clima_dict[seg["evento_id"]]["tags_clima_semelhantes"] \
                or evento_clima_dict[seg["evento_id"]]["tags_clima"]

        trilha_escolhida = None
        if tags_clima:
            candidatos = pontuar_trilhas(tags_clima, trilha_pool)
            if candidatos:
                trilha_escolhida = candidatos[0]

        plano.append({
            "evento_id": seg["evento_id"],
            "titulo_evento": seg["titulo_evento"],
            "versiculos": seg["versiculos"],
            "inicio_ms": seg["inicio_ms"],
            "fim_ms": seg["fim_ms"],
            "duracao_seg": max(0.5, (seg["fim_ms"] - seg["inicio_ms"]) / 1000.0),
            "trilha": trilha_escolhida,
        })

    return plano


def relatorio_lacunas_trilha(plano_segmentos):
    """
    Texto legível com os segmentos que ficaram SEM trilha (ver
    calcular_segmentos_trilha) -- pra você revisar e decidir se amplia o
    trilha_pool, cadastra tags_clima que faltam no evento, ou aceita o
    silêncio ali mesmo. Retorna None se não há lacuna nenhuma.
    """
    lacunas = [s for s in plano_segmentos if not s["trilha"]]
    if not lacunas:
        return None
    linhas = [f"{len(lacunas)} segmento(s) SEM TRILHA (silêncio nesse trecho):\n"]
    for s in lacunas:
        v_ini, v_fim = s["versiculos"][0], s["versiculos"][-1]
        faixa = f"v{v_ini}" if v_ini == v_fim else f"v{v_ini}-{v_fim}"
        motivo = "evento não reconhecido no léxico" if not s["evento_id"] else \
            f"evento '{s['titulo_evento']}' sem trilha do pool com clima em comum"
        linhas.append(f"  {faixa:>10s}  ({s['duracao_seg']:.1f}s) -- {motivo}")
    return "\n".join(linhas)


def baixar_trilha(url, destino):
    """Baixa um arquivo de trilha (url_download, ou url_preview como
    alternativa) pro caminho local `destino`. Retorna True se deu certo."""
    import requests
    from pathlib import Path

    destino = Path(destino)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
        r.raise_for_status()
        with open(destino, "wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    except Exception:
        return False
    return destino.exists() and destino.stat().st_size > 1000


# ── Vocabulário fechado de clima (1 palavra representante por grupo do
# dicionario_sinonimos_clima.py) -- dado pra IA como opções, pra sempre
# sugerir algo que já bate com um grupo de sinônimo conhecido, em vez de
# inventar palavra nova toda vez. ──────────────────────────────────────
VOCABULARIO_CLIMA = [grupo[0] for grupo in GRUPOS_CLIMA_PT]


def sugerir_tags_clima_eventos_em_lote(eventos, groq_client, mistral_client, estado_provedor,
                                          modelo_groq, modelo_mistral, tamanho_lote=15, max_tokens=2000,
                                          timeout_segundos=45):
    """
    Pede pra IA (Groq/Mistral, rodízio com fallback em qualquer erro --
    mesmo padrão de traduzir_tags_em_lote) sugerir 1-3 tags de CLIMA por
    evento, escolhendo do vocabulário fechado (VOCABULARIO_CLIMA) --
    em LOTE (~15 eventos por chamada), não 1 por evento.

    `eventos`: lista de dicts com pelo menos "id" e "titulo" (e
    "personagens", se tiver -- ajuda a IA a captar o clima certo).

    `timeout_segundos`: cada chamada desiste sozinha depois desse tempo
    (em vez de travar sem aviso nenhum -- foi isso que aconteceu numa
    rodada de teste: sem timeout, sem print de progresso, parecia
    travado e não dava pra saber se ia terminar ou não).

    Imprime o progresso a cada lote (X/Y) -- pra você ver que está
    avançando, não só silêncio até o fim.

    Retorna dict {evento_id: [tags_clima]} -- SÓ sugestão, "os dois"
    conforme combinado: você revisa/corrige direto na planilha depois
    (a IA não é a palavra final)."""
    resultado = {}
    total_lotes = (len(eventos) + tamanho_lote - 1) // tamanho_lote

    for num_lote, i in enumerate(range(0, len(eventos), tamanho_lote), start=1):
        lote = eventos[i:i + tamanho_lote]
        itens_prompt = [
            {"id": e.get("id"), "titulo": e.get("titulo", ""), "personagens": e.get("personagens", [])}
            for e in lote
        ]
        prompt = f"""Pra cada cena bíblica abaixo, sugira de 1 a 3 palavras de CLIMA/EMOÇÃO
(como a cena deveria SOAR musicalmente, não como ela parece visualmente)
-- escolha SÓ dessa lista fechada, copiando exatamente como está escrito:

{", ".join(VOCABULARIO_CLIMA)}

Cenas:
{json.dumps(itens_prompt, ensure_ascii=False)}

Retorne JSON estrito: {{"climas": {{"id_do_evento": ["palavra1", "palavra2"], ...}}}}
-- uma entrada por evento da lista, na mesma ordem."""

        def _chamar(provedor):
            if provedor == "groq":
                res = groq_client.chat.completions.create(
                    model=modelo_groq, messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.3, max_tokens=max_tokens,
                    timeout=timeout_segundos,
                )
                return json.loads(res.choices[0].message.content)
            else:
                res = mistral_client.chat.complete(
                    model=modelo_mistral, messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.3, max_tokens=max_tokens,
                    timeout_ms=timeout_segundos * 1000,
                )
                return json.loads(res.choices[0].message.content)

        primeiro = estado_provedor["atual"]
        segundo = "mistral" if primeiro == "groq" else "groq"
        climas = {}
        erro_final = None
        sucesso = False
        for provedor in (primeiro, segundo):
            cliente = groq_client if provedor == "groq" else mistral_client
            if not cliente:
                continue
            try:
                dados = _chamar(provedor)
                estado_provedor["atual"] = segundo if provedor == primeiro else primeiro
                climas = dados.get("climas", {})
                sucesso = True
                break
            except Exception as e:
                erro_final = e
                continue  # tenta o outro provedor -- qualquer erro, nao so cota

        for evento in lote:
            resultado[evento["id"]] = climas.get(evento["id"], [])

        status = "✅" if sucesso else f"⚠️ falhou nos dois provedores ({erro_final})"
        print(f"   [{num_lote}/{total_lotes}] {len(lote)} evento(s) -- {status}")

    return resultado


def _col_letra(indice_1_based):
    """Converte índice de coluna (1=A, 2=B, ..., 27=AA) pra letra --
    sem depender de gspread.utils aqui (módulo standalone)."""
    letras = ""
    n = indice_1_based
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def gravar_tags_clima(aba, climas_por_id, coluna_id="evento_id"):
    """
    Escreve os climas sugeridos (dict {id: [tags]}, ver
    sugerir_tags_clima_eventos_em_lote) nas colunas tags_clima/
    tags_clima_semelhantes -- ATUALIZA a linha que já existe (achada
    pelo `coluna_id` -- "evento_id" pra aba evento_tags, "titulo_id"
    pra aba titulo_tags), não duplica. Só grava quem ainda está vazio
    (não sobrescreve uma correção que você já fez na mão -- revisão
    manual, "os dois" conforme combinado).

    AUTOCURA: se as colunas tags_clima/tags_clima_semelhantes ainda não
    existirem no cabeçalho por algum motivo (ex: a migração de
    garantir_aba_evento_tags/titulo_tags não rodou antes por qualquer
    razão), cria elas aqui mesmo antes de gravar, em vez de travar com
    KeyError -- isso já aconteceu uma vez depois de 191 lotes de IA já
    processados, perdendo só a gravação (não o trabalho da IA) por
    causa de uma coluna faltando."""
    cabecalho = aba.row_values(1)
    faltando = [c for c in ("tags_clima", "tags_clima_semelhantes") if c not in cabecalho]
    if faltando:
        if len(cabecalho) + len(faltando) > aba.col_count:
            aba.add_cols(len(cabecalho) + len(faltando) - aba.col_count)
        for i, nome in enumerate(faltando):
            aba.update_cell(1, len(cabecalho) + 1 + i, nome)
        cabecalho = cabecalho + faltando

    dados = aba.get_all_records()
    col = {nome: i + 1 for i, nome in enumerate(cabecalho)}

    atualizados = 0
    corpo = []
    for i, linha in enumerate(dados):
        item_id = str(linha.get(coluna_id, ""))
        if item_id not in climas_por_id:
            continue
        if str(linha.get("tags_clima", "")).strip():
            continue  # já tem algo (sugestão anterior ou correção manual sua) -- não sobrescreve
        tags = climas_por_id[item_id]
        if not tags:
            continue
        tags_semelhantes = expandir_tags_clima(tags)
        num_linha = i + 2  # +1 cabeçalho, +1 índice 1-based
        corpo.append({"range": f"{_col_letra(col['tags_clima'])}{num_linha}", "values": [[", ".join(tags)]]})
        corpo.append({"range": f"{_col_letra(col['tags_clima_semelhantes'])}{num_linha}", "values": [[", ".join(tags_semelhantes)]]})
        atualizados += 1

    if corpo:
        aba.batch_update(corpo)
    return atualizados


# ── Estoque ÚNICO de som (trilha + efeito) ──────────────────────────────────
# Uma aba só, ainda chamada "trilha_stock" de propósito -- é o nome que o
# painel de revisão (Apps Script, fora deste repo) já espera; renomear a
# aba quebraria o painel sem a gente conseguir perceber daqui. As 10
# primeiras colunas são EXATAMENTE as de sempre, na mesma ordem -- as 3
# novas (categoria, tags_concretas*) vão sempre no FINAL, nunca no meio.
COLUNAS_TRILHA_STOCK = ["id", "titulo", "url_preview", "url_download", "autor", "duracao_s",
                          "tags_clima", "tags_clima_semelhantes", "fonte", "data_sincronizacao"]
COLUNAS_ESTOQUE_SOM = COLUNAS_TRILHA_STOCK + ["categoria", "tags_concretas", "tags_concretas_semelhantes"]


def garantir_aba_estoque_som(spreadsheet, nome_aba="trilha_stock"):
    """Acha (ou cria) a aba única de estoque de som -- guarda TANTO
    trilha quanto efeito sonoro, diferenciados pela coluna `categoria`
    ("trilha", "efeito" ou "ambos") -- mesma planilha da Biblioteca de
    Match. `url_preview` é o que o painel usa pra tocar um trechinho
    antes de escolher (Freesound: link direto do MP3 de prévia; manual:
    vazio, é arquivo local do YouTube Audio Library).

    Migra o cabeçalho sozinha se a aba já existir no formato antigo (só
    as 10 colunas de trilha) -- ACRESCENTA as 3 colunas novas no final,
    nunca reordena as que já existem (ver nota de COLUNAS_ESTOQUE_SOM)."""
    try:
        aba = spreadsheet.worksheet(nome_aba)
    except Exception:
        aba = spreadsheet.add_worksheet(title=nome_aba, rows=200, cols=len(COLUNAS_ESTOQUE_SOM))
        aba.append_row(COLUNAS_ESTOQUE_SOM)
        return aba

    cabecalho_atual = aba.row_values(1)
    if cabecalho_atual != COLUNAS_ESTOQUE_SOM:
        if len(COLUNAS_ESTOQUE_SOM) > aba.col_count:
            aba.add_cols(len(COLUNAS_ESTOQUE_SOM) - aba.col_count)
        aba.update(values=[COLUNAS_ESTOQUE_SOM], range_name=f"A1:{_col_letra(len(COLUNAS_ESTOQUE_SOM))}1")
    return aba


def sincronizar_estoque_som(aba_estoque_som, itens_normalizados):
    """
    Escreve o estoque de som (trilha e/ou efeito, já normalizado -- ver
    carregar_trilha_stock_freesound()/carregar_trilha_stock_manual()/
    carregar_trilha_stock_pasta_drive() [categoria="trilha"] e
    carregar_efeitos_stock_freesound()/carregar_efeitos_stock_pasta_drive()
    [categoria="efeito"]) na aba única -- ATUALIZA quem já existe (mesmo
    id+fonte), SÓ ADICIONA quem é novo. Não duplica rodando de novo.

    Cada item já vem com "categoria" e a lista de tags correspondente
    ("tags_clima" pra trilha, "tags_concretas" pra efeito) -- a outra
    coluna de tag fica em branco pra esse item (a menos que você preencha
    os dois na mão, na planilha, pra marcar um som de uso duplo)."""
    from datetime import datetime
    existentes = {}  # (id, fonte) -> numero da linha (1-based, já contando cabecalho)
    dados_atuais = aba_estoque_som.get_all_records()
    for i, linha in enumerate(dados_atuais):
        existentes[(str(linha.get("id", "")), linha.get("fonte", ""))] = i + 2

    corpo_update = []
    linhas_novas = []
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    for item in itens_normalizados:
        chave = (str(item["id"]), item["fonte"])
        tags_clima = item.get("tags_clima", [])
        tags_concretas = item.get("tags_concretas", [])
        valores = [
            item["id"], item["titulo"], item["url"], item.get("url_download", ""),
            item["autor"], item.get("duracao_s", ""),
            ", ".join(tags_clima), ", ".join(expandir_tags_clima(tags_clima)) if tags_clima else "",
            item["fonte"], agora,
            item.get("categoria", ""),
            ", ".join(tags_concretas), ", ".join(_expandir_visual(tags_concretas)) if tags_concretas else "",
        ]
        if chave in existentes:
            num_linha = existentes[chave]
            corpo_update.append({"range": f"A{num_linha}:{_col_letra(len(COLUNAS_ESTOQUE_SOM))}{num_linha}", "values": [valores]})
        else:
            linhas_novas.append(valores)

    if corpo_update:
        aba_estoque_som.batch_update(corpo_update)
    if linhas_novas:
        aba_estoque_som.append_rows(linhas_novas, value_input_option="USER_ENTERED")

    return len(linhas_novas), len(corpo_update)


def carregar_estoque_som_da_planilha(aba_estoque_som, categoria):
    """
    Lê a aba única de estoque de som e devolve no formato pronto pro
    match, filtrado por `categoria` ("trilha" ou "efeito" -- itens
    marcados "ambos" na planilha entram nos dois).

    Pra "trilha": {id, titulo, url, autor, tags_clima, fonte} (lê
    tags_clima_semelhantes) -- formato que pontuar_trilhas() espera.
    Pra "efeito": {id, titulo, url, autor, tags, fonte} (lê
    tags_concretas_semelhantes) -- formato que pontuar_efeitos() espera.

    Linha sem a coluna `categoria` preenchida (ex: dado antigo, de antes
    dessa migração) não entra em nenhum dos dois -- rode
    organizar-trilha-audio.ipynb/organizar-efeitos-audio.ipynb de novo
    pra preencher a categoria retroativamente.
    """
    if categoria not in ("trilha", "efeito"):
        raise ValueError(f"categoria inválida: {categoria!r} (use 'trilha' ou 'efeito')")

    resultado = []
    for linha in aba_estoque_som.get_all_records():
        cat_linha = str(linha.get("categoria", "")).strip().lower()
        if cat_linha not in (categoria, "ambos"):
            continue
        item = {
            "id": str(linha.get("id", "")),
            "titulo": linha.get("titulo", ""),
            "url": linha.get("url_preview", ""),
            "autor": linha.get("autor", ""),
            "fonte": linha.get("fonte", ""),
        }
        if categoria == "trilha":
            item["tags_clima"] = [t.strip() for t in str(linha.get("tags_clima_semelhantes", "")).split(",") if t.strip()]
        else:
            item["tags"] = [t.strip() for t in str(linha.get("tags_concretas_semelhantes", "")).split(",") if t.strip()]
        resultado.append(item)
    return resultado


def parsear_nome_arquivo_trilha(nome_arquivo):
    """
    Extrai titulo/autor/fonte de um nome de arquivo .mp3 baixado do
    YouTube Audio Library ou Pixabay -- os dois vêm com nome bagunçado
    (clima + "créditos" + nome + autor, tudo junto, separadores
    inconsistentes) -- ver exemplos reais testados no notebook
    organizar-trilha-audio.ipynb.

    O CLIMA não vem daqui -- vem do nome da PASTA onde o arquivo está
    (ver carregar_trilha_stock_pasta_drive), que é mais confiável que
    tentar ler o clima solto no nome do arquivo.
    """
    import re
    nome = nome_arquivo
    if nome.lower().endswith(".mp3"):
        nome = nome[:-4]
    elif nome.lower().endswith("mp3"):
        nome = nome[:-3]

    m = re.search(r"cr[ée]ditos[\s\-@:]*", nome, re.IGNORECASE)
    resto = nome[m.end():].strip() if m else nome.strip()

    eh_youtube = bool(re.search(r"youtube", resto, re.IGNORECASE))
    fonte = "YouTube Audio Library" if eh_youtube else "Pixabay"

    if fonte == "YouTube Audio Library":
        # remove "(Youtube Audio Library)" (com o parêntese de FECHAMENTO
        # incluso) -- tem que rodar ANTES de qualquer strip de parêntese
        # solto, senão o ")" de fechamento pode já ter sumido e o regex
        # não encontra mais o padrão completo pra remover
        resto_sem_fonte = re.sub(r"\(\s*youtube.*?audio.*?library.*?\)", "", resto, flags=re.IGNORECASE).strip()
        partes = resto_sem_fonte.split(" - ")
        titulo = partes[0].strip() if partes else resto_sem_fonte
        autor = partes[1].strip() if len(partes) > 1 else ""
    else:
        # Pixabay -- aqui sim pode ter parêntese solto (ex: "@Nome-do-som(
        # httpspixabay...)") -- tira só nesse ramo, depois de já ter
        # decidido a fonte
        resto = resto.strip("()").strip()
        m2 = re.search(r"(https?pixabay\.com.*)$", resto, re.IGNORECASE)
        if m2:
            titulo = resto[:m2.start()].strip().rstrip("(").strip()
            autor = m2.group(1).strip().rstrip(")").strip()
        else:
            titulo = resto
            autor = ""

    return {"titulo": titulo, "autor": autor, "fonte": fonte}


def url_drive_tocavel(file_id, url_proxy_apps_script=None):
    """Monta o link que toca no <audio> HTML do painel de trilha.

    IMPORTANTE: desde jan/2024 o Google BLOQUEIA embutir arquivo do
    Drive direto num <audio>/<img> de fora do próprio Drive (erro 403 --
    é bloqueio no servidor do Google, não tem jeito só mexendo no HTML).
    Por isso, se `url_proxy_apps_script` for passado (a URL do Web App
    que você publicou a partir do Code.gs -- ver função doGet lá),
    monta o link APONTANDO PRO PROXY (que serve o arquivo através do
    domínio do próprio Apps Script, contornando o bloqueio) -- é o
    formato que você deve usar.

    Sem `url_proxy_apps_script` (None), cai pro link direto antigo, que
    NÃO funciona mais embutido -- só existe pra não quebrar código
    antigo que ainda não migrou."""
    if url_proxy_apps_script:
        return f"{url_proxy_apps_script.rstrip('/')}?id={file_id}"
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def tornar_arquivo_publico(drive_service, file_id):
    """Compartilha o arquivo como 'qualquer pessoa com o link pode ver'
    -- sem isso, url_drive_tocavel() gera um link que existe mas não
    toca (dá erro de permissão). Idempotente -- rodar de novo não duplica
    a permissão nem dá erro se já estiver público."""
    try:
        drive_service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"},
        ).execute()
    except Exception as e:
        # se já for público, a API às vezes reclama de permissão duplicada --
        # não é um erro que precise travar o processo
        print(f"   ⚠️  Não consegui confirmar permissão pública de {file_id}: {e}")


def listar_subpastas(drive_service, pasta_pai_id):
    """Lista as subpastas DIRETAS de uma pasta (cada uma = um clima, ver
    carregar_trilha_stock_pasta_drive)."""
    resultado = drive_service.files().list(
        q=f"'{pasta_pai_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)", pageSize=200,
    ).execute()
    return resultado.get("files", [])


def listar_mp3_da_pasta(drive_service, pasta_id):
    """Lista os arquivos .mp3 dentro de uma pasta (não desce em
    subpastas -- cada pasta de clima deve ter os mp3 direto dentro)."""
    resultado = drive_service.files().list(
        q=f"'{pasta_id}' in parents and trashed=false and name contains '.mp3'",
        fields="files(id, name)", pageSize=500,
    ).execute()
    return resultado.get("files", [])


def achar_pasta_por_caminho(drive_service, caminho_relativo, pasta_raiz_id=None):
    """Acha o ID de uma pasta pelo caminho tipo 'Pasta/Subpasta'.

    A PRIMEIRA parte do caminho é buscada em TODO o Drive acessível
    (incluindo pastas que OUTRA CONTA compartilhou com você) -- não só
    dentro do seu "Meu Drive". Isso importa porque uma pasta
    compartilhada nunca aparece como filha de "root" pra quem recebeu o
    compartilhamento, mesmo com permissão de Editor -- ela mantém a
    posição na hierarquia de quem é dono original. Buscar só "dentro de
    root" (jeito antigo) nunca ia achar nesse caso.

    As partes SEGUINTES do caminho já usam o ID do pai encontrado, que
    funciona normalmente (relação pai-filho não muda por conta de
    compartilhamento, só a primeira pasta precisa da busca ampla)."""
    partes = caminho_relativo.strip("/").split("/")
    atual = pasta_raiz_id
    for i, parte in enumerate(partes):
        if i == 0 and pasta_raiz_id is None:
            q = f"name='{parte}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        else:
            q = f"'{atual}' in parents and name='{parte}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        resultado = drive_service.files().list(
            q=q, fields="files(id, name)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        achados = resultado.get("files", [])
        if not achados:
            onde = f"dentro de {atual}" if atual else "(nem no seu Drive, nem em pastas compartilhadas com você)"
            raise FileNotFoundError(f"Pasta '{parte}' não encontrada {onde}")
        atual = achados[0]["id"]
    return atual


def carregar_trilha_stock_pasta_drive(drive_service, pasta_raiz_id, tornar_publico=True, url_proxy_apps_script=None):
    """
    Varre as SUBPASTAS de `pasta_raiz_id` (cada subpasta = um clima, ex:
    audio/alegre/, audio/dramatico/) e lista os .mp3 de cada uma --
    parseia titulo/autor/fonte do nome do arquivo (ver
    parsear_nome_arquivo_trilha), usa o NOME DA PASTA como tags_clima,
    e monta o link tocável (ver url_drive_tocavel).

    `url_proxy_apps_script`: a URL do Web App publicado a partir do
    Code.gs (função doGet) -- OBRIGATÓRIO na prática, já que o link
    direto do Drive não toca mais embutido (bloqueio do Google desde
    jan/2024). Sem isso, os links gerados existem mas não vão tocar no
    painel.

    Se `tornar_publico=True` (padrão), compartilha cada arquivo como
    'qualquer pessoa com o link' automaticamente -- sem isso, o link
    existe mas não toca (erro de permissão). Só precisa rodar uma vez
    por arquivo (não duplica se já estiver público).

    Devolve no MESMO formato comum que carregar_trilha_stock_freesound/
    manual -- pronto pra sincronizar_estoque_som()."""
    resultado = []
    subpastas = listar_subpastas(drive_service, pasta_raiz_id)
    print(f"   📁 {len(subpastas)} subpasta(s) de clima encontrada(s): {', '.join(p['name'] for p in subpastas)}")

    for pasta in subpastas:
        clima_base = pasta["name"].strip().lower()
        # "Esperança x Vitória" -> ["esperança", "vitória"] -- nome de pasta
        # pode juntar mais de um clima com " x "
        climas = [c.strip() for c in clima_base.split(" x ") if c.strip()]

        arquivos = listar_mp3_da_pasta(drive_service, pasta["id"])
        print(f"   📂 {pasta['name']}: {len(arquivos)} arquivo(s)")

        for arquivo in arquivos:
            info = parsear_nome_arquivo_trilha(arquivo["name"])
            if tornar_publico:
                tornar_arquivo_publico(drive_service, arquivo["id"])
            resultado.append({
                "id": arquivo["id"],
                "titulo": info["titulo"],
                "url": url_drive_tocavel(arquivo["id"], url_proxy_apps_script),
                "autor": info["autor"],
                "tags_clima": expandir_tags_clima(climas),
                "categoria": "trilha",
                "fonte": info["fonte"],
                "nome_arquivo": arquivo["name"],
            })

    return resultado


# ==============================================
# EFEITOS SONOROS -- diferente de trilha: casa por AÇÃO/OBJETO CONCRETO
# (porta, trovão, espada, cavalo...), não por clima -- reaproveita o
# dicionário de sinônimo VISUAL (dicionario_sinonimos.py), o mesmo que
# a imagem usa, não o de clima. E é pontual (mais de um efeito pode
# coexistir no mesmo versículo -- diferente de trilha, que é 1 vencedor
# só por versículo).
# ==============================================

from dicionario_sinonimos import expandir_tags_semelhantes as _expandir_visual, MAPA_SINONIMOS_PT as _MAPA_VISUAL_PT


def extrair_tags_efeito_de_lista_bruta(tags_brutas):
    """Igual extrair_tags_clima_de_lista_bruta, mas filtra pelo
    dicionário VISUAL (concreto), não pelo de clima -- usado pro
    Freesound, cujas tags cruas às vezes têm palavra de ação/objeto
    junto com termo técnico."""
    tags_concretas = [t for t in tags_brutas if _normalizar_palavra(t) in _MAPA_VISUAL_PT]
    return _expandir_visual(tags_concretas)


def carregar_efeitos_stock_freesound(linhas_planilha, coluna_tags="Tags", coluna_id="ID",
                                        coluna_titulo="Título", coluna_url="URL Preview", coluna_autor="Autor"):
    """Igual carregar_trilha_stock_freesound, mas filtra por tag
    CONCRETA (visual), não clima -- devolve categoria="efeito", pronta
    pra sincronizar_estoque_som()."""
    resultado = []
    for linha in linhas_planilha:
        tags_brutas = [t.strip() for t in str(linha.get(coluna_tags, "")).split(",") if t.strip()]
        tags_concretas = extrair_tags_efeito_de_lista_bruta(tags_brutas)
        if not tags_concretas:
            continue
        resultado.append({
            "id": str(linha.get(coluna_id, "")),
            "titulo": linha.get(coluna_titulo, ""),
            "url": linha.get(coluna_url, ""),
            "autor": linha.get(coluna_autor, ""),
            "tags_concretas": tags_concretas,
            "categoria": "efeito",
            "fonte": "freesound",
        })
    return resultado


def carregar_efeitos_stock_pasta_drive(drive_service, pasta_raiz_id, tornar_publico=True):
    """
    Igual carregar_trilha_stock_pasta_drive, mas cada SUBPASTA é um
    OBJETO/AÇÃO concreta (ex: efeitos/porta/, efeitos/trovao/,
    efeitos/cavalo/), não um clima -- expande via dicionário VISUAL.

    Devolve no formato {id, titulo, url, autor, tags_concretas,
    categoria, fonte, nome_arquivo} -- pronto pra
    sincronizar_estoque_som()."""
    resultado = []
    subpastas = listar_subpastas(drive_service, pasta_raiz_id)
    print(f"   📁 {len(subpastas)} subpasta(s) de efeito encontrada(s): {', '.join(p['name'] for p in subpastas)}")

    for pasta in subpastas:
        objeto_base = pasta["name"].strip().lower()
        objetos = [o.strip() for o in objeto_base.split(" x ") if o.strip()]

        arquivos = listar_mp3_da_pasta(drive_service, pasta["id"])
        print(f"   📂 {pasta['name']}: {len(arquivos)} arquivo(s)")

        for arquivo in arquivos:
            info = parsear_nome_arquivo_trilha(arquivo["name"])
            if tornar_publico:
                tornar_arquivo_publico(drive_service, arquivo["id"])
            resultado.append({
                "id": arquivo["id"],
                "titulo": info["titulo"],
                "url": url_drive_tocavel(arquivo["id"]),  # não usado pelo painel (bloqueio do Drive) -- só referência
                "autor": info["autor"],
                "tags_concretas": _expandir_visual(objetos),
                "categoria": "efeito",
                "fonte": info["fonte"],
                "nome_arquivo": arquivo["name"],
            })

    return resultado


def pontuar_efeitos(tags_alvo, efeitos_pool):
    """Mesma lógica de pontuar_trilhas(), pro universo de EFEITO sonoro:
    pontua cada efeito do `efeitos_pool` pela sobreposição de tags
    CONCRETAS (porta, trovão, cavalo...) contra o alvo (palavras-chave do
    versículo), ordena do melhor pro pior."""
    alvo_normalizado = {_normalizar_palavra(t) for t in tags_alvo}
    candidatos = []
    for efeito in efeitos_pool:
        tags_efeito_normalizadas = {_normalizar_palavra(t) for t in efeito["tags"]}
        batidas = alvo_normalizado & tags_efeito_normalizadas
        if batidas:
            candidatos.append({**efeito, "score": len(batidas), "tags_batidas": sorted(batidas)})
    return sorted(candidatos, key=lambda c: -c["score"])


def calcular_efeitos_pontuais(tempos_versiculo, livro_pt, capitulo, versiculo_tags_dict,
                                 efeitos_pool, dist_min_repeticao=2):
    """
    Casa um efeito sonoro pontual pra cada versículo cujas palavras-chave
    (`tags_semelhantes`, já calculadas no match de cena -- ver
    match_pipeline.carregar_versiculo_tags/registrar_tags_versiculo)
    baterem com alguma candidata do `efeitos_pool` (curado à mão, igual
    o trilha_pool). Diferente da trilha: é por VERSÍCULO individual (não
    agrupa em segmentos) e a maioria dos versículos fica SEM efeito
    nenhum -- é pontual de propósito, só pros momentos concretos (porta
    batendo, trovão, cavalo...), não uma trilha de fundo contínua.

    Evita repetir o MESMO efeito em versículos muito próximos
    (`dist_min_repeticao`), igual à anti-repetição do match de cena.

    Versículo sem tags_semelhantes cadastradas (match de cena não achou
    palavra-chave nenhuma) ou sem nenhum efeito do pool batendo é
    simplesmente OMITIDO do resultado -- não é lacuna, é o esperado (nem
    todo versículo precisa de efeito).

    Retorna lista só com os versículos que TIVERAM match:
    [{"versiculo", "inicio_ms", "efeito": {...}}]
    """
    ultimo_uso = {}
    pontos = []
    for v in sorted(tempos_versiculo.keys()):
        chave = (str(livro_pt), str(capitulo), str(v))
        linha = versiculo_tags_dict.get(chave)
        if not linha:
            continue
        tags_alvo = [t.strip() for t in str(linha.get("tags_semelhantes", "")).split(",") if t.strip()]
        if not tags_alvo:
            continue

        candidatos = pontuar_efeitos(tags_alvo, efeitos_pool)
        escolhido = None
        for candidato in candidatos:
            ultima_vez = ultimo_uso.get(candidato["id"])
            if ultima_vez is None or (v - ultima_vez) >= dist_min_repeticao:
                escolhido = candidato
                break

        if escolhido:
            ultimo_uso[escolhido["id"]] = v
            pontos.append({"versiculo": v, "inicio_ms": tempos_versiculo[v], "efeito": escolhido})

    return pontos
