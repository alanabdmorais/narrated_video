#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar-central-cores.py — Gera as DUAS centrais de cores a partir do cores.py.

    python3 assets/gerar-central-cores.py

Saídas (ambas na pasta assets/):
    central-decisao-cores.html      -> 5 idiomas (pt/en/es/fr/ko)
    central-decisao-cores-zh.html   -> 6 idiomas (+ chinês)

Por que um gerador em vez de dois arquivos editados à mão: as duas centrais
compartilham quase tudo (as 20 classes e as 21 cores são idênticas — o chinês
não trouxe nenhuma categoria nova, só reaproveita `particula`). Mantidas à
mão, uma correção entraria numa e não na outra. Aqui a única fonte de verdade
das cores é o `pipeline/modulos/cores.py`, e o que muda entre as versões está
declarado em UM lugar só (VARIANTES, abaixo).

O HTML de estrutura/CSS/JS vem do próprio central-decisao-cores.html, usado
como template — este script só troca o bloco `const DADOS` e alguns textos.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pipeline" / "modulos"))

import cores  # noqa: E402
from config import PipelineConfig  # noqa: E402

ASSETS = RAIZ / "assets"
TEMPLATE = ASSETS / "central-decisao-cores.html"

# ── Exemplos em chinês, por classe ────────────────────────────────────────────
# "—" = a classe não existe nesse idioma (modal/auxiliar são só do inglês; as
# terminações e o sufixo, só do coreano).
EXEMPLOS_ZH = {
    "substantivo": "路", "nome_proprio": "大卫", "verbo": "走", "pronome": "她",
    "artigo": "这", "adjetivo": "强", "numeral": "七", "preposicao": "在",
    "conjuncao": "但是", "adverbio": "今天", "interjeicao": "啊", "pontuacao": "。",
    "modal": "—", "auxiliar": "—", "particula": "的/了/吗",
    "terminacao_honorifica": "—", "terminacao_nominal": "—",
    "terminacao_adjetival": "—", "terminacao_final": "—", "sufixo": "—",
}

DEF_PARTICULA_KO = (
    "Coreano: marca a função de uma palavra na frase. Conceito sem equivalente "
    "direto nos outros 4 idiomas."
)
DEF_PARTICULA_KO_ZH = (
    "Coreano e chinês: marca a função de uma palavra na frase. Conceito sem "
    "equivalente direto nos idiomas latinos. No chinês é a classe mais frequente "
    "da língua (o 的 sozinho é o caractere mais comum) — por isso o chinês "
    "reaproveita esta categoria em vez de precisar de uma cor própria."
)

VARIANTES = {
    "central-decisao-cores.html": {
        "com_chines": False,
        "idiomas": ["pt", "en", "es", "fr", "ko"],
        "eyebrow": "Legenda Multicor · 5 Idiomas · 20 classes",
        "titulo_html": "Painel de Classificação — Legenda Multicor (20 classes)",
        "nome_particula": "Partícula (coreano)",
        "def_particula": DEF_PARTICULA_KO,
        "origem_particula_stanza": [],
        "fallback_adverbio": "fallback (PART fora do EN, X, SYM, tag imprevista)",
        "nota": (
            "Versão de <b>5 idiomas</b> (pt/en/es/fr/ko). Para a de 6, com chinês, "
            "veja <code>central-decisao-cores-zh.html</code> — mesmas 20 classes e "
            "mesmas 21 cores, já que o chinês não precisou de nenhuma categoria nova."
        ),
    },
    "central-decisao-cores-zh.html": {
        "com_chines": True,
        "idiomas": ["pt", "en", "es", "fr", "ko", "zh"],
        "eyebrow": "Legenda Multicor · 6 Idiomas (com chinês) · 20 classes",
        "titulo_html": "Painel de Classificação — Legenda Multicor, 6 idiomas (20 classes)",
        "nome_particula": "Partícula (coreano/chinês)",
        "def_particula": DEF_PARTICULA_KO_ZH,
        "origem_particula_stanza": ["ZH: PART (的, 了, 吗, 着, 过...)"],
        "fallback_adverbio": "fallback (PART fora do EN/ZH, X, SYM, tag imprevista)",
        "nota": (
            "Versão de <b>6 idiomas</b>, com chinês (zh-Hans). Mesmas 20 classes e "
            "mesmas 21 cores da versão de 5 — o chinês <b>não precisou de categoria "
            "nova</b>: reaproveita as 14 genéricas + <code>particula</code>. As 6 "
            "exclusivas do coreano não se aplicam porque coreano é aglutinante "
            "(sufixos transformam a palavra) e chinês é isolante (palavras são "
            "blocos independentes)."
        ),
    },
}


def construir_dados(base: dict, v: dict) -> dict:
    d = json.loads(json.dumps(base))  # cópia profunda

    # ── cores/emoji das 20 classes: direto do cores.py ────────────────────
    d["cores"] = dict(cores.CORES_HTML)
    d["cores_texto"] = dict(cores.CORES_TEXTO)
    d["emoji"] = dict(cores.EMOJI_CLASSE)
    d["nomes_cor_oficial"] = dict(cores.NOMES_COR)
    d["paleta"] = {h: {"emoji": e, "nome": n} for h, (e, n) in cores.PALETA_EMOJI.items()}
    d["cor_reserva"] = cores.COR_RESERVA

    # ── exemplos por idioma ───────────────────────────────────────────────
    for classe, ex in d["exemplos"].items():
        if v["com_chines"]:
            ex["zh"] = EXEMPLOS_ZH.get(classe, "—")
        else:
            ex.pop("zh", None)

    # ── o que muda de texto entre as versões ──────────────────────────────
    d["nomes"]["particula"] = v["nome_particula"]
    d["explicacoes"]["particula"]["definicao"] = v["def_particula"]
    d["explicacoes"]["particula"]["origem"]["stanza"] = list(v["origem_particula_stanza"])
    d["explicacoes"]["adverbio"]["origem"]["stanza"] = [
        "ADV", "EN: PART “not”", v["fallback_adverbio"],
    ]
    d["nota_variante"] = v["nota"]

    # ── cores por idioma (vídeo multi-idioma cor única) ───────────────────
    cfg = PipelineConfig(NOME_ORACAO="x")
    d["cores_idiomas"] = [{
        "lang": l,
        "hex": cfg.CORES_IDIOMAS[l],
        "emoji": cores.emoji_por_cor(cfg.CORES_IDIOMAS[l]),
        "nome": cores.NOMES_IDIOMA_LEGENDA.get(l, l),
        "nome_cor": cores.PALETA_EMOJI[cfg.CORES_IDIOMAS[l]][1],
        "y": cfg.POSICOES_Y[l],
    } for l in sorted(v["idiomas"], key=lambda l: cfg.POSICOES_Y.get(l, 999))]

    assert set(d["cores"]) == set(d["explicacoes"]) == set(d["exemplos"]), \
        "classes divergiram entre cores/explicacoes/exemplos"
    return d


def gerar(nome_saida: str, v: dict, template: str) -> None:
    raw = template
    base = json.loads(re.search(r"const DADOS = (\{.*\});\n", raw).group(1))
    dados = construir_dados(base, v)

    raw = re.sub(
        r"const DADOS = \{.*\};\n",
        lambda _: "const DADOS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n",
        raw, count=1,
    )

    def troca(padrao_regex, novo):
        nonlocal raw
        novo_raw, n = re.subn(padrao_regex, lambda _: novo, raw, count=1)
        assert n == 1, f"nao casou: {padrao_regex}"
        raw = novo_raw

    troca(r"<title>[^<]*</title>", f"<title>{v['titulo_html']}</title>")
    troca(r'<p class="eyebrow">[^<]*</p>', f'<p class="eyebrow">{v["eyebrow"]}</p>')
    troca(r"const TODOS_IDIOMAS = \[[^\]]*\];",
          "const TODOS_IDIOMAS = " + json.dumps(v["idiomas"]) + ";")
    troca(r"const BANDEIRAS = \{[^}]*\};",
          "const BANDEIRAS = { " + ", ".join(f'{l}: "{l.upper()}"' for l in v["idiomas"]) + " };")
    # nota da variante, logo abaixo do parágrafo de abertura
    troca(r'(?s)(</p>\n  </header>)',
          f'</p>\n    <p class="lede" style="margin-top:12px">{v["nota"]}</p>\n  </header>')

    (ASSETS / nome_saida).write_text(raw, encoding="utf-8")
    print(f"  -> {nome_saida}  ({len(v['idiomas'])} idiomas)")


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    # tira uma nota de variante que já esteja no template, pra não acumular a
    # cada geração
    template = re.sub(r'\n    <p class="lede" style="margin-top:12px">.*?</p>', "",
                      template, count=1, flags=re.S)
    print("Gerando as centrais de cores a partir de cores.py:")
    for nome, v in VARIANTES.items():
        gerar(nome, v, template)
    print("OK")


if __name__ == "__main__":
    main()
