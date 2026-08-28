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


# ── Colinha pra descrição do YouTube ──────────────────────────────────────────
# Blocos prontos pra copiar, um por tipo de vídeo. Gerada do mesmo cores.py que
# as centrais -- é o ponto de gerar em vez de escrever à mão: mexeu na cor ou no
# emoji, roda o script e a colinha acompanha, sem chance de ficar desatualizada.
COLINHA_BLOCOS = [
    ("Multi-idioma cor única — 6 idiomas (com chinês)", "idiomas",
     ["pt", "en", "es", "fr", "ko", "zh"]),
    ("Multi-idioma cor única — 5 idiomas", "idiomas",
     ["pt", "en", "es", "fr", "ko"]),
    ("Multicolor — 6 idiomas (com chinês)", "classes",
     ["pt", "en", "es", "fr", "ko", "zh"]),
    ("Multicolor — 5 idiomas", "classes",
     ["pt", "en", "es", "fr", "ko"]),
    ("Multicolor — sem coreano (pt/en/es/fr)", "classes",
     ["pt", "en", "es", "fr"]),
    ("Multicolor — só latinos (pt/es/fr)", "classes",
     ["pt", "es", "fr"]),
]

COLINHA_CSS = """
  :root { --bg:#191510; --surface:#24201a; --surface-2:#2e2820; --line:#3a3327;
    --text:#ede3d1; --text-muted:#9c917d; --accent:#c99b4a; --ok:#5a8f6f; }
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);
    font-family:'IBM Plex Sans',sans-serif;line-height:1.5}
  .wrap{max-width:820px;margin:0 auto;padding:0 24px 80px}
  header{padding:44px 0 24px;border-bottom:1px solid var(--line)}
  .eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.12em;
    text-transform:uppercase;color:var(--accent);margin:0 0 12px}
  h1{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(26px,4.5vw,38px);
    line-height:1.1;margin:0 0 14px}
  p.lede{max-width:660px;color:var(--text-muted);font-size:15px;margin:0}
  .bloco{margin-top:34px;border:1px solid var(--line);border-radius:10px;
    background:var(--surface);overflow:hidden}
  .bloco-cab{display:flex;align-items:center;gap:12px;padding:12px 18px;
    background:var(--surface-2);border-bottom:1px solid var(--line);flex-wrap:wrap}
  .bloco-cab h2{margin:0;font-size:14.5px;font-weight:600;flex:1;min-width:200px}
  .qtd{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--text-muted)}
  .btn{padding:7px 16px;background:var(--accent);color:#191510;border:none;
    border-radius:6px;font-family:'IBM Plex Sans';font-weight:600;font-size:12.5px;cursor:pointer}
  .btn.ok{background:var(--ok);color:#fff}
  pre{margin:0;padding:16px 18px;font-family:'IBM Plex Mono',monospace;font-size:13.5px;
    line-height:1.7;white-space:pre-wrap;overflow-x:auto}
  footer{margin-top:50px;padding-top:18px;border-top:1px solid var(--line);
    color:var(--text-muted);font-size:12px;font-family:'IBM Plex Mono',monospace}
  code{background:var(--surface-2);padding:1px 5px;border-radius:4px;font-size:.92em}
"""


def gerar_colinha(nome_saida: str) -> None:
    blocos_html = []
    for titulo, tipo, idiomas in COLINHA_BLOCOS:
        if tipo == "idiomas":
            cfg = PipelineConfig(NOME_ORACAO="x")
            ordem = sorted(idiomas, key=lambda l: cfg.POSICOES_Y.get(l, 999))
            texto = cores.legenda_youtube_idiomas(cfg.CORES_IDIOMAS, ordem)
            qtd = f"{len(ordem)} idiomas · na ordem da tela"
        else:
            classes = cores.classes_para_idiomas(idiomas)
            texto = cores.legenda_youtube(classes, idiomas)
            qtd = f"{len(classes)} classes"
        blocos_html.append(f"""  <section class="bloco">
    <div class="bloco-cab">
      <h2>{titulo}</h2>
      <span class="qtd">{qtd}</span>
      <button class="btn" data-copiar>Copiar</button>
    </div>
    <pre>{texto}</pre>
  </section>""")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Colinha — legenda de cores pra descrição do YouTube</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{COLINHA_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow">Colinha · descrição do YouTube</p>
    <h1>Legenda de cores pra colar na descrição</h1>
    <p class="lede">Clique em <b>Copiar</b> no bloco do tipo de vídeo e cole na descrição.
      Cada linha é o emoji da cor + o que ela significa naquele vídeo. Escolha o bloco pelos
      idiomas que o vídeo realmente tem — um vídeo sem coreano não deve listar as terminações
      coreanas, e um só com idiomas latinos não tem as partículas do inglês.</p>
  </header>
{chr(10).join(blocos_html)}
  <footer>Gerada por <code>assets/gerar-central-cores.py</code> a partir de
    <code>pipeline/modulos/cores.py</code> — mexeu na cor ou no emoji, rode o script de novo
    e esta colinha acompanha junto com as centrais.</footer>
</div>
<script>
document.querySelectorAll('[data-copiar]').forEach(btn => {{
  btn.addEventListener('click', async () => {{
    const texto = btn.closest('.bloco').querySelector('pre').textContent;
    try {{
      await navigator.clipboard.writeText(texto);
    }} catch (e) {{
      // fallback pra quando a área de transferência é bloqueada (file://, etc.)
      const ta = document.createElement('textarea');
      ta.value = texto; document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove();
    }}
    const antes = btn.textContent;
    btn.textContent = 'Copiado ✓'; btn.classList.add('ok');
    setTimeout(() => {{ btn.textContent = antes; btn.classList.remove('ok'); }}, 1600);
  }});
}});
</script>
</body>
</html>
"""
    (ASSETS / nome_saida).write_text(html, encoding="utf-8")
    print(f"  -> {nome_saida}  ({len(COLINHA_BLOCOS)} blocos)")


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    # tira uma nota de variante que já esteja no template, pra não acumular a
    # cada geração
    template = re.sub(r'\n    <p class="lede" style="margin-top:12px">.*?</p>', "",
                      template, count=1, flags=re.S)
    print("Gerando as centrais de cores a partir de cores.py:")
    for nome, v in VARIANTES.items():
        gerar(nome, v, template)
    print("Gerando a colinha da descrição do YouTube:")
    gerar_colinha("colinha-emojis-youtube.html")
    print("OK")


if __name__ == "__main__":
    main()
