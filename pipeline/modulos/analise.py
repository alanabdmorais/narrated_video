# -*- coding: utf-8 -*-
"""
analise.py — A análise BRUTA do Stanza e do Kiwi: guardar, ler e reconstruir
as peças a partir dela.

Por que guardar o bruto: até aqui o `doc = nlp(texto)` do Stanza e o
`kiwi.analyze(...)` viviam só dentro da célula do notebook e morriam com ela.
Sobrava a peça já mapeada (texto + classe). Consequência: mudar UMA regra de
cor exigia rodar o analisador inteiro de novo -- baixar modelo, esperar,
gastar sessão de Colab. Em dois dias a regra mudou quatro vezes.

Com o bruto salvo, mudar regra vira remapear em segundos, sem rede e sem
analisador. E o bruto é BARATO: medido no Mateus 2, o CSV com lema, upos e
traços dos 5 idiomas dá 140 KB -- menos que os 438 KB da classificação já
mapeada que o projeto salvava antes disto.

O bruto é guardado no nível do TOKEN, com as palavras sintáticas dentro --
não no nível da peça já cortada. A diferença importa: a separação do clítico
("prostraram-se" -> "prostraram-" + "se") só é possível porque o token
carrega as duas palavras. Um bruto no nível da peça deixaria de fora
exatamente as mudanças de tokenização.

Ele é CACHE, não verdade: está preso à versão do analisador que o gerou, e
por isso o arquivo carimba analisador e versão.

    salvar / carregar        o arquivo do bruto
    de_stanza / de_kiwi      converter a saída do analisador pro formato daqui
    construir_pecas          bruto -> [PecaColorida], com o mapeamento base
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from classificacao import classificar_palavra_stanza, separar_por_hifen
from classificacao_ko import classificar_pecas_palavra_ko
from renderizacao import PecaColorida

FORMATO = 1   # sobe quando o formato do arquivo mudar de forma incompatível


@dataclass(frozen=True)
class PalavraBruta:
    """Uma palavra sintática, como o analisador a devolveu.

    `inicio`/`fim` são deslocamentos no texto do bloco e só o Kiwi preenche
    (o Stanza não dá deslocamento por palavra dentro de um token multipalavra).
    -1 = não informado.
    """
    texto: str
    lema: str = ""
    upos: str = ""
    xpos: str = ""
    feats: str = ""
    inicio: int = -1
    fim: int = -1


@dataclass(frozen=True)
class TokenBruto:
    """Um token como aparece ESCRITO, com as palavras sintáticas dentro.

    "prostraram-se" é um token com duas palavras; "nos" (em+os) também. A
    diferença entre os dois -- e o motivo de um poder ser separado e o outro
    não -- é o hífen, que só existe no texto do token.
    """
    texto: str
    palavras: list[PalavraBruta] = field(default_factory=list)
    # O olhar-adiante ("a" + infinitivo vira preposição) não pode atravessar
    # fronteira de frase: o Stanza analisa frase a frase, e o token seguinte
    # da OUTRA frase não é contexto nenhum. Guardar isto mantém o
    # construir_pecas idêntico ao laço que rodava dentro do notebook.
    fim_de_sentenca: bool = False


@dataclass(frozen=True)
class BlocoBruto:
    inicio_ms: int
    fim_ms: int
    texto: str
    tokens: list[TokenBruto] = field(default_factory=list)


# ── Converter a saída do analisador ──────────────────────────────────────────

def de_stanza(doc: Any, leg_texto: str, inicio_ms: int, fim_ms: int) -> BlocoBruto:
    """Converte o `doc` do Stanza (duck-typed, sem importar stanza aqui)."""
    tokens: list[TokenBruto] = []
    for sentenca in doc.sentences:
        da_sentenca = list(sentenca.tokens)
        for i, token in enumerate(da_sentenca):
            tokens.append(TokenBruto(
                texto=token.text,
                palavras=[PalavraBruta(texto=w.text or "", lema=w.lemma or "",
                                       upos=w.upos or "", xpos=w.xpos or "",
                                       feats=w.feats or "")
                          for w in token.words],
                fim_de_sentenca=(i == len(da_sentenca) - 1),
            ))
    return BlocoBruto(inicio_ms=inicio_ms, fim_ms=fim_ms, texto=leg_texto, tokens=tokens)


def de_kiwi(tokens_kiwi: Any, original: str, inicio_ms: int, fim_ms: int) -> BlocoBruto:
    """Converte a saída do Kiwi. O "token" aqui é a PALAVRA ESCRITA (o grupo
    que o Kiwi marca com o mesmo word_position) e as "palavras" são os
    morfemas dentro dela, com deslocamento -- é do deslocamento que sai o
    texto exibido, nunca da forma do morfema (ver construir_pecas)."""
    grupos: dict[tuple, list] = {}
    ordem: list[tuple] = []
    for t in tokens_kiwi:
        chave = (t.sent_position, t.word_position)
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(t)

    tokens: list[TokenBruto] = []
    for chave in ordem:
        toks = sorted(grupos[chave], key=lambda t: (t.start, -t.len))
        ini = min(t.start for t in toks)
        fim = max(t.start + t.len for t in toks)
        tokens.append(TokenBruto(
            texto=original[ini:fim],
            palavras=[PalavraBruta(texto=t.form, upos=t.tag,
                                   inicio=t.start, fim=t.start + t.len)
                      for t in toks],
        ))
    return BlocoBruto(inicio_ms=inicio_ms, fim_ms=fim_ms, texto=original, tokens=tokens)


# ── Arquivo ──────────────────────────────────────────────────────────────────

def salvar(blocos: list[BlocoBruto], caminho: Path | str, *,
           idioma: str, analisador: str, versao: str) -> Path:
    """Grava o bruto carimbado. O carimbo não é decoração: o bruto é cache de
    uma versão específica do analisador, e daqui a um ano ninguém vai lembrar
    qual."""
    caminho = Path(caminho)
    caminho.write_text(json.dumps({
        "formato": FORMATO,
        "idioma": idioma,
        "analisador": analisador,
        "versao_analisador": versao,
        "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "blocos": [asdict(b) for b in blocos],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return caminho


def carregar(caminho: Path | str) -> tuple[list[BlocoBruto], dict]:
    """Devolve (blocos, cabecalho). Formato desconhecido levanta ValueError em
    vez de tentar adivinhar -- ler um formato futuro pela metade sairia numa
    legenda errada, calada."""
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    formato = bruto.get("formato")
    if formato != FORMATO:
        raise ValueError(f"{Path(caminho).name} está no formato {formato!r}, "
                         f"e este módulo lê o {FORMATO}. Gere o bruto de novo.")
    blocos = [
        BlocoBruto(
            inicio_ms=b["inicio_ms"], fim_ms=b["fim_ms"], texto=b.get("texto", ""),
            tokens=[TokenBruto(texto=t["texto"],
                               palavras=[PalavraBruta(**p) for p in t["palavras"]])
                    for t in b["tokens"]],
        )
        for b in bruto["blocos"]
    ]
    cabecalho = {k: v for k, v in bruto.items() if k != "blocos"}
    return blocos, cabecalho


# ── Bruto -> peças (o mapeamento base) ───────────────────────────────────────

def construir_pecas(bloco: BlocoBruto, idioma: str, analisador: str) -> list[PecaColorida]:
    """Monta as peças de um bloco a partir do bruto, aplicando só o
    MAPEAMENTO BASE (o que a etiqueta do analisador significa). As correções
    -- onde a etiqueta engana -- vêm depois, na central
    (revisao_classes.aplicar_correcoes).

    Este laço morava dentro da célula do notebook, duplicado nos dois
    notebooks multicor. Aqui ele é um só, e dá pra testar sem Colab.
    """
    if analisador == "kiwi":
        return _pecas_kiwi(bloco)
    return _pecas_stanza(bloco, idioma)


def _pecas_stanza(bloco: BlocoBruto, idioma: str) -> list[PecaColorida]:
    pecas: list[PecaColorida] = []
    for token in bloco.tokens:
        if not token.palavras:
            continue
        cabeca = token.palavras[0]           # na contração, a preposição

        # Clítico que o hífen já separa na tela: cada parte com a cor dela.
        partes = separar_por_hifen(token.texto, len(token.palavras))
        if partes:
            for k, (txt, palavra) in enumerate(zip(partes, token.palavras)):
                pecas.append(PecaColorida(
                    txt,
                    classificar_palavra_stanza(txt, palavra.lema, palavra.upos,
                                               palavra.xpos, palavra.feats, idioma),
                    colado_anterior=(k > 0), upos=palavra.upos,
                    lema=palavra.lema, feats=palavra.feats))
            continue

        # TOKEN, não palavra: a contração tem que aparecer como está escrita
        # ("nos dias", não "em os dias"). A análise é só pra escolher a cor.
        pecas.append(PecaColorida(
            token.texto,
            classificar_palavra_stanza(token.texto, cabeca.lema, cabeca.upos,
                                       cabeca.xpos, cabeca.feats, idioma),
            upos=cabeca.upos, lema=cabeca.lema, feats=cabeca.feats))
    return pecas


def _pecas_kiwi(bloco: BlocoBruto) -> list[PecaColorida]:
    pecas: list[PecaColorida] = []
    for token in bloco.tokens:
        if not token.palavras:
            continue
        classes = classificar_pecas_palavra_ko(
            [{"peca": p.texto, "classe_kiwi": p.upos} for p in token.palavras])

        # O texto exibido vem SEMPRE de uma fatia do original, nunca da forma
        # do morfema: "셨" é 시+었, e exibir a forma escreveria "태어나시었을"
        # onde está escrito "태어나셨을". Morfemas que dividem a mesma fatia
        # viram uma peça só, com a classe do primeiro.
        fatias: list[list] = []
        for palavra, classe in zip(token.palavras, classes):
            if fatias and palavra.inicio < fatias[-1][1]:
                fatias[-1][1] = max(fatias[-1][1], palavra.fim)
            else:
                fatias.append([palavra.inicio, palavra.fim, classe,
                               palavra.upos, palavra.lema])
        for i, (ini, fim, classe, tag, lema) in enumerate(fatias):
            texto = bloco.texto[ini:fim]
            if not texto.strip():
                continue
            pecas.append(PecaColorida(texto, classe, colado_anterior=(i > 0),
                                      upos=tag, lema=lema))
    return pecas


def confere(blocos: list[BlocoBruto], legendas) -> Optional[str]:
    """O bruto salvo corresponde ao SRT que está sendo usado agora? Devolve
    None se confere, ou o motivo.

    Mesma ideia (e mesma tolerância) do renderizacao.classificacao_confere:
    compara só as letras e os dígitos, na ordem, porque o tokenizador separa
    "l'adorer" em dois e o Kiwi quebra a palavra coreana em morfemas.
    """
    if len(blocos) != len(legendas):
        return f"{len(blocos)} bloco(s) no bruto contra {len(legendas)} no SRT atual"

    def letras(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum())

    for i, (bloco, leg) in enumerate(zip(blocos, legendas), 1):
        do_bruto = letras("".join(t.texto for t in bloco.tokens))
        if do_bruto != letras(leg.texto):
            return f"o bloco {i} do bruto não bate com o SRT atual"
    return None
