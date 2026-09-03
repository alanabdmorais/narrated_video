# -*- coding: utf-8 -*-
"""
srt_utils.py — Utilitários para arquivos SRT (projeto Narrated Video).

Módulo enxuto, portado de oracao_v1/srt_utils.py — traz só o que os
notebooks de legenda (Single Subtitle, Language Subtitles) precisam por
enquanto: ler e salvar SRT. Funções de sincronização/redistribuição entre
idiomas serão portadas quando o notebook de Language Subtitles for criado.

Funções:
    ler_srt(caminho)              → list[Legenda]
    salvar_srt(legendas, caminho)
"""
from __future__ import annotations

import difflib
import logging
import re
from pathlib import Path
from typing import Optional

from models import Legenda, str_para_ms

logger = logging.getLogger(__name__)


# ── Leitura ───────────────────────────────────────────────────────────────────

def ler_srt(caminho: Path | str) -> list[Legenda]:
    """
    Lê um arquivo SRT e retorna lista de Legenda.

    Suporta:
    - encoding utf-8 e utf-8-sig (com BOM)
    - timestamps com vírgula (00:00:01,000) e ponto (00:00:01.000)
    - múltiplas linhas de texto por bloco
    - artefatos do YouTube entre colchetes [Music], [Applause]
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"SRT não encontrado: {caminho}")

    conteudo = caminho.read_text(encoding="utf-8-sig")
    blocos   = re.split(r"\n\s*\n", conteudo.strip())
    legendas: list[Legenda] = []

    for bloco in blocos:
        linhas = [l.strip() for l in bloco.strip().splitlines() if l.strip()]
        ts_linha = next((l for l in linhas if "-->" in l), None)
        if not ts_linha:
            continue
        partes = ts_linha.split("-->")
        if len(partes) != 2:
            continue
        inicio_ms = str_para_ms(partes[0].strip())
        fim_ms    = str_para_ms(partes[1].strip())

        textos = [
            l for l in linhas
            if "-->" not in l and not l.isdigit() and l != " "
        ]
        texto = " ".join(textos).strip()
        texto = re.sub(r"\[.*?\]", "", texto).strip()

        if not texto:
            continue

        legendas.append(Legenda(
            id        = len(legendas) + 1,
            inicio_ms = inicio_ms,
            fim_ms    = fim_ms,
            texto     = texto,
        ))

    logger.debug("ler_srt('%s'): %d legendas", caminho.name, len(legendas))
    return legendas


# ── Escrita ───────────────────────────────────────────────────────────────────

def salvar_srt(legendas: list[Legenda], caminho: Path | str) -> None:
    """Salva lista de Legenda como arquivo SRT (utf-8 sem BOM)."""
    caminho = Path(caminho)
    linhas: list[str] = []
    for i, leg in enumerate(legendas, 1):
        linhas.append(str(i))
        linhas.append(f"{leg.inicio_str} --> {leg.fim_str}")
        linhas.append(leg.texto)
        linhas.append("")
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    logger.debug("salvar_srt('%s'): %d legendas", caminho.name, len(legendas))


# ── Ajuste de contagem (redistribuição via IA) ─────────────────────────────────

def ajustar_para_n_partes(partes: list[str], n: int) -> tuple[list[str], bool]:
    """
    Força a lista `partes` a ter exatamente `n` elementos, sem descartar
    texto. Nunca falha — sempre retorna (lista_com_n_itens, houve_ajuste).

    A IA (redistribuição multi-idioma, correção, etc.) nem sempre acerta o
    número exato de segmentos pedido. Em vez de descartar o resultado
    quando isso acontece, ajustamos automaticamente:
      - Partes a mais: funde o excedente na última posição.
      - Partes a menos: quebra as partes mais longas (por vírgula ou por
        espaço) até completar `n`. Se não der mais pra quebrar, preenche o
        restante com um marcador de revisão manual (nunca fica vazio).
    """
    partes = [p.strip() for p in partes if p is not None]
    if len(partes) == n:
        return partes, False

    partes = list(partes)

    if len(partes) > n:
        cabeca = partes[:n - 1]
        resto = " ".join(partes[n - 1:])
        return cabeca + [resto], True

    while len(partes) < n:
        candidatos = [(i, p) for i, p in enumerate(partes) if len(p.split()) > 1]
        if not candidatos:
            break
        idx, texto = max(candidatos, key=lambda t: len(t[1]))
        if ',' in texto:
            corte = texto.index(',') + 1
            esquerda, direita = texto[:corte].strip(), texto[corte:].strip()
        else:
            palavras = texto.split()
            meio = len(palavras) // 2
            esquerda = " ".join(palavras[:meio])
            direita = " ".join(palavras[meio:])
        partes = partes[:idx] + [esquerda, direita] + partes[idx + 1:]

    while len(partes) < n:
        partes.append("[revisar manualmente]")

    return partes, True


def _palavras_simples(texto: str) -> list[str]:
    """Palavras comparáveis, sem pontuação e sem caixa. Serve pra qualquer
    idioma do projeto -- \\w cobre acento, hangul e ideograma."""
    return re.findall(r"\w+", texto.lower())


def repartir_como(texto_corrido: str, textos_referencia: list[str]) -> list[str]:
    """Reparte `texto_corrido` em len(textos_referencia) partes, cortando nos
    MESMOS pontos proporcionais em que a referência corta o texto dela.

    Substitui a redistribuição por IA. O motivo é medido: no Mateus 2, o desvio
    de cada idioma em relação ao mestre (proporção do capítulo já exibida em
    cada bloco) caiu de 1,5-2,1% para 0,1% nos quatro idiomas. Na tela isso era
    a diferença entre o espanhol mostrar o versículo anterior enquanto o inglês
    já estava no seguinte.

    Além de alinhar melhor, é determinística: não chama IA, não custa, roda
    sempre igual, e elimina de vez o laço, o bloco vazio e a palavra sumida --
    a saída contém as mesmas palavras da entrada por construção.

    O corte desliza até a fronteira de palavra mais próxima do alvo, e entre as
    quatro candidatas mais próximas prefere uma que venha logo depois de
    pontuação: cortar em vírgula lê melhor que cortar no meio de uma oração,
    e a perda de precisão é pequena.
    """
    n = len(textos_referencia)
    palavras = texto_corrido.split()
    if n <= 0:
        return []
    if len(palavras) < n:
        # Texto curto demais pra n blocos. Não é pra acontecer num capítulo,
        # mas se acontecer é melhor devolver partes vazias no fim do que
        # estourar: o conferir_redistribuicao() acusa logo em seguida.
        return palavras + [""] * (n - len(palavras))

    def uteis(s: str) -> int:
        return sum(1 for c in s if c.isalnum())

    # Onde a referência corta, em proporção do texto dela
    tam_ref = [uteis(t) for t in textos_referencia]
    total_ref = sum(tam_ref) or 1
    alvos, soma = [], 0
    for t in tam_ref[:-1]:
        soma += t
        alvos.append(soma / total_ref)

    # Proporção acumulada em cada fronteira de palavra do texto a repartir
    pesos = [uteis(p) for p in palavras]
    total = sum(pesos) or 1
    acumulado, soma = [], 0
    for w in pesos:
        soma += w
        acumulado.append(soma / total)

    FIM_DE_ORACAO = ",.;:!?»”\"'"
    cortes: list[int] = []
    usados: set[int] = set()
    for alvo in alvos:
        ordem = sorted(range(1, len(palavras)), key=lambda i: abs(acumulado[i - 1] - alvo))
        escolha = None
        for i in ordem[:4]:
            if i not in usados and palavras[i - 1][-1:] in FIM_DE_ORACAO:
                escolha = i
                break
        if escolha is None:
            for i in ordem:
                if i not in usados:
                    escolha = i
                    break
        usados.add(escolha)
        cortes.append(escolha)

    partes, inicio = [], 0
    for corte in sorted(cortes) + [len(palavras)]:
        partes.append(" ".join(palavras[inicio:corte]))
        inicio = corte
    return partes


def conferir_redistribuicao(partes: list[str], texto_fonte: str) -> list[str]:
    """Confere o resultado da redistribuição por IA. Devolve uma lista de
    problemas legíveis (vazia = nada achado).

    A checagem principal é EXATA, não heurística, porque o contrato é exato: o
    prompt manda "não repita nem omita nenhuma palavra do texto original" -- a
    IA só reparte. Então a concatenação das partes tem que ter as mesmas
    palavras da fonte, na mesma ordem. Isso pega de uma vez palavra sumida,
    palavra inventada, bloco vazio e o laço em que a IA reescreve um trecho.

    A primeira versão disto era um detector de repetição por prefixo, e ele
    falhou nos dois sentidos ao mesmo tempo: acusou três blocos legítimos e
    deixou passar três blocos vazios. O motivo é que Mateus 2 tem versículos
    paralelos -- "levantou-se, tomou o menino e sua mãe" abre o v14 e o v21, e
    a fala do anjo se repete no v13 e no v20. Depois da redistribuição esses
    trechos caem em blocos que COMEÇAM igual, de propósito. Nenhum limiar de
    prefixo separa isso de um laço da IA, porque não há o que separar: a
    repetição é real e correta.
    """
    problemas: list[str] = []

    # ── A fonte foi preservada? ─────────────────────────────────────────────
    a = _palavras_simples(texto_fonte)
    b = _palavras_simples(" ".join(partes))
    if a:
        sm = difflib.SequenceMatcher(None, a, b)
        sumiram, surgiram = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("delete", "replace"):
                sumiram.extend(a[i1:i2])
            if tag in ("insert", "replace"):
                surgiram.extend(b[j1:j2])
        if sumiram:
            problemas.append(f"{len(sumiram)} palavra(s) da fonte sumiram: "
                             + ", ".join(sumiram[:8]) + ("; ..." if len(sumiram) > 8 else ""))
        if surgiram:
            problemas.append(f"{len(surgiram)} palavra(s) apareceram do nada: "
                             + ", ".join(surgiram[:8]) + ("; ..." if len(surgiram) > 8 else ""))

    # ── Bloco vazio ─────────────────────────────────────────────────────────
    # Sai da conferência acima também (as palavras foram parar noutro bloco ou
    # sumiram), mas vale nomear: bloco vazio some da tela sem deixar rastro.
    vazios = [str(i) for i, x in enumerate(partes, 1) if not x.strip()]
    if vazios:
        problemas.append(f"{len(vazios)} bloco(s) sem texto nenhum: " + ", ".join(vazios[:10]))

    # ── Bloco inchado ───────────────────────────────────────────────────────
    # Defeito diferente: não perde texto, mas joga um parágrafo inteiro num
    # bloco só -- ilegível na tela. É o que o ajustar_para_n_partes faz quando
    # a IA devolve partes demais (funde o excedente na última posição).
    tamanhos = [len(x.split()) for x in partes]
    if tamanhos:
        mediana = sorted(tamanhos)[len(tamanhos) // 2]
        limite = max(3 * mediana, 25)   # o piso evita alarme com mediana minúscula
        inchados = [f"{i} ({t} palavras)" for i, t in enumerate(tamanhos, 1) if t > limite]
        if inchados:
            problemas.append(
                f"{len(inchados)} bloco(s) muito maior(es) que a mediana de "
                f"{mediana} palavras: " + "; ".join(inchados[:6])
                + ("; ..." if len(inchados) > 6 else ""))

    # ── Marcador de preenchimento ───────────────────────────────────────────
    marcados = [str(i) for i, x in enumerate(partes, 1) if "[revisar manualmente]" in x]
    if marcados:
        problemas.append(f"{len(marcados)} bloco(s) preenchidos com marcador de "
                         f"revisão (a IA devolveu texto de menos): " + ", ".join(marcados[:10]))

    return problemas


# ── Extração de texto contínuo (para redistribuição via IA) ────────────────────

def texto_corrido(legendas: list[Legenda]) -> str:
    """Junta todos os textos em uma única string separada por espaço."""
    return " ".join(leg.texto for leg in legendas)


def fatiar_em_slots(legendas: list[Legenda]) -> list[tuple[tuple[int, int], str]]:
    """
    Mesma limpeza do extrair_texto_unico, só que SEM jogar fora de qual bloco
    veio cada frase: devolve [((inicio_ms, fim_ms), frase), ...] na ordem do
    arquivo, com frase vazia onde o bloco foi descartado.

    Existe porque as faixas de legenda do YouTube de um mesmo vídeo compartilham
    a MESMA grade de tempos entre idiomas (a tradução automática é feita bloco a
    bloco). Esse par tempo↔texto é uma âncora exata entre idiomas -- e o
    extrair_texto_unico, que colapsa tudo num texto corrido, a descartava.

    Invariante: " ".join(frases não vazias) == extrair_texto_unico(legendas).
    """
    slots: list[tuple[tuple[int, int], str]] = []
    visto: set[str] = set()

    for leg in legendas:
        tempo = (leg.inicio_ms, leg.fim_ms)
        if leg.duracao_ms < 50:  # artefato (legenda quase instantânea)
            slots.append((tempo, ""))
            continue
        frase = _extrair_prefixo(leg.texto)
        if frase and frase not in visto:
            visto.add(frase)
            slots.append((tempo, frase))
        else:
            slots.append((tempo, ""))

    return slots


def extrair_texto_unico(legendas: list[Legenda]) -> str:
    """
    Remove frases duplicadas (artefato comum das legendas automáticas do
    YouTube, que mostram texto cumulativo/rolante — cada bloco repete
    parte do anterior). Detecta o padrão "frase frase" e mantém só uma
    ocorrência. Retorna o texto corrido sem duplicatas.
    """
    return " ".join(frase for _, frase in fatiar_em_slots(legendas) if frase)


def _extrair_prefixo(texto: str) -> str:
    """
    Detecta o padrão "A A" onde A é a primeira metade do texto.
    Retorna A se encontrar repetição, senão retorna o texto original.
    """
    tokens = texto.split()
    n = len(tokens)
    for i in range(1, n // 2 + 1):
        prefixo = " ".join(tokens[:i])
        seguinte = " ".join(tokens[i: i * 2])
        if prefixo == seguinte:
            return prefixo
    return texto


# ── Repartição ancorada na grade do YouTube ───────────────────────────────────

# Quanto do texto do idioma-alvo precisa cair em slots que existem na grade
# para a âncora valer. Medido no Mateus 2: pt/es/fr/ko deram 100%. Legenda
# enviada à parte pelo autor do vídeo (em vez de traduzida automaticamente)
# teria grade própria e daria perto de 0 -- é esse caso que o limiar pega.
_MINIMO_SLOTS_NA_GRADE = 0.80
# Quanto das palavras do mestre o difflib precisa casar contra a legenda do
# YouTube no MESMO idioma. Medido no Mateus 2: 96,6%. Uma tradução diferente
# derrubaria isso.
_MINIMO_CASAMENTO_MESTRE = 0.70


def _coordenadas_na_grade(
    slots: list[tuple[tuple[int, int], str]],
    indice_por_tempo: dict[tuple[int, int], int],
) -> tuple[list[str], list[float], int, int]:
    """Espalha as palavras de cada slot dentro do índice desse slot na grade:
    a k-ésima de n palavras do slot i fica na coordenada i + k/n.

    Devolve (palavras, coordenadas, slots_aproveitados, slots_fora_da_grade).
    """
    palavras: list[str] = []
    coordenadas: list[float] = []
    dentro = fora = 0

    for tempo, texto in slots:
        if not texto.strip():
            continue
        i = indice_por_tempo.get(tempo)
        if i is None:
            fora += 1
            continue
        dentro += 1
        ws = texto.split()
        for k, w in enumerate(ws):
            palavras.append(w)
            coordenadas.append(i + k / len(ws))

    return palavras, coordenadas, dentro, fora


def repartir_pela_grade(
    legendas_alvo: list[Legenda],
    legendas_grade: list[Legenda],
    textos_referencia: list[str],
) -> tuple[list[str], str]:
    """Reparte o texto do idioma-alvo nos blocos da legenda mestre usando como
    âncora a GRADE de tempos das legendas do YouTube.

    Devolve (partes, motivo) -- `partes` vazio quando a âncora não vale, e
    `motivo` sempre explica o que aconteceu, pra quem chama poder avisar e cair
    no repartir_como.

        legendas_alvo       legenda crua do YouTube no idioma-alvo   (yt_pt)
        legendas_grade      legenda crua do YouTube no idioma MESTRE (yt_en)
        textos_referencia   texto de cada bloco da legenda mestre

    Por que isso funciona: as faixas de legenda de um mesmo vídeo do YouTube
    são traduzidas bloco a bloco, então todas compartilham a mesma grade de
    tempos. Cada slot dessa grade é uma âncora exata entre idiomas -- no
    Mateus 2 são 102 âncoras, contra as 23 fronteiras de versículo que eu ia
    usar e contra nenhuma da repartição proporcional pura.

    A ponte até a mestre é feita por texto, não por tempo: a legenda do YouTube
    e a mestre são do mesmo vídeo mas de linhas do tempo diferentes (a do
    YouTube tem a abertura do vídeo na frente). Como as duas estão no idioma
    mestre, o difflib casa palavra a palavra.

    Medido no Mateus 2 (nome próprio caindo no mesmo bloco do mestre, medida
    independente de proporção): a repartição proporcional acerta 90/158 = 57%,
    esta aqui acerta 152/158 = 96% -- pt, es e fr em 100%, coreano em 85%.
    """
    n = len(textos_referencia)
    if n == 0:
        return [], "a legenda mestre está vazia"

    slots_grade = fatiar_em_slots(legendas_grade)
    indice_por_tempo = {tempo: i for i, (tempo, _) in enumerate(slots_grade)}

    pal_grade, coord_grade, _, _ = _coordenadas_na_grade(slots_grade, indice_por_tempo)
    if not pal_grade:
        return [], "a legenda do YouTube no idioma mestre veio vazia"

    # ── ponte mestre ↔ grade, por texto ──────────────────────────────────────
    pal_mestre: list[str] = []
    primeira_palavra: dict[int, int] = {}
    for b, texto in enumerate(textos_referencia):
        for w in texto.split():
            primeira_palavra.setdefault(b, len(pal_mestre))
            pal_mestre.append(w)
    if not pal_mestre:
        return [], "a legenda mestre não tem palavras"

    sm = difflib.SequenceMatcher(
        None, [_normalizar_palavra(w) for w in pal_mestre],
        [_normalizar_palavra(w) for w in pal_grade], autojunk=False)

    casadas = sum(bl.size for bl in sm.get_matching_blocks())
    proporcao = casadas / len(pal_mestre)
    if proporcao < _MINIMO_CASAMENTO_MESTRE:
        return [], (f"a legenda mestre e a do YouTube no idioma mestre só casam "
                    f"{proporcao:.0%} das palavras (mínimo {_MINIMO_CASAMENTO_MESTRE:.0%}) "
                    f"— são edições diferentes?")

    mapa: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                mapa[i1 + k] = j1 + k
        elif tag == "replace":
            n_a, n_b = i2 - i1, j2 - j1
            for k in range(n_a):
                mapa[i1 + k] = min(j1 + int(k * n_b / max(n_a, 1)), j2 - 1)

    # ── fronteira de cada bloco do mestre, em coordenada de grade ────────────
    fronteiras: list[float] = []
    for b in range(n):
        i = primeira_palavra.get(b)          # None = bloco vazio na mestre
        j = mapa.get(i) if i is not None else None
        if j is None and i is not None:
            for d in range(1, 15):     # bloco cuja 1ª palavra o difflib não casou
                if i - d in mapa:
                    j = mapa[i - d] + d
                    break
                if i + d in mapa:
                    j = mapa[i + d] - d
                    break
        j = max(0, min(j if j is not None else 0, len(coord_grade) - 1))
        fronteiras.append(coord_grade[j])
    # bloco vazio no mestre pode gerar fronteira fora de ordem; monotoniza
    for b in range(1, n):
        fronteiras[b] = max(fronteiras[b], fronteiras[b - 1])
    fronteiras[0] = float("-inf")
    fronteiras.append(float("inf"))

    # ── palavras do alvo, na coordenada da grade ─────────────────────────────
    slots_alvo = fatiar_em_slots(legendas_alvo)
    pal_alvo, coord_alvo, dentro, fora = _coordenadas_na_grade(slots_alvo, indice_por_tempo)
    if dentro + fora == 0:
        return [], "a legenda do YouTube no idioma-alvo veio vazia"
    aproveitados = dentro / (dentro + fora)
    if aproveitados < _MINIMO_SLOTS_NA_GRADE:
        return [], (f"só {aproveitados:.0%} dos blocos do idioma-alvo estão na grade do "
                    f"idioma mestre (mínimo {_MINIMO_SLOTS_NA_GRADE:.0%}) — a legenda "
                    f"deste idioma não é tradução automática da mestre")

    partes: list[list[str]] = [[] for _ in range(n)]
    b = 0
    for w, c in zip(pal_alvo, coord_alvo):
        while b + 1 < n and c >= fronteiras[b + 1]:
            b += 1
        partes[b].append(w)

    return [" ".join(p) for p in partes], (
        f"{dentro} blocos ancorados na grade ({aproveitados:.0%}), "
        f"ponte com a mestre em {proporcao:.0%} das palavras")


def _normalizar_palavra(p: str) -> str:
    """Só o miolo alfanumérico, sem caixa — pra comparar palavra de edições
    diferentes do mesmo texto."""
    return re.sub(r"[^\w]", "", p, flags=re.UNICODE).lower()


# ── Alinhamento de versículos (indicador livro:versículo) ──────────────────────

def extrair_marcadores_versiculo(texto_com_versiculos: str) -> tuple[list[str], dict[int, int]]:
    """
    Recebe um texto onde os números de versículo aparecem como tokens
    isolados no meio do fluxo (ex: "1 Now when Jesus ... 2 Where is he...").
    Retorna (palavras_sem_marcadores, {numero_versiculo: indice_da_palavra_onde_comeca}).
    """
    texto_com_versiculos = texto_com_versiculos.replace("\n", " ")
    tokens = texto_com_versiculos.split()

    inicio_versiculo: dict[int, int] = {}
    palavras: list[str] = []
    indice = 0

    for tok in tokens:
        if re.fullmatch(r"\d{1,3}", tok):
            v = int(tok)
            if v not in inicio_versiculo:
                inicio_versiculo[v] = indice
        else:
            palavras.append(tok)
            indice += 1

    return palavras, inicio_versiculo


def texto_por_versiculo(texto_com_versiculos: str) -> dict[int, str]:
    """
    Reaproveita extrair_marcadores_versiculo() e devolve o TEXTO de cada
    versículo (não o tempo) — {numero_versiculo: "texto do versículo"}.
    Usado pro sistema de match cena↔roteiro, que precisa do conteúdo de
    cada versículo pra sugerir palavras-chave/tags, não do tempo.
    """
    palavras, inicio_versiculo = extrair_marcadores_versiculo(texto_com_versiculos)
    versos_ordenados = sorted(inicio_versiculo.keys())

    resultado: dict[int, str] = {}
    for i, v in enumerate(versos_ordenados):
        inicio = inicio_versiculo[v]
        fim = inicio_versiculo[versos_ordenados[i + 1]] if i + 1 < len(versos_ordenados) else len(palavras)
        resultado[v] = " ".join(palavras[inicio:fim])
    return resultado


def alinhar_versiculos(
    texto_com_versiculos: str,
    legendas_mestre: list[Legenda],
) -> dict[int, int]:
    """
    Alinha um texto com marcadores de versículo (ver extrair_marcadores_versiculo)
    contra as legendas da mestre (por palavra, com tempo interpolado
    linearmente dentro de cada bloco) e retorna {numero_versiculo: tempo_ms_inicio}.

    Usa alinhamento por sequência (difflib) em vez de assumir correspondência
    exata palavra-a-palavra — tolera pequenas diferenças de pontuação/grafia
    entre o texto de referência e a mestre.
    """
    import difflib

    # constrói lista de (palavra, tempo_ms_interpolado) a partir da mestre
    palavras_mestre: list[tuple[str, int]] = []
    for leg in legendas_mestre:
        palavras_bloco = leg.texto.split()
        n = len(palavras_bloco)
        if n == 0:
            continue
        duracao = leg.fim_ms - leg.inicio_ms
        for i, p in enumerate(palavras_bloco):
            ms = leg.inicio_ms + (i / n) * duracao
            palavras_mestre.append((p, round(ms)))

    palavras_ref, inicio_versiculo = extrair_marcadores_versiculo(texto_com_versiculos)

    def normalizar(p: str) -> str:
        return re.sub(r"[^\w]", "", p).lower()

    seq_ref = [normalizar(p) for p in palavras_ref]
    seq_mestre = [normalizar(p) for p, _ in palavras_mestre]

    sm = difflib.SequenceMatcher(None, seq_ref, seq_mestre, autojunk=False)
    mapa: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                mapa[i1 + k] = j1 + k
        elif tag == "replace":
            n_ref, n_mestre = i2 - i1, j2 - j1
            for k in range(n_ref):
                j = j1 + int(k * n_mestre / max(n_ref, 1))
                mapa[i1 + k] = min(j, j2 - 1) if n_mestre > 0 else j1

    resultado: dict[int, int] = {}
    for v, idx_ref in inicio_versiculo.items():
        idx_mestre = mapa.get(idx_ref)
        if idx_mestre is None:
            # tenta o vizinho mais próximo já mapeado
            for delta in range(1, 10):
                if idx_ref - delta in mapa:
                    idx_mestre = mapa[idx_ref - delta] + delta
                    break
                if idx_ref + delta in mapa:
                    idx_mestre = mapa[idx_ref + delta] - delta
                    break
        idx_mestre = max(0, min(idx_mestre or 0, len(palavras_mestre) - 1))
        resultado[v] = palavras_mestre[idx_mestre][1]

    return resultado


def gerar_legendas_versiculo(
    tempos_versiculo: dict[int, int],
    capitulo: int,
    abreviacoes: list[str],
    fim_video_ms: int,
) -> list[Legenda]:
    """
    Constrói a lista de Legenda do indicador de versículo — um bloco por
    versículo, com o texto combinado "Abrev1/Abrev2/... capitulo:versiculo"
    (abreviações duplicadas são removidas, mantendo a primeira ocorrência).
    """
    vistos: list[str] = []
    for a in abreviacoes:
        if a not in vistos:
            vistos.append(a)
    label_livro = "/".join(vistos)

    versos_ordenados = sorted(tempos_versiculo.keys())
    legendas: list[Legenda] = []
    for i, v in enumerate(versos_ordenados):
        inicio = tempos_versiculo[v]
        fim = tempos_versiculo[versos_ordenados[i + 1]] if i + 1 < len(versos_ordenados) else fim_video_ms
        legendas.append(Legenda(
            id=i + 1,
            inicio_ms=inicio,
            fim_ms=fim,
            texto=f"{label_livro} {capitulo}:{v}",
        ))
    return legendas


# ── Qual arquivo é a legenda mestre ───────────────────────────────────────────

def escolher_legenda_mestre(
    nome_oficial: str,
    legados: tuple[str, ...],
    existe,
) -> tuple[str, Optional[str]]:
    """Resolve QUAL arquivo é a legenda mestre, devolvendo (nome, aviso).

    `existe` é uma função nome -> bool: quem chama é que sabe olhar o Drive.
    Fica assim pra esta decisão ser testável sem Drive nenhum -- ela é o
    contrato de todo o nível 2, e contrato que só dá pra conferir rodando o
    pipeline inteiro ninguém confere.

    A ordem é: o nome oficial (`<nome>_mestre.srt`) primeiro; se não existir,
    os lugares onde a mestre morava antes de ter nome próprio, e aí SEMPRE com
    aviso. Um arquivo virar mestre em silêncio é o defeito que este nome
    próprio existe pra impedir.
    """
    if existe(nome_oficial):
        return nome_oficial, None

    for nome in legados:
        if nome != nome_oficial and existe(nome):
            return nome, (
                f"'{nome_oficial}' não está no Drive, então a mestre desta vez é "
                f"'{nome}' (era ali que ela morava antes de ter nome próprio). "
                f"Rode a célula 'PROMOVER A MESTRE' do caption-single-revisar.ipynb "
                f"pra fixar isso — enquanto não rodar, qual arquivo manda depende "
                f"de quais existem na pasta.")

    return nome_oficial, (
        f"não achei nem '{nome_oficial}' nem nenhum dos antigos "
        f"({', '.join(legados)}) no Drive.")


def legendas_de_creditos(
    autores: list[str],
    duracoes_seg: list[float],
    prefixo: str = "Imagem: ",
) -> list[Legenda]:
    """SRT do crédito da imagem — um bloco por clipe, no tempo dele.

    Existe por causa da versão em MINIATURA. Na versão de tela cheia o crédito
    já vem queimado dentro do próprio clipe, em corpo 16; encolhido pra dentro
    de uma miniatura de 37% ele vira uma marca de 6px que ninguém lê. Aqui o
    crédito sai do clipe e vira uma camada do QUADRO, em tamanho normal, no
    canto inferior esquerdo -- onde a miniatura não chega.

    Clipes seguidos do MESMO autor viram um bloco só: a mesma linha piscando
    a cada troca de clipe chama mais atenção que o crédito merece.

    Clipe sem autor não vira bloco vazio -- vira ausência de crédito naquele
    trecho, que é a verdade.
    """
    if len(autores) != len(duracoes_seg):
        raise ValueError(f"{len(autores)} autor(es) para {len(duracoes_seg)} "
                         f"duração(ões) — a lista tem que ser a mesma")

    legendas: list[Legenda] = []
    inicio_ms = 0
    for autor, duracao in zip(autores, duracoes_seg):
        fim_ms = inicio_ms + int(round(duracao * 1000))
        nome = (autor or "").strip()
        if nome:
            if legendas and legendas[-1].texto == f"{prefixo}{nome}" \
                    and legendas[-1].fim_ms == inicio_ms:
                legendas[-1].fim_ms = fim_ms          # mesmo autor, segue o bloco
            else:
                legendas.append(Legenda(id=len(legendas) + 1, inicio_ms=inicio_ms,
                                        fim_ms=fim_ms, texto=f"{prefixo}{nome}"))
        inicio_ms = fim_ms
    for n, leg in enumerate(legendas, start=1):
        leg.id = n
    return legendas


def gerar_legendas_titulo(
    faixas: list[tuple[int, int, str]],
    tempos_versiculo: dict[int, int],
    fim_video_ms: int,
) -> list[Legenda]:
    """SRT do título do trecho — um bloco por FAIXA de versículos.

        faixas: [(versiculo_ini, versiculo_fim, texto), ...]

    Irmã de gerar_legendas_versiculo(), com uma diferença que importa: o
    indicador de versículo muda a cada versículo e cobre o capítulo inteiro;
    o título muda a cada TRECHO (Mateus 2 tem quatro) e pode ter buraco --
    versículo que não está em faixa nenhuma fica sem título na tela, em vez
    de herdar o do trecho anterior.

    Faixa cujo primeiro versículo não tem tempo é PULADA, não chutada: sem o
    tempo, o título entraria na hora errada e ficaria contando outra história
    junto com a narração.
    """
    legendas: list[Legenda] = []
    for v_ini, v_fim, texto in sorted(faixas):
        if not texto.strip() or v_ini not in tempos_versiculo:
            continue
        inicio = tempos_versiculo[v_ini]
        # o fim é onde o versículo SEGUINTE ao último da faixa começa
        seguintes = [v for v in sorted(tempos_versiculo) if v > v_fim]
        fim = tempos_versiculo[seguintes[0]] if seguintes else fim_video_ms
        if fim <= inicio:
            continue
        legendas.append(Legenda(id=len(legendas) + 1, inicio_ms=inicio,
                                fim_ms=fim, texto=texto.strip()))
    return legendas
