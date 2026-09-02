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
import html
import json
import re
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

from cores import CORES_HTML, cor_html, cor_texto, nome_cor
from renderizacao import PecaColorida

CAMINHO_LEXICO_PADRAO = Path(__file__).parent.parent / "dados_lexico" / "classes-excecoes.json"

CLASSES_VALIDAS: frozenset[str] = frozenset(CORES_HTML)

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

def carregar_lexico(caminho: Path | str | None = None) -> dict[str, list[dict]]:
    """Lê o léxico de exceções versionado. Ausente = dicionário vazio: o
    léxico é opcional por construção, e um projeto novo começa sem nenhum."""
    caminho = Path(caminho or CAMINHO_LEXICO_PADRAO)
    if not caminho.exists():
        return {}
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return {k: v for k, v in bruto.items() if not k.startswith("_")}


def _forma(texto: str) -> str:
    return (texto or "").strip().lower()


def aplicar_excecoes(
    blocos: list[dict],
    idioma: str,
    lexico: Optional[dict[str, list[dict]]] = None,
) -> tuple[list[dict], list[str]]:
    """Aplica o léxico de exceções às peças já classificadas.

    Devolve (blocos, mudancas) -- `mudancas` sempre lista o que mudou, porque
    correção automática silenciosa é a mesma armadilha que o erro silencioso
    que ela conserta.

    Cada regra é {palavra, de, para, porque}. O `de` é a classe que o
    analisador devolveu, e é ele que torna a regra CONDICIONAL: sem ele, uma
    entrada pra "a" pintaria de preposição todo artigo "a" do capítulo.
    """
    regras = (lexico if lexico is not None else carregar_lexico()).get(idioma, [])
    if not regras:
        return blocos, []

    por_palavra: dict[str, list[dict]] = {}
    for r in regras:
        por_palavra.setdefault(_forma(r["palavra"]), []).append(r)

    saida, mudancas = [], []
    for i, bloco in enumerate(blocos, 1):
        pecas = []
        for peca in bloco.get("pecas", []):
            nova = peca
            for r in por_palavra.get(_forma(peca.texto), ()):
                de = r.get("de")
                if de and de != peca.classe:
                    continue
                if r["para"] not in CLASSES_VALIDAS:
                    mudancas.append(f"bloco {i}: regra de «{peca.texto}» pede a classe "
                                    f"'{r['para']}', que não existe — ignorada")
                    continue
                if r["para"] != peca.classe:
                    nova = peca._replace(classe=r["para"])
                    mudancas.append(f"bloco {i}: «{peca.texto}» {peca.classe} → {r['para']}"
                                    + (f"  ({r['porque']})" if r.get("porque") else ""))
                break
            pecas.append(nova)
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
        por_palavra[_forma(p.texto)][p.classe] += 1
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
        if p.classe in classes_raras:
            maioria = por_palavra[_forma(p.texto)].most_common(1)[0]
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    f"aqui é '{p.classe}', mas nas outras {maioria[1]} vezes "
                                    f"desta legenda é '{maioria[0]}'"))

    # ── (c) classe rara neste idioma ────────────────────────────────────
    cont_classe = Counter(p.classe for _, _, p in todas)
    raras = {cl for cl, q in cont_classe.items() if q <= _RARA_MAXIMA}
    ja_apontado = {(s.bloco, s.ordem) for s in achados}
    for i, j, p in todas:
        if p.classe in raras and (i, j) not in ja_apontado:
            achados.append(Suspeita(idioma, i, j, p.texto, p.classe,
                                    f"'{p.classe}' aparece só {cont_classe[p.classe]}× "
                                    f"em todo o {idioma.upper()} — classe rara é fácil de "
                                    f"sair errada sem ninguém notar"))

    return sorted(achados, key=lambda s: (s.bloco, s.ordem))


# ══════════════════════════════════════════════════════════════════════════
# 3. Ida-e-volta: planilha pra corrigir, página pra achar o que corrigir
# ══════════════════════════════════════════════════════════════════════════

_COLUNAS = ["idioma", "bloco", "ordem", "palavra", "classe",
            "cor", "suspeita", "upos", "colado_anterior", "inicio_ms", "fim_ms"]


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


def sugerir_excecoes(mudancas: list[dict]) -> str:
    """Transforma as correções manuais em entradas prontas pro léxico.

    Só sugere a correção que se repetiu (mesma palavra, mesmo de→para, mais de
    uma vez): correção que aconteceu UMA vez pode ser questão de contexto, e
    virar regra fixa espalharia o erro pelo resto da Bíblia.
    """
    from collections import Counter
    contagem = Counter((m["idioma"], _forma(m["palavra"]), m["de"], m["para"])
                       for m in mudancas)
    por_idioma: dict[str, list[dict]] = {}
    for (idioma, palavra, de, para), q in sorted(contagem.items()):
        if q < 2:
            continue
        por_idioma.setdefault(idioma, []).append({
            "palavra": palavra, "de": de, "para": para,
            "porque": f"corrigido à mão {q}× — PREENCHA o porquê antes de versionar",
        })
    if not por_idioma:
        return ""
    return json.dumps(por_idioma, ensure_ascii=False, indent=2)


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
