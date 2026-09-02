# -*- coding: utf-8 -*-
"""
revisao_classes.py — O que acontece DEPOIS da classificação: correção
automática, lista de suspeitas, e a ida-e-volta pra correção manual.

Divisão de trabalho:

    classificacao.py / classificacao_ko.py   análise -> classe (por palavra)
    revisao_classes.py (aqui)                conferir, corrigir, revisar
    renderizacao.py                          classe -> cor -> .ass

Por que existe: o Stanza e o Kiwi erram, e o erro deles é MUDO -- sai uma cor
plausível e ninguém percebe até assistir o vídeo. Este módulo faz três coisas
contra isso, em ordem de quanto poupam de trabalho humano:

  1. CORREÇÃO AUTOMÁTICA (aplicar_excecoes) -- o que já se sabe que erra,
     conserta sozinho. O léxico é versionado, então correção feita uma vez
     vale pra todo capítulo seguinte.
  2. SUSPEITAS (suspeitas) -- aponta ONDE olhar, pra não ter que ler 3.300
     peças. Medido no Mateus 2: 39 apontamentos em 3.349 peças (1,2%).
  3. IDA-E-VOLTA (exportar_csv / importar_csv / pagina_revisao) -- a correção
     manual do que sobrar, numa planilha, com uma página que mostra as cores
     de verdade pra achar o erro sem assistir o vídeo.
"""
from __future__ import annotations

import csv
import difflib
import html
import json
import re
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

from classificacao import parse_feats
from cores import (CORES_HTML, MAPA_CLASSES_FINAS, cor_html, cor_texto,
                   nome_cor)
from renderizacao import PecaColorida

# As 20 oficiais MAIS as finas do coreano. O Kiwi devolve "substantivo_proprio"
# e "particula_sujeito", e é isso que fica guardado na peça -- quem traduz pra
# oficial é o cores._resolver_classe(), na hora de escolher a cor. Sem as duas
# famílias aqui, o importar_csv recusaria TODA linha do coreano.
CLASSES_VALIDAS: frozenset[str] = frozenset(CORES_HTML) | frozenset(MAPA_CLASSES_FINAS)


def _forma(texto: str) -> str:
    """A palavra como as regras a comparam: sem espaço em volta, sem caixa."""
    return (texto or "").strip().lower()


def _oficial(classe: str) -> str:
    """A classe como o espectador a vê -- é ela que as suspeitas comparam.
    "terminacao_final_neutra" e "terminacao_final_imperativa" saem da mesma
    cor, então tratá-las como classes diferentes inventaria divergência onde
    a tela não mostra nenhuma."""
    return MAPA_CLASSES_FINAS.get(classe, classe)

# UPOS que o classificar_palavra_stanza trata com regra própria. O que não
# está aqui cai no `return "adverbio"` do fim -- que é um chute, não uma
# análise, e sai da mesma cor que um advérbio de verdade.
_UPOS_COM_REGRA = frozenset({
    "PROPN", "NOUN", "PRON", "VERB", "AUX", "ADJ", "DET",
    "ADP", "CCONJ", "SCONJ", "ADV", "NUM", "INTJ", "PUNCT",
})
# PART tem regra só em inglês (to/'s/not) e em chinês (的, 了...).
_UPOS_COM_REGRA_POR_IDIOMA = {"en": {"PART"}, "zh": {"PART"}}

# O Kiwi devolve isto quando não conhece a tag. Vira cinza -- a MESMA cor da
# pontuação --, então some no meio da legenda sem nenhum sinal.
_CLASSE_SEM_REGRA_KO = "outro"


# ══════════════════════════════════════════════════════════════════════════
# 1. Correção automática
# ══════════════════════════════════════════════════════════════════════════

CAMINHO_CENTRAL_PADRAO = Path(__file__).parent.parent / "dados_lexico" / "classes-correcoes.json"

FORMATO_CENTRAL = 1


class ErroDeRegra(Exception):
    """A central tem uma regra que não dá pra executar — com o motivo."""


def carregar_central(caminho: Path | str | None = None) -> list[dict]:
    """Lê a central de correções automáticas.

    Ausente = lista vazia: a central é opcional por construção, e um projeto
    novo começa sem regra nenhuma. Formato desconhecido, ao contrário, LEVANTA
    -- ler pela metade sairia numa legenda errada, calada.
    """
    caminho = Path(caminho or CAMINHO_CENTRAL_PADRAO)
    if not caminho.exists():
        return []
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    formato = bruto.get("formato")
    if formato != FORMATO_CENTRAL:
        raise ErroDeRegra(f"{caminho.name} está no formato {formato!r}, e este "
                          f"módulo lê o {FORMATO_CENTRAL}.")
    regras = bruto.get("regras", [])
    for i, r in enumerate(regras, 1):
        conferir_regra(r, f"regra {i} ({r.get('id', 'sem id')})")
    return regras


_CAMPOS_QUANDO = {"palavra", "lema", "upos", "classe", "feats", "seguinte", "anterior"}
_CAMPOS_ENTAO  = {"classe", "seguinte_classe", "anterior_classe"}


def conferir_regra(regra: dict, onde: str) -> None:
    """Recusa regra malformada na LEITURA, não na hora de aplicar. Regra com
    campo escrito errado seria silenciosa: ela simplesmente nunca casaria, e
    ninguém descobre que a correção parou de acontecer."""
    if "quando" not in regra or "entao" not in regra:
        raise ErroDeRegra(f"{onde}: falta 'quando' ou 'entao'")
    def conferir_condicao(cond, caminho_):
        sobra = set(cond) - _CAMPOS_QUANDO
        if sobra:
            raise ErroDeRegra(f"{onde}: campo desconhecido em {caminho_}: "
                              f"{', '.join(sorted(sobra))}. Válidos: "
                              f"{', '.join(sorted(_CAMPOS_QUANDO))}")
        for vizinho in ("seguinte", "anterior"):
            if vizinho in cond:
                conferir_condicao(cond[vizinho], f"{caminho_}.{vizinho}")
    conferir_condicao(regra["quando"], "quando")
    sobra = set(regra["entao"]) - _CAMPOS_ENTAO
    if sobra:
        raise ErroDeRegra(f"{onde}: campo desconhecido em 'entao': "
                          f"{', '.join(sorted(sobra))}")
    for campo, valor in regra["entao"].items():
        if valor not in CLASSES_VALIDAS:
            raise ErroDeRegra(f"{onde}: 'entao.{campo}' pede a classe '{valor}', "
                              f"que não existe")
    if not regra.get("porque"):
        raise ErroDeRegra(f"{onde}: falta o 'porque'. Regra sem motivo ninguém "
                          f"ousa apagar depois, e a central vira entulho.")


def _casa(peca, cond: dict) -> bool:
    """A peça satisfaz esta condição? Peça inexistente (borda do bloco) nunca
    casa -- 'não existe' não é 'qualquer coisa'."""
    if peca is None:
        return False
    if "palavra" in cond and _forma(peca.texto) not in {_forma(x) for x in cond["palavra"]}:
        return False
    if "lema" in cond and _forma(peca.lema) not in {_forma(x) for x in cond["lema"]}:
        return False
    if "upos" in cond and peca.upos not in cond["upos"]:
        return False
    if "classe" in cond and _oficial(peca.classe) not in cond["classe"]:
        return False
    if "feats" in cond:
        traços = parse_feats(peca.feats)
        for chave, valor in cond["feats"].items():
            if traços.get(chave) != valor:
                return False
    return True


def _regra_casa(regra: dict, pecas: list, i: int) -> bool:
    quando = regra["quando"]
    propria = {k: v for k, v in quando.items() if k not in ("seguinte", "anterior")}
    if not _casa(pecas[i], propria):
        return False
    if "seguinte" in quando:
        if not _casa(pecas[i + 1] if i + 1 < len(pecas) else None, quando["seguinte"]):
            return False
    if "anterior" in quando:
        if not _casa(pecas[i - 1] if i > 0 else None, quando["anterior"]):
            return False
    return True


def aplicar_correcoes(
    blocos: list[dict],
    idioma: str,
    regras: Optional[list[dict]] = None,
) -> tuple[list[dict], list[str]]:
    """Aplica a central de correções automáticas a um idioma.

    Devolve (blocos, mudancas) -- `mudancas` sempre lista o que mudou e por
    qual regra, porque correção automática silenciosa é a mesma armadilha que
    o erro silencioso que ela conserta.

    Ordem: a primeira regra que casa vence, e cada peça é decidida uma vez.
    As regras não atravessam fronteira de bloco: o contexto que vale é o que
    aparece junto na tela.
    """
    if regras is None:
        regras = carregar_central()
    doidioma = [r for r in regras if idioma in r.get("idiomas", [])]
    if not doidioma:
        return blocos, []

    saida, mudancas = [], []
    for n, bloco in enumerate(blocos, 1):
        pecas = list(bloco.get("pecas", []))
        for i in range(len(pecas)):
            for regra in doidioma:
                if not _regra_casa(regra, pecas, i):
                    continue
                alvos = [(i, regra["entao"].get("classe")),
                         (i + 1, regra["entao"].get("seguinte_classe")),
                         (i - 1, regra["entao"].get("anterior_classe"))]
                for k, nova in alvos:
                    if nova is None or not (0 <= k < len(pecas)):
                        continue
                    if pecas[k].classe != nova:
                        mudancas.append(
                            f"bloco {n}: «{pecas[k].texto}» {pecas[k].classe} → {nova}"
                            f"   [{regra.get('id', 'sem id')}]")
                        pecas[k] = pecas[k]._replace(classe=nova)
                break
        saida.append({**bloco, "pecas": pecas})
    return saida, mudancas


def corrigir_pontuacao(blocos: list[dict]) -> tuple[list[dict], list[str]]:
    """Invariante mecânica, não linguística: peça só de sinais é pontuação, e
    peça com letra ou dígito não é.

    Não depende de idioma nem de analisador, e no Mateus 2 não corrige nada
    (as 3.349 peças já respeitam) -- é guarda, não conserto. Vale a pena
    porque o modo de errar aqui é invisível: a classe 'outro' do Kiwi (tag
    imprevista) sai CINZA, a mesma cor da pontuação.
    """
    saida, mudancas = [], []
    for i, bloco in enumerate(blocos, 1):
        pecas = []
        for peca in bloco.get("pecas", []):
            tem_letra = any(c.isalnum() for c in peca.texto)
            if not tem_letra and peca.classe != "pontuacao" and peca.texto.strip():
                mudancas.append(f"bloco {i}: «{peca.texto}» {peca.classe} → pontuacao "
                                f"(só sinais)")
                peca = peca._replace(classe="pontuacao")
            elif tem_letra and peca.classe == "pontuacao":
                mudancas.append(f"bloco {i}: «{peca.texto}» está como pontuacao mas tem "
                                f"letra — CONFIRA (pode ser a classe 'outro' do Kiwi, "
                                f"que sai da mesma cor)")
            pecas.append(peca)
        saida.append({**bloco, "pecas": pecas})
    return saida, mudancas


# ══════════════════════════════════════════════════════════════════════════
# 2. Suspeitas — onde olhar
# ══════════════════════════════════════════════════════════════════════════

class Suspeita(NamedTuple):
    idioma: str
    bloco: int          # 1-based
    ordem: int          # posição da peça dentro do bloco, 1-based
    palavra: str
    classe: str
    motivo: str


# Calibrado contra o Mateus 2 inteiro (3.349 peças nos 5 idiomas), decodificado
# do .ass queimado. Os números por regra estão em CONFIGURACAO.md. Limiar que
# nunca aponta nada não protege; limiar que aponta tudo ninguém lê.
_MINORIA_MAXIMA = 2      # ocorrências da leitura minoritária
_MAIORIA_MINIMA = 3      # ...contra estas da majoritária
_RARA_MAXIMA    = 3      # classe com até tantas ocorrências no idioma


def suspeitas(blocos_por_idioma: dict[str, list[dict]]) -> list[Suspeita]:
    """Peças que merecem um olhar humano, com o motivo de cada uma.

    NÃO é uma lista de erros: as três regras apontam ambiguidade legítima
    junto com erro de verdade ("où" é advérbio numa frase e pronome na outra).
    É uma lista de ONDE olhar.
    """
    achados: list[Suspeita] = []
    for idioma, blocos in sorted(blocos_por_idioma.items()):
        achados += _suspeitas_do_idioma(idioma, blocos)
    return achados


def _suspeitas_do_idioma(idioma: str, blocos: list[dict]) -> list[Suspeita]:
    from collections import Counter, defaultdict

    todas = [(i, j, p)
             for i, bloco in enumerate(blocos, 1)
             for j, p in enumerate(bloco.get("pecas", []), 1)]
    achados: list[Suspeita] = []

    # ── (a) o analisador não tinha regra: a classe saiu de um chute ──────
    com_regra = _UPOS_COM_REGRA | _UPOS_COM_REGRA_POR_IDIOMA.get(idioma, set())
    for i, j, p in todas:
        if p.classe == _CLASSE_SEM_REGRA_KO:
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    "o Kiwi devolveu uma tag sem regra — sai CINZA, "
                                    "igual à pontuação"))
        elif p.upos and idioma != "ko" and p.upos not in com_regra:
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    f"o Stanza devolveu {p.upos}, que não tem regra — "
                                    f"virou '{p.classe}' por falta de opção"))

    # ── (b) a mesma palavra recebeu classes diferentes ──────────────────
    por_palavra: dict[str, Counter] = defaultdict(Counter)
    for _, _, p in todas:
        por_palavra[_forma(p.texto)][_oficial(p.classe)] += 1
    minoritarias: dict[str, set[str]] = {}
    for palavra, cont in por_palavra.items():
        if len(cont) < 2:
            continue
        (_, q_maior), *resto = cont.most_common()
        if q_maior < _MAIORIA_MINIMA:
            continue
        fora = {cl for cl, q in resto if q <= _MINORIA_MAXIMA}
        if fora:
            minoritarias[palavra] = fora
    for i, j, p in todas:
        classes_raras = minoritarias.get(_forma(p.texto), ())
        if _oficial(p.classe) in classes_raras:
            maioria = por_palavra[_forma(p.texto)].most_common(1)[0]
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    f"aqui é '{_oficial(p.classe)}', mas nas outras {maioria[1]} vezes "
                                    f"desta legenda é '{maioria[0]}'"))

    # ── (c) classe rara neste idioma ────────────────────────────────────
    cont_classe = Counter(_oficial(p.classe) for _, _, p in todas)
    raras = {cl for cl, q in cont_classe.items() if q <= _RARA_MAXIMA}
    ja_apontado = {(s.bloco, s.ordem) for s in achados}
    for i, j, p in todas:
        if _oficial(p.classe) in raras and (i, j) not in ja_apontado:
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    f"'{_oficial(p.classe)}' aparece só "
                                    f"{cont_classe[_oficial(p.classe)]}× "
                                    f"em todo o {idioma.upper()} — classe rara é fácil de "
                                    f"sair errada sem ninguém notar"))

    return sorted(achados, key=lambda s: (s.bloco, s.ordem))


# ══════════════════════════════════════════════════════════════════════════
# 3. Ida-e-volta: planilha pra corrigir, página pra achar o que corrigir
# ══════════════════════════════════════════════════════════════════════════

_COLUNAS = ["idioma", "bloco", "ordem", "palavra", "classe",
            "cor", "manual", "suspeita", "upos", "colado_anterior",
            "inicio_ms", "fim_ms"]


def exportar_csv(
    blocos_por_idioma: dict[str, list[dict]],
    caminho: Path | str,
    achados: Optional[Iterable[Suspeita]] = None,
) -> Path:
    """Um CSV com TODOS os idiomas, uma linha por peça — pra abrir no Sheets,
    corrigir a coluna `classe` e subir de volta (ver importar_csv).

    O arquivo é autossuficiente: leva tempo, ordem e `colado_anterior`, então
    o importar_csv reconstrói a classificação inteira sem precisar do JSON.
    Só a coluna `classe` deve ser editada; as outras são o que identifica a
    peça, e mexer nelas quebra a volta.
    """
    caminho = Path(caminho)
    achados = list(achados or [])
    motivo_de = {}
    for s in achados:
        motivo_de.setdefault((s.idioma, s.bloco, s.ordem), []).append(s.motivo)

    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(_COLUNAS)
        for idioma, blocos in sorted(blocos_por_idioma.items()):
            for i, bloco in enumerate(blocos, 1):
                for j, p in enumerate(bloco.get("pecas", []), 1):
                    w.writerow([
                        idioma, i, j, p.texto, p.classe,
                        nome_cor(p.classe),
                        # já mexido à mão numa revisão anterior: é o que a
                        # diferença entre classe e classe_automatica marca
                        "sim" if (p.classe_automatica
                                  and p.classe != p.classe_automatica) else "",
                        " / ".join(motivo_de.get((idioma, i, j), ())),
                        p.upos, int(p.colado_anterior),
                        bloco["inicio_ms"], bloco["fim_ms"],
                    ])
    return caminho


class ErroDeRevisao(Exception):
    """O CSV corrigido não pode ser usado — com o motivo exato."""


def importar_csv(caminho: Path | str) -> tuple[dict[str, list[dict]], list[str]]:
    """Lê o CSV corrigido de volta pra {idioma: blocos}.

    Recusa em vez de aceitar em silêncio: classe inexistente, coluna faltando,
    bloco sem peça. O motivo de recusar é que o estrago é invisível -- uma
    classe com erro de digitação viraria cinza no vídeo, do jeitinho de uma
    pontuação, e ninguém veria antes de assistir.
    """
    caminho = Path(caminho)
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        raise ErroDeRevisao(f"{caminho.name} está vazio")
    faltando = [c for c in _COLUNAS if c not in linhas[0]]
    if faltando:
        raise ErroDeRevisao(f"{caminho.name} está sem a(s) coluna(s): {', '.join(faltando)}. "
                            f"Baixe o CSV de novo e corrija só a coluna 'classe'.")

    invalidas: dict[str, int] = {}
    for r in linhas:
        c = (r["classe"] or "").strip()
        if c not in CLASSES_VALIDAS:
            invalidas[c] = invalidas.get(c, 0) + 1
    if invalidas:
        lista = ", ".join(f"'{c}' ({q}×)" for c, q in sorted(invalidas.items()))
        raise ErroDeRevisao(
            f"{len(invalidas)} classe(s) que não existem: {lista}.\n"
            f"As válidas são: {', '.join(sorted(CLASSES_VALIDAS))}")

    por_idioma: dict[str, dict[int, dict]] = {}
    for r in linhas:
        idioma = r["idioma"].strip()
        bloco = int(r["bloco"])
        destino = por_idioma.setdefault(idioma, {})
        alvo = destino.setdefault(bloco, {"inicio_ms": int(r["inicio_ms"]),
                                          "fim_ms": int(r["fim_ms"]),
                                          "_pecas": []})
        alvo["_pecas"].append((int(r["ordem"]),
                               PecaColorida(r["palavra"], r["classe"].strip(),
                                            bool(int(r["colado_anterior"] or 0)),
                                            r.get("upos", ""))))

    saida: dict[str, list[dict]] = {}
    avisos: list[str] = []
    for idioma, blocos in por_idioma.items():
        numeros = sorted(blocos)
        if numeros != list(range(1, len(numeros) + 1)):
            raise ErroDeRevisao(f"{idioma}: os blocos do CSV não vão de 1 a "
                                f"{len(numeros)} sem buraco — alguma linha foi apagada?")
        lista = []
        for n in numeros:
            b = blocos[n]
            pecas = [p for _, p in sorted(b["_pecas"], key=lambda t: t[0])]
            lista.append({"inicio_ms": b["inicio_ms"], "fim_ms": b["fim_ms"], "pecas": pecas})
        saida[idioma] = lista
        avisos.append(f"{idioma}: {len(lista)} blocos, "
                      f"{sum(len(b['pecas']) for b in lista)} peças")
    return saida, avisos


def aplicar_csv(
    blocos_por_idioma: dict[str, list[dict]],
    caminho: Path | str,
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Passa a coluna `classe` do CSV corrigido pras peças que estão na
    memória, e devolve (blocos, mudancas).

    Por que não usar o CSV inteiro: ele não carrega `lema`, `feats` nem
    `classe_automatica` -- de propósito, pra planilha ter só o que se deve
    editar. Reconstruir a partir dele perderia justamente o que as regras
    leem e o carimbo que distingue correção da mão. Aqui só a CLASSE atravessa.

    Recusa quando as peças do CSV não são as mesmas da memória: linha
    apagada, palavra reescrita, idioma faltando. Melhor parar do que casar
    classe com a palavra errada.
    """
    do_csv, _ = importar_csv(caminho)

    faltando = [i for i in blocos_por_idioma if i not in do_csv]
    if faltando:
        raise ErroDeRevisao(f"o CSV não tem estes idiomas: {', '.join(faltando)}. "
                            f"Envie o arquivo inteiro, não uma aba filtrada.")

    saida, mudancas = {}, []
    for idioma, blocos in blocos_por_idioma.items():
        novos_blocos = do_csv[idioma]
        if len(novos_blocos) != len(blocos):
            raise ErroDeRevisao(f"{idioma}: o CSV tem {len(novos_blocos)} blocos e a "
                                f"classificação tem {len(blocos)}")
        lista = []
        for i, (bloco, do_arquivo) in enumerate(zip(blocos, novos_blocos), 1):
            pecas, do_csv_pecas = bloco.get("pecas", []), do_arquivo.get("pecas", [])
            if len(pecas) != len(do_csv_pecas):
                raise ErroDeRevisao(f"{idioma} bloco {i}: o CSV tem "
                                    f"{len(do_csv_pecas)} peças e a classificação "
                                    f"tem {len(pecas)} — alguma linha foi apagada?")
            novas = []
            for peca, do_arq in zip(pecas, do_csv_pecas):
                if _forma(peca.texto) != _forma(do_arq.texto):
                    raise ErroDeRevisao(
                        f"{idioma} bloco {i}: o CSV diz «{do_arq.texto}» onde a "
                        f"classificação tem «{peca.texto}». Só a coluna `classe` "
                        f"pode ser editada.")
                if do_arq.classe != peca.classe:
                    mudancas.append({"idioma": idioma, "bloco": i,
                                     "palavra": peca.texto,
                                     "de": peca.classe, "para": do_arq.classe})
                    peca = peca._replace(classe=do_arq.classe)
                novas.append(peca)
            lista.append({**bloco, "pecas": novas})
        saida[idioma] = lista
    return saida, mudancas


def diferencas(antes: dict[str, list[dict]], depois: dict[str, list[dict]]) -> list[dict]:
    """O que a correção manual mudou — uma lista de
    {idioma, bloco, palavra, de, para}. Serve pro relatório e pro
    sugerir_excecoes()."""
    mudancas = []
    for idioma, blocos_d in sorted(depois.items()):
        blocos_a = antes.get(idioma, [])
        for i, bloco_d in enumerate(blocos_d, 1):
            if i > len(blocos_a):
                continue
            pecas_a = blocos_a[i - 1].get("pecas", [])
            for j, p_d in enumerate(bloco_d.get("pecas", [])):
                if j >= len(pecas_a):
                    continue
                p_a = pecas_a[j]
                if p_a.classe != p_d.classe:
                    mudancas.append({"idioma": idioma, "bloco": i, "palavra": p_d.texto,
                                     "de": p_a.classe, "para": p_d.classe})
    return mudancas


def sugerir_regras(mudancas: list[dict]) -> str:
    """Transforma as correções manuais em regras prontas pra central.

    Só sugere a correção que se repetiu (mesma palavra, mesmo de→para, mais
    de uma vez): correção que aconteceu UMA vez pode ser questão de contexto,
    e virar regra fixa espalharia o erro pelo resto da Bíblia.

    Sai no formato da central, com o `porque` por preencher -- de propósito.
    A central recusa regra sem motivo na leitura, então a sugestão não entra
    versionada sem alguém escrever por que ela existe.
    """
    from collections import Counter
    contagem = Counter((m["idioma"], _forma(m["palavra"]), m["de"], m["para"])
                       for m in mudancas)
    regras = []
    for (idioma, palavra, de, para), q in sorted(contagem.items()):
        if q < 2:
            continue
        regras.append({
            "id": f"{idioma}-{re.sub(r'[^a-z0-9]+', '-', palavra).strip('-') or 'palavra'}-{para}",
            "idiomas": [idioma],
            "quando": {"palavra": [palavra], "classe": [de]},
            "entao": {"classe": para},
            "porque": f"CORRIGIDO À MÃO {q}× no vídeo — escreva aqui POR QUE o "
                      f"analisador erra, senão a central recusa esta regra na leitura.",
        })
    if not regras:
        return ""
    return json.dumps(regras, ensure_ascii=False, indent=2)


_PAGINA = """<!doctype html>
<meta charset="utf-8">
<title>Revisão de classes — {titulo}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; background: #f6f6f4; color: #1a1a1a;
         font: 15px/1.6 -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 80px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #666; margin: 0 0 28px; }}
  .resumo {{ background: #fff; border: 1px solid #e0e0dc; border-radius: 10px;
            padding: 16px 20px; margin-bottom: 28px; }}
  .resumo b {{ font-variant-numeric: tabular-nums; }}
  .bloco {{ background: #fff; border: 1px solid #e0e0dc; border-radius: 10px;
           padding: 14px 18px; margin-bottom: 14px; }}
  .cab {{ color: #888; font-size: 12px; letter-spacing: .04em;
         text-transform: uppercase; margin-bottom: 10px; }}
  .linha {{ margin-bottom: 8px; }}
  .lang {{ display: inline-block; width: 26px; color: #999; font-size: 12px;
          font-weight: 600; vertical-align: middle; }}
  .p {{ display: inline-block; padding: 1px 5px; margin: 2px 1px; border-radius: 4px;
       border: 2px solid; vertical-align: middle; }}
  .p.suspeita {{ outline: 2px dashed #d33; outline-offset: 2px; }}
  .aviso {{ background: #fff8e1; border: 1px solid #ffe0a3; border-radius: 10px;
           padding: 14px 18px; margin-bottom: 20px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 5px 10px 5px 0; vertical-align: top; }}
  th {{ color: #888; font-weight: 600; border-bottom: 1px solid #e0e0dc; }}
  td.pal {{ font-weight: 600; white-space: nowrap; }}
  .legenda span {{ display: inline-block; padding: 1px 6px; margin: 2px 3px 2px 0;
                  border: 2px solid; border-radius: 4px; font-size: 12px; }}
</style>
<main>
<h1>Revisão de classes — {titulo}</h1>
<p class="sub">As cores são as mesmas do vídeo. O tracejado vermelho marca as
peças que entraram na lista de suspeitas.</p>
<div class="resumo">{resumo}</div>
{avisos}
<h2 style="font-size:16px">Legenda das cores</h2>
<p class="legenda">{legenda}</p>
{corpo}
</main>
"""


def _span(peca: PecaColorida, suspeita: bool) -> str:
    fundo = cor_html(peca.classe)
    return (f'<span class="p{" suspeita" if suspeita else ""}" '
            f'style="border-color:{fundo};background:{fundo};color:{cor_texto(peca.classe)}" '
            f'title="{html.escape(peca.classe)}">{html.escape(peca.texto)}</span>')


def pagina_revisao(
    blocos_por_idioma: dict[str, list[dict]],
    caminho: Path | str,
    achados: Optional[Iterable[Suspeita]] = None,
    titulo: str = "",
) -> Path:
    """Uma página HTML com a legenda inteira pintada como vai pro vídeo.

    Existe porque nome de classe não é o que se enxerga: o erro aparece
    quando 'Herodes' sai preto no meio de nomes próprios amarelos. Antes
    disto, achar um erro de cor exigia assistir o vídeo.
    """
    caminho = Path(caminho)
    achados = list(achados or [])
    marcadas = {(s.idioma, s.bloco, s.ordem) for s in achados}

    idiomas = sorted(blocos_por_idioma)
    n_blocos = max((len(b) for b in blocos_por_idioma.values()), default=0)
    n_pecas = sum(len(bl.get("pecas", [])) for b in blocos_por_idioma.values() for bl in b)

    corpo = []
    for i in range(1, n_blocos + 1):
        linhas = []
        for idioma in idiomas:
            blocos = blocos_por_idioma[idioma]
            if i > len(blocos):
                continue
            pecas = blocos[i - 1].get("pecas", [])
            pintadas = "".join(_span(p, (idioma, i, j) in marcadas)
                               for j, p in enumerate(pecas, 1))
            linhas.append(f'<div class="linha"><span class="lang">{idioma.upper()}</span>'
                          f'{pintadas}</div>')
        corpo.append(f'<div class="bloco"><div class="cab">bloco {i}</div>'
                     + "".join(linhas) + "</div>")

    if achados:
        linhas = "".join(
            f"<tr><td>{s.idioma}</td><td>{s.bloco}</td><td class='pal'>{html.escape(s.palavra)}</td>"
            f"<td>{s.classe}</td><td>{html.escape(s.motivo)}</td></tr>"
            for s in sorted(achados, key=lambda s: (s.idioma, s.bloco, s.ordem)))
        avisos = (f'<div class="aviso"><b>{len(achados)} peça(s) pra conferir</b>'
                  f'<table><tr><th>idioma</th><th>bloco</th><th>palavra</th>'
                  f'<th>classe</th><th>por quê</th></tr>{linhas}</table></div>')
    else:
        avisos = '<div class="aviso"><b>Nenhuma suspeita</b> — o que não quer dizer nenhum erro.</div>'

    usadas = sorted({p.classe for b in blocos_por_idioma.values()
                     for bl in b for p in bl.get("pecas", [])})
    legenda = "".join(
        f'<span style="border-color:{cor_html(c)};background:{cor_html(c)};'
        f'color:{cor_texto(c)}">{c}</span>' for c in usadas)

    resumo = (f"<b>{n_pecas}</b> peças em <b>{n_blocos}</b> blocos e "
              f"<b>{len(idiomas)}</b> idiomas ({', '.join(i.upper() for i in idiomas)}). "
              f"<b>{len(achados)}</b> na lista de suspeitas "
              f"({len(achados) / n_pecas:.1%} do total).")

    caminho.write_text(_PAGINA.format(titulo=html.escape(titulo or caminho.stem),
                                      resumo=resumo, avisos=avisos,
                                      legenda=legenda, corpo="".join(corpo)),
                       encoding="utf-8")
    return caminho


# ══════════════════════════════════════════════════════════════════════════
# 4. Refazer do bruto sem apagar a correção manual
# ══════════════════════════════════════════════════════════════════════════

def remapear(
    blocos_salvos: Optional[list[dict]],
    blocos_brutos: list,
    idioma: str,
    analisador: str,
    regras: Optional[list[dict]] = None,
) -> tuple[list[dict], list[str]]:
    """Refaz a classificação a partir do BRUTO com as regras de hoje,
    preservando o que foi corrigido à mão.

    É o que o bruto salvo compra: mudar uma regra de cor deixa de exigir
    rodar o Stanza/Kiwi de novo. E é seguro porque a peça guarda
    `classe_automatica` -- onde ela difere de `classe`, a diferença é humana
    e é mantida.

    `blocos_salvos` pode ser None (nunca houve classificação): aí é só
    mapear. Devolve (blocos, relatorio).
    """
    from analise import construir_pecas

    novos = [
        {"inicio_ms": b.inicio_ms, "fim_ms": b.fim_ms,
         "pecas": construir_pecas(b, idioma, analisador)}
        for b in blocos_brutos
    ]
    novos, mudancas_regra = aplicar_correcoes(novos, idioma, regras)
    novos = [
        {**b, "pecas": [p._replace(classe_automatica=p.classe) for p in b["pecas"]]}
        for b in novos
    ]
    relatorio = [f"{len(mudancas_regra)} correção(ões) da central"]

    if not blocos_salvos:
        return novos, relatorio

    sem_carimbo = sum(1 for b in blocos_salvos for p in b.get("pecas", [])
                      if not p.classe_automatica)
    if sem_carimbo:
        relatorio.append(
            f"⚠️  {sem_carimbo} peça(s) salvas são anteriores ao carimbo "
            f"`classe_automatica`: não dá pra saber o que nelas foi corrigido à "
            f"mão, então valem as regras de hoje. Confira a revisão antes de queimar.")

    mantidas, perdidas = 0, []
    for i, bloco_novo in enumerate(novos):
        if i >= len(blocos_salvos):
            break
        salvas = blocos_salvos[i].get("pecas", [])
        # só as peças que a mão mexeu interessam
        corrigidas = {j: p for j, p in enumerate(salvas)
                      if p.classe_automatica and p.classe != p.classe_automatica}
        if not corrigidas:
            continue
        pecas = list(bloco_novo["pecas"])
        # o remapeamento pode ter mudado o CORTE das peças (foi o que a
        # separação do clítico fez), então casa por texto em vez de por posição
        sm = difflib.SequenceMatcher(
            None, [_forma(p.texto) for p in salvas],
            [_forma(p.texto) for p in pecas], autojunk=False)
        mapa = {}
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    mapa[i1 + k] = j1 + k
        for j, peca_salva in corrigidas.items():
            destino = mapa.get(j)
            if destino is None:
                perdidas.append(f"bloco {i + 1}: «{peca_salva.texto}» "
                                f"({peca_salva.classe_automatica} → {peca_salva.classe})")
                continue
            pecas[destino] = pecas[destino]._replace(classe=peca_salva.classe)
            mantidas += 1
        novos[i] = {**bloco_novo, "pecas": pecas}

    relatorio.append(f"{mantidas} correção(ões) manual(is) preservada(s)")
    if perdidas:
        relatorio.append(
            f"⚠️  {len(perdidas)} correção(ões) manual(is) NÃO puderam ser "
            f"reaproveitadas (a peça mudou de forma no remapeamento):")
        relatorio += [f"      {x}" for x in perdidas]
    return novos, relatorio
