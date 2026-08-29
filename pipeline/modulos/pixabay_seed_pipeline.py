# -*- coding: utf-8 -*-
"""
pixabay_seed_pipeline.py — Semeadura automática da image-stock via léxico

Em vez de buscar imagem por imagem na hora do match (ou manualmente no
Pixabay Image Manager), este módulo varre eventos-biblicos.js e busca
imagens na API do Pixabay PRA CADA EVENTO ainda sem cobertura, já
marcando o rastreio (Chave_Match_*) e o intervalo de capítulo
(estruturado, não só texto) na planilha -- você só revisa e escolhe o
vencedor de cada versículo depois, sem digitar nada.

Fluxo:
    1. eventos_para_semear()      — filtra eventos-biblicos.js por livro
                                     (+ capítulo, opcional) que ainda não
                                     têm imagem (nem na biblioteca de
                                     match, nem já semeada antes)
    2. semear_imagens_lote()      — busca no Pixabay + escreve na
                                     image-stock, com Chave_Match_* e o
                                     intervalo Capitulo_Ini/Fim
                                     (Versiculo_Ini/Fim ficam vazios pra
                                     semeadura por evento -- só título
                                     dá esse nível)
    3. [roda pixabay-image-descriptions.ipynb -- é ele quem preenche
       Tags_PT/EN e Tags_Semelhantes_PT/EN, a partir do CONTEÚDO real da
       imagem via visão, não mais de uma lista fechada de temas bíblicos]
    4. [você escolhe o vencedor de cada versículo no painel de revisão
       do Apps Script (Code.gs/PainelRevisao.html) -- grava direto na
       biblioteca de match, sem passar por aqui de novo]

Reaproveita _parse_referencia_evento() do match_pipeline.py.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

import requests

from match_pipeline import (
    _parse_referencia_evento,
    carregar_biblioteca_match,
    registrar_na_biblioteca_match,
)
from dicionario_sinonimos import expandir_tags_semelhantes
from pixabay_urls import url_estavel

COLUNAS_EXTRAS_SEED = ["Vezes_Usada"]

COLUNAS_ITENS_SEMEADOS = ["nivel", "item_id", "data_criacao"]


def garantir_aba_eventos_semeados(spreadsheet, nome_aba="eventos_semeados"):
    """
    Acha (ou cria) a aba que registra QUAIS ITENS (evento, título OU
    versículo) já tiveram uma busca em lote feita -- vive na Biblioteca
    de Match (mesma planilha de biblioteca_match/versiculo_tags), NÃO na
    image-stock, porque a image-stock agora só guarda as tags da própria
    imagem, nenhum contexto bíblico.

    Uma aba só serve os 3 níveis (coluna `nivel` distingue) -- mais
    simples que 3 abas separadas. Se a aba já existir no formato antigo
    (só "evento_id", sem "nivel"), completa o cabeçalho sem apagar as
    linhas já gravadas (tratadas como nivel="evento" por
    carregar_itens_semeados, ver lá).
    """
    try:
        aba = spreadsheet.worksheet(nome_aba)
        cabecalho = aba.row_values(1)
        if cabecalho == ["evento_id", "data_criacao"]:
            aba.update_cell(1, 1, "item_id")
            aba.insert_cols([["nivel"]], 1)
            aba.update_cell(1, 1, "nivel")
            for i in range(2, aba.row_count + 1):
                if aba.cell(i, 2).value:
                    aba.update_cell(i, 1, "evento")  # linhas antigas eram todas de evento
        return aba
    except Exception:
        aba = spreadsheet.add_worksheet(title=nome_aba, rows=2000, cols=len(COLUNAS_ITENS_SEMEADOS))
        aba.append_row(COLUNAS_ITENS_SEMEADOS)
        return aba


def carregar_itens_semeados(aba_itens_semeados, nivel):
    """IDs (só do `nivel` pedido: 'evento'/'titulo'/'versiculo') que já
    tiveram uma busca em lote feita antes -- evita buscar de novo no
    Pixabay pro mesmo item."""
    linhas = aba_itens_semeados.get_all_records()
    return {str(l.get("item_id", "")).strip() for l in linhas if l.get("nivel") == nivel and l.get("item_id")}


def registrar_item_semeado(aba_itens_semeados, nivel, item_id):
    """Marca um item (evento/título/versículo) como já semeado -- uma vez
    só por item, depois da busca no Pixabay (com sucesso ou não, pra não
    ficar tentando de novo um termo que não trouxe nada)."""
    from datetime import datetime
    aba_itens_semeados.append_row([nivel, item_id, datetime.now().strftime("%Y-%m-%d %H:%M")])


# ── Compatibilidade com o nome antigo (código/notebooks já publicados) ──────
def carregar_eventos_semeados(aba_eventos_semeados):
    return carregar_itens_semeados(aba_eventos_semeados, "evento")


def registrar_evento_semeado(aba_eventos_semeados, evento_id):
    registrar_item_semeado(aba_eventos_semeados, "evento", evento_id)


def buscar_imagens_pixabay(termo, chave_api, quantidade=5, lang="pt"):
    """
    Busca imagens na API do Pixabay (endpoint de FOTOS, /api/ -- não
    confundir com /api/videos/, que é o que o video_pipeline.py usa).
    Retorna a lista de hits crus da API (dict com id, largeImageURL,
    tags, user, previewURL, imageWidth/imageHeight, etc.) -- mesmos
    campos que o seu Pixabay Image Manager (Apps Script) já usa.
    """
    if not termo or not termo.strip():
        return []
    if not chave_api:
        raise RuntimeError("CHAVE_API_PIXABAY não configurada.")

    url = (
        "https://pixabay.com/api/?key=" + chave_api
        + "&q=" + quote(termo.strip())
        + "&per_page=" + str(max(3, min(quantidade, 200)))
        + "&image_type=photo&safesearch=true&lang=" + lang
        # Só horizontais. O Apps Script que semeia os VÍDEOS já filtrava assim
        # (`&orientation=horizontal`) e o das imagens não — por isso a planilha
        # de fotos veio cheia de retrato. Foto em pé num vídeo deitado não tem
        # saída boa: ou vira tarja preta dos dois lados, ou o corte come 2/3
        # da imagem. Barrar na origem é o único conserto que não perde nada.
        + "&orientation=horizontal"
    )
    resposta = requests.get(url, timeout=30)
    if resposta.status_code != 200:
        raise RuntimeError(f"Pixabay API status {resposta.status_code}: {resposta.text[:200]}")
    dados = resposta.json()
    return dados.get("hits", [])[:quantidade]


def traduzir_tags_em_lote(tags_pt, cache_traducao, groq_client, mistral_client, estado_provedor,
                            modelo_groq, modelo_mistral, tamanho_lote=25, max_tokens=1500):
    """
    Traduz uma LISTA de tags em português pro inglês, em LOTES (uma
    chamada de IA resolve ~25 tags de uma vez, não uma chamada por
    palavra) -- pensado pra usar com listas grandes (evento + título +
    versículo + tags_semelhantes de cada um facilmente passam de 50-100
    tags por capítulo).

    `cache_traducao` é um dict {tag_pt_normalizada: tag_en} que você
    mesmo mantém entre chamadas (ou carrega do que já foi salvo antes,
    ver nome_campo_en nas funções de semeadura) -- só traduz o que AINDA
    não está no cache, e devolve o cache ATUALIZADO (as traduções novas
    já somadas às que você passou). "Sob demanda, mas guardado": você
    decide onde persistir esse cache depois (JSON do léxico, ou a coluna
    tags_semelhantes_en da versiculo_tags).

    Retorna (cache_atualizado, mapa_usado) -- mapa_usado é só as tags
    pedidas NESTA chamada, já traduzidas (via cache ou tradução nova).
    """
    def normalizar(s):
        return s.strip().lower()

    pendentes = []
    vistos = set()
    for tag in tags_pt:
        chave = normalizar(tag)
        if chave and chave not in cache_traducao and chave not in vistos:
            pendentes.append(tag.strip())
            vistos.add(chave)

    for i in range(0, len(pendentes), tamanho_lote):
        lote = pendentes[i:i + tamanho_lote]
        prompt = f"""Traduza cada uma dessas palavras/expressões em português (vocabulário
de cenas bíblicas) pro inglês -- tradução curta e direta, pensada pra
busca de fotos (Pixabay), não tradução literal de dicionário.

Palavras: {json.dumps(lote, ensure_ascii=False)}

Retorne JSON estrito: {{"traducoes": {{"palavra em pt": "translation in en", ...}}}}
-- uma entrada por palavra da lista, na mesma grafia que veio (chave
idêntica ao que foi pedido, só o valor traduzido)."""

        def _chamar(provedor):
            if provedor == "groq":
                res = groq_client.chat.completions.create(
                    model=modelo_groq, messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.2, max_tokens=max_tokens,
                )
                return json.loads(res.choices[0].message.content)
            else:
                res = mistral_client.chat.complete(
                    model=modelo_mistral, messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0.2, max_tokens=max_tokens,
                )
                return json.loads(res.choices[0].message.content)

        primeiro = estado_provedor["atual"]
        segundo = "mistral" if primeiro == "groq" else "groq"
        traducoes = {}
        for provedor in (primeiro, segundo):
            cliente = groq_client if provedor == "groq" else mistral_client
            if not cliente:
                continue
            try:
                dados = _chamar(provedor)
                estado_provedor["atual"] = segundo if provedor == primeiro else primeiro
                traducoes = dados.get("traducoes", {})
                break
            except Exception:
                continue  # tenta o outro provedor -- qualquer erro, nao so cota

        for tag in lote:
            chave = normalizar(tag)
            # aceita a traducao venha com a mesma grafia ou nao (procura
            # case-insensitive nas chaves devolvidas, cai pro proprio
            # termo em portugues se a IA nao devolveu essa palavra)
            valor = traducoes.get(tag) or next(
                (v for k, v in traducoes.items() if normalizar(k) == chave), tag
            )
            cache_traducao[chave] = valor

    mapa_usado = {tag: cache_traducao.get(normalizar(tag), tag) for tag in tags_pt}
    return cache_traducao, mapa_usado


def eventos_para_semear(eventos_biblicos, livro_pt, capitulo_ini=None, capitulo_fim=None, ja_cobertos=None):
    """
    Filtra eventos-biblicos.js por livro (e, opcionalmente, faixa de
    capítulo -- se capitulo_ini for None, pega o LIVRO INTEIRO) que
    ainda não estão em ja_cobertos (união de: já na biblioteca de match
    + já semeados na image-stock, ver eventos_ja_semeados()).
    """
    ja_cobertos = ja_cobertos or set()
    alvo = []
    for evento in eventos_biblicos:
        if str(evento.get("id", "")) in ja_cobertos:
            continue
        faixa = _parse_referencia_evento(evento.get("referencia", ""), livro_pt)
        if not faixa:
            continue
        if capitulo_ini is not None:
            fim = capitulo_fim if capitulo_fim is not None else capitulo_ini
            if faixa[1] < capitulo_ini or faixa[0] > fim:
                continue  # faixa do evento não cruza com o intervalo pedido
        alvo.append(evento)
    return alvo


def garantir_colunas_extras(worksheet, colunas_extras=COLUNAS_EXTRAS_SEED):
    """Adiciona no fim do cabeçalho as colunas Chave_Match_* se ainda não
    existirem -- não mexe em nenhuma coluna já existente na planilha.

    Expande a GRADE da planilha primeiro (worksheet.add_cols) se preciso
    -- o gspread não faz isso sozinho, e escrever numa coluna além do
    tamanho atual da grade (col_count) dá erro "exceeds grid limits" em
    vez de criar a coluna."""
    cabecalho = worksheet.row_values(1)
    faltando = [c for c in colunas_extras if c not in cabecalho]
    if not faltando:
        return cabecalho

    colunas_necessarias = len(cabecalho) + len(faltando)
    if colunas_necessarias > worksheet.col_count:
        worksheet.add_cols(colunas_necessarias - worksheet.col_count)

    for i, nome in enumerate(faltando):
        worksheet.update_cell(1, len(cabecalho) + 1 + i, nome)
    return cabecalho + faltando


def _compilar_tags(tags_base, tags_semelhantes=None, usar_tags_semelhantes=True, max_tags_por_item=None):
    """Combina tags_base + tags_semelhantes (só se usar_tags_semelhantes=True),
    deduplicado (case-insensitive, mantém a primeira grafia). Se
    max_tags_por_item for passado, corta a lista final nesse tamanho --
    tags_base sempre vêm primeiro no resultado (prioridade sobre as
    _semelhantes), então o corte nunca sacrifica uma tag base por causa
    de sinônimo."""
    fonte = list(tags_base or [])
    if usar_tags_semelhantes:
        fonte += list(tags_semelhantes or [])
    vistos, resultado = set(), []
    for tag in fonte:
        chave = tag.strip().lower()
        if chave and chave not in vistos:
            vistos.add(chave)
            resultado.append(tag.strip())
    if max_tags_por_item is not None:
        resultado = resultado[:max_tags_por_item]
    return resultado


def _gravar_hits_pixabay(hits, worksheet, cabecalho):
    """Escreve os hits crus do Pixabay como linhas novas na image-stock --
    só metadados da própria imagem, nenhum contexto bíblico."""
    linhas = []
    for i, hit in enumerate(hits):
        tags_pixabay = hit.get("tags", "") or ""
        valores = {
            "Thumbnail": f"Ver #{i + 1}",
            # Link ESTÁVEL, não o assinado que a API entrega em
            # largeImageURL: estes notebooks gravam DIRETO na image-stock,
            # sem triagem no meio, e a linha vai ficar lá por meses. Ver
            # pixabay_urls.url_estavel.
            "Imagem": url_estavel(hit),
            "ID": hit.get("id"),
            "Título": (tags_pixabay.split(",")[0].strip() if tags_pixabay else ""),
            "Autor": hit.get("user", "Pixabay"),
            "Tags": tags_pixabay,
            "Resolução": f"{hit.get('imageWidth', '')} × {hit.get('imageHeight', '')}",
            "Visualizações": hit.get("views", 0),
            "Downloads": hit.get("downloads", 0),
            "Likes": hit.get("likes", 0),
            "Favoritos": hit.get("favorites", 0),
            "URL Thumbnail": hit.get("previewURL", ""),
            "Largura": hit.get("imageWidth", ""),
            "Altura": hit.get("imageHeight", ""),
            "Vezes_Usada": 0,
        }
        linhas.append([valores.get(col, "") for col in cabecalho])
    if linhas:
        worksheet.append_rows(linhas, value_input_option="USER_ENTERED")
    return len(linhas)


def semear_por_tags(tags_pt, worksheet, chave_api_pixabay, cache_traducao,
                      quantidade_por_tag=3, delay_segundos=2,
                      groq_client=None, mistral_client=None, modelo_groq=None, modelo_mistral=None,
                      estado_provedor=None, usar_tags_semelhantes=True, tags_semelhantes=None,
                      max_tags_por_item=None):
    """
    Núcleo compartilhado pelas 3 passadas (evento/título/versículo):
    1. Compila tags_pt + tags_semelhantes (se usar_tags_semelhantes),
       deduplicado.
    2. Traduz em LOTE pro inglês (cache_traducao evita retraduzir o que
       já foi traduzido antes -- "sob demanda, mas guardado").
    3. Busca no Pixabay UMA VEZ POR TAG traduzida (quantidade_por_tag
       imagens cada).
    4. Escreve tudo na image-stock (só metadados da imagem).

    Retorna (cache_traducao atualizado, total_de_imagens_adicionadas).
    Cada nível (evento/título/versículo) só passa pelas SUAS PRÓPRIAS
    tags aqui -- nunca as do nível pai/filho -- então nada é buscado
    duas vezes (ver conversa sobre "problema N+1"/rollup hierárquico).
    """
    cabecalho = garantir_colunas_extras(worksheet)
    estado_provedor = estado_provedor if estado_provedor is not None else {"atual": "mistral"}

    tags_compiladas = _compilar_tags(tags_pt, tags_semelhantes, usar_tags_semelhantes, max_tags_por_item)
    if not tags_compiladas:
        return cache_traducao, 0

    if groq_client or mistral_client:
        cache_traducao, mapa_en = traduzir_tags_em_lote(
            tags_compiladas, cache_traducao, groq_client, mistral_client,
            estado_provedor, modelo_groq, modelo_mistral,
        )
    else:
        mapa_en = {t: t for t in tags_compiladas}  # sem IA -- busca em portugues mesmo

    total = 0
    for tag_pt in tags_compiladas:
        termo_en = mapa_en.get(tag_pt, tag_pt)
        try:
            hits = buscar_imagens_pixabay(termo_en, chave_api_pixabay, quantidade_por_tag, lang="en")
        except Exception as e:
            print(f"     ❌ tag {tag_pt!r} ({termo_en!r}): {e}")
            time.sleep(delay_segundos)
            continue
        n = _gravar_hits_pixabay(hits, worksheet, cabecalho)
        total += n
        print(f"     {'✅' if n else '⚠️ 0'} {tag_pt!r} → {termo_en!r}: +{n} imagem(ns)")
        time.sleep(delay_segundos)

    return cache_traducao, total


def semear_por_evento(eventos_alvo, worksheet, chave_api_pixabay, cache_traducao,
                        aba_itens_semeados=None, quantidade_por_tag=3, delay_segundos=2,
                        groq_client=None, mistral_client=None, modelo_groq=None, modelo_mistral=None,
                        usar_tags_semelhantes=True, max_tags_por_item=None, callback_pos_item=None):
    """Passada 1/3: um evento inteiro processado UMA VEZ (suas próprias
    `tags`/`tags_semelhantes`, já vindas do léxico -- ver
    dados_lexico/eventos-biblicos.json). Retorna (cache_traducao, resumo)."""
    estado_provedor = {"atual": "mistral"}
    resumo = {}
    for evento in eventos_alvo:
        evento_id = evento.get("id", "")
        print(f"  📖 Evento {evento_id} ({evento.get('titulo','')})")
        cache_traducao, total = semear_por_tags(
            evento.get("tags", []), worksheet, chave_api_pixabay, cache_traducao,
            quantidade_por_tag, delay_segundos, groq_client, mistral_client, modelo_groq, modelo_mistral,
            estado_provedor, usar_tags_semelhantes, evento.get("tags_semelhantes", []), max_tags_por_item,
        )
        resumo[evento_id] = total
        if aba_itens_semeados is not None:
            try:
                registrar_item_semeado(aba_itens_semeados, "evento", evento_id)
            except Exception as e:
                print(f"   ⚠️  Não consegui marcar {evento_id} em itens_semeados: {e}")
        if callback_pos_item:
            callback_pos_item(evento_id)
    return cache_traducao, resumo


def semear_por_titulo(titulos_alvo, worksheet, chave_api_pixabay, cache_traducao,
                        aba_itens_semeados=None, quantidade_por_tag=3, delay_segundos=2,
                        groq_client=None, mistral_client=None, modelo_groq=None, modelo_mistral=None,
                        usar_tags_semelhantes=True, max_tags_por_item=None, callback_pos_item=None):
    """Passada 2/3: cada título processado UMA VEZ (granularidade de
    versículo, mais fino que evento -- ver dados_lexico/titulos-biblicos.json).
    `titulos_alvo` é uma lista de (chave_id, entrada) -- entrada tem
    "tags"/"tags_semelhantes"."""
    estado_provedor = {"atual": "mistral"}
    resumo = {}
    for chave_id, titulo in titulos_alvo:
        print(f"  📖 Título {chave_id} ({titulo.get('titulo','')})")
        cache_traducao, total = semear_por_tags(
            titulo.get("tags", []), worksheet, chave_api_pixabay, cache_traducao,
            quantidade_por_tag, delay_segundos, groq_client, mistral_client, modelo_groq, modelo_mistral,
            estado_provedor, usar_tags_semelhantes, titulo.get("tags_semelhantes", []), max_tags_por_item,
        )
        resumo[chave_id] = total
        if aba_itens_semeados is not None:
            try:
                registrar_item_semeado(aba_itens_semeados, "titulo", chave_id)
            except Exception as e:
                print(f"   ⚠️  Não consegui marcar {chave_id} em itens_semeados: {e}")
        if callback_pos_item:
            callback_pos_item(chave_id)
    return cache_traducao, resumo


def carregar_tags_image_stock(worksheet_imagens):
    """Lê Tags_Semelhantes_PT de TODA a image-stock, devolve lista de
    sets (um por linha, já em minúsculo) -- pronto pra
    contar_candidatos_versiculo(). Só pra CONTAR quantos candidatos já
    existem (decidir se pula a busca), nunca usado pra buscar."""
    dados = worksheet_imagens.get_all_records()
    resultado = []
    for linha in dados:
        bruto = str(linha.get("Tags_Semelhantes_PT", "") or "")
        tags = {t.strip().lower() for t in bruto.split(",") if t.strip()}
        if tags:
            resultado.append(tags)
    return resultado


def contar_candidatos_versiculo(tags_semelhantes_versiculo, tags_image_stock):
    """Conta quantas linhas da image-stock têm PELO MENOS 1 tag em comum
    com o versículo -- mesma lógica de match do painel (Code.gs), em
    Python. Usado só pra DECIDIR se vale a pena buscar mais pra esse
    versículo, nunca pra buscar em si."""
    tags_verso = {t.strip().lower() for t in tags_semelhantes_versiculo}
    if not tags_verso:
        return 0
    return sum(1 for tags_imagem in tags_image_stock if tags_verso & tags_imagem)


def semear_por_versiculo(versiculos_alvo, worksheet, chave_api_pixabay, cache_traducao,
                           aba_itens_semeados=None, quantidade_por_tag=1, delay_segundos=2,
                           groq_client=None, mistral_client=None, modelo_groq=None, modelo_mistral=None,
                           usar_tags_semelhantes=True, max_tags_por_item=None, callback_pos_item=None,
                           tipo_fonte="imagem", biblioteca_match=None, tags_image_stock=None,
                           min_candidatos_para_pular=5, versiculos_forcar_pular=None):
    """
    Passada 3/3 -- SEM repetição possível (cada versículo já é único).

    IMPORTANTE -- busca SEARCH-SAFE: usa só tags_pt + tags_sugeridas (as
    PRÓPRIAS do versículo), expandidas por sinônimo NA HORA -- NUNCA usa
    a tags_semelhantes já salva na versiculo_tags pra buscar, porque essa
    coluna agora é o estoque RICO (inclui tags do evento/título também,
    ver match_pipeline.registrar_tags_versiculo). Se a busca usasse ela,
    reintroduziria o "problema N+1": cada versículo re-buscaria a mesma
    tag de evento/título que evento/título já buscaram sozinhos lá em
    cima. tags_semelhantes só é lida aqui pra CONTAGEM (ver abaixo).

    Pula automaticamente (sem gastar Pixabay/IA) versículos que:
    - estão em `versiculos_forcar_pular` (lista de item_id -- pra você
      pular manualmente por qualquer motivo, além dos automáticos), OU
    - já têm vencedor escolhido em `biblioteca_match` (se passado --
      ver match_pipeline.carregar_biblioteca_match), OU
    - já têm >= `min_candidatos_para_pular` candidatos na image-stock
      (contando por tag em comum contra `tags_image_stock`, se passado
      -- ver carregar_tags_image_stock())

    `versiculos_alvo`: lista de dicts {item_id, livro_pt, capitulo,
    versiculo, tags_pt, tags_sugeridas, tags_semelhantes} -- vem da
    versiculo_tags (tags_semelhantes só é usada pra contagem, não busca).
    """
    estado_provedor = {"atual": "mistral"}
    resumo = {}
    forcar_pular = set(versiculos_forcar_pular or [])

    for v in versiculos_alvo:
        item_id = v["item_id"]

        if item_id in forcar_pular:
            print(f"  ⏭️  Versículo {item_id}: pulado manualmente")
            if callback_pos_item:
                callback_pos_item(item_id)
            continue

        if biblioteca_match is not None:
            chave_vencedor = (str(v.get("livro_pt", "")), str(v.get("capitulo", "")),
                               str(v.get("versiculo", "")), tipo_fonte)
            if chave_vencedor in biblioteca_match:
                print(f"  ⏭️  Versículo {item_id}: já tem vencedor escolhido")
                if callback_pos_item:
                    callback_pos_item(item_id)
                continue

        if tags_image_stock is not None:
            n_candidatos = contar_candidatos_versiculo(v.get("tags_semelhantes", []), tags_image_stock)
            if n_candidatos >= min_candidatos_para_pular:
                print(f"  ⏭️  Versículo {item_id}: já tem {n_candidatos} candidato(s) (limite: {min_candidatos_para_pular})")
                if callback_pos_item:
                    callback_pos_item(item_id)
                continue

        print(f"  📖 Versículo {item_id}")
        tags_proprias = list(v.get("tags_pt", [])) + list(v.get("tags_sugeridas", []))
        tags_busca = expandir_tags_semelhantes(tags_proprias) if usar_tags_semelhantes else tags_proprias
        cache_traducao, total = semear_por_tags(
            tags_busca, worksheet, chave_api_pixabay, cache_traducao,
            quantidade_por_tag, delay_segundos, groq_client, mistral_client, modelo_groq, modelo_mistral,
            estado_provedor, usar_tags_semelhantes=False, tags_semelhantes=None, max_tags_por_item=max_tags_por_item,
        )
        resumo[item_id] = total
        if aba_itens_semeados is not None:
            try:
                registrar_item_semeado(aba_itens_semeados, "versiculo", item_id)
            except Exception as e:
                print(f"   ⚠️  Não consegui marcar {item_id} em itens_semeados: {e}")
        if callback_pos_item:
            callback_pos_item(item_id)

    return cache_traducao, resumo


# ── alocar_biblioteca_a_partir_da_planilha() foi removida ──────────────────
# A escolha de vencedor agora é por VERSÍCULO (não mais 1 por evento
# escolhido automaticamente) -- feita manualmente no painel de revisão
# (Apps Script, bound à planilha biblioteca_match), que grava direto na
# biblioteca via match_pipeline.registrar_na_biblioteca_match(). Ver
# Code.gs / PainelRevisao.html.
