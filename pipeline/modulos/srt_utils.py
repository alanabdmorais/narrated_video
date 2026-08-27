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

import logging
import re
from pathlib import Path

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


# ── Extração de texto contínuo (para redistribuição via IA) ────────────────────

def texto_corrido(legendas: list[Legenda]) -> str:
    """Junta todos os textos em uma única string separada por espaço."""
    return " ".join(leg.texto for leg in legendas)


def extrair_texto_unico(legendas: list[Legenda]) -> str:
    """
    Remove frases duplicadas (artefato comum das legendas automáticas do
    YouTube, que mostram texto cumulativo/rolante — cada bloco repete
    parte do anterior). Detecta o padrão "frase frase" e mantém só uma
    ocorrência. Retorna o texto corrido sem duplicatas.
    """
    frases_unicas: list[str] = []
    visto: set[str] = set()

    for leg in legendas:
        if leg.duracao_ms < 50:  # artefato (legenda quase instantânea)
            continue
        frase = _extrair_prefixo(leg.texto)
        if frase and frase not in visto:
            frases_unicas.append(frase)
            visto.add(frase)

    return " ".join(frases_unicas)


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
