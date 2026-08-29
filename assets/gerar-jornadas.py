#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar-jornadas.py — Escreve o `pipeline/JORNADAS.md` a partir do jornadas.py.

    python3 assets/gerar-jornadas.py

Mesmo arranjo das centrais de cor: o dado mora num módulo (`jornadas.py`, que
também sabe se conferir contra a pasta de notebooks) e o documento é gerado.
Um mapa escrito à mão e um `verificar_repo()` que confere outra coisa seriam
duas verdades, e a que envelhece calada é sempre a escrita à mão.

Por que dois formatos do mesmo mapa:

    JORNADAS.md      pra ler no repositório, ao lado do código
    JORNADAS-artifact.html  pra publicar e abrir no celular, sem clonar nada
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pipeline" / "modulos"))

import jornadas as J  # noqa: E402

SAIDA_MD = RAIZ / "pipeline" / "JORNADAS.md"
SAIDA_HTML = RAIZ / "assets" / "jornadas-artifact.html"

CABECA = """# Jornadas — o que rodar pra conseguir o quê

> ⚠️ **Gerado por `assets/gerar-jornadas.py` a partir de
> `pipeline/modulos/jornadas.py`.** Não edite este arquivo à mão: mexa no
> módulo e rode o script. O módulo também se confere contra a pasta de
> notebooks (`python3 pipeline/modulos/jornadas.py`), então notebook novo que
> ninguém encaixou numa jornada é acusado em vez de sumir do mapa.

São %(n_nb)d notebooks. A pergunta que se faz na prática nunca é "o que este
notebook faz?" — é a inversa: **"eu quero um resultado assim; o que eu rodo?"**
Este documento responde essa.

Referência de nomes de arquivo, parâmetros e planilhas: `CONFIGURACAO.md`.
Aqui é só o caminho.

## Os três tipos

| Tipo | Frequência |
|---|---|
| **preparo** | uma vez na vida do projeto, ou quando o estoque cresce |
| **vídeo** | uma vez por vídeo |
| **apoio** | quando você quiser; não produz vídeo |

## O que os quatro níveis de vídeo NÃO são

Os quatro níveis (`_video_base` → `_final` → `_final_idiomas` →
`_final_multicolor`) **não são uma cadeia de arquivos**. Os três notebooks de
burn leem todos o mesmo `NOME_VIDEO_BASE`: nenhum queima em cima do mp4 do
nível anterior. Consequências práticas:

- dá pra ir direto ao nível 3 sem nunca gerar o vídeo do nível 1;
- os quatro mp4 convivem na mesma pasta, e nenhum invalida o outro;
- **o que encadeia de verdade são os SRT, não os mp4.** O nível 2 precisa do
  SRT mestre que o `caption-single-generate` produz; o nível 3 precisa dos SRT
  por idioma que o `caption-multilang-generate` produz.

Por isso, abaixo, "depende de" aponta pra jornada cujo **arquivo** é
pré-requisito — não pro "nível de baixo".
"""

RODAPE = """
## Conferir o mapa

```
python3 pipeline/modulos/jornadas.py
```

Acusa três coisas que fariam este documento mentir:

| Achado | Significa |
|---|---|
| `[órfão]` | notebook novo na pasta que nenhuma jornada cita |
| `[fantasma]` | jornada citando notebook que foi renomeado ou apagado |
| `[dependência]` | `depende_de` apontando pra jornada que não existe |

## Perguntar ao mapa, em vez de ler

```python
import jornadas as J

J.caminho_ate("multicolor")          # tudo que precisa acontecer antes, em ordem
J.jornadas_de("caption-single-generate")   # em que jornadas este notebook entra
J.por_id("compilacao").armadilha     # o erro que essa jornada costuma provocar
```
"""


def _mermaid() -> str:
    """Grafo das dependências entre jornadas. O GitHub renderiza ```mermaid."""
    forma = {J.PREPARO: ("[", "]"), J.VIDEO: ("(", ")"), J.APOIO: ("{{", "}}")}
    linhas = ["```mermaid", "flowchart LR"]
    for j in J.JORNADAS:
        a, b = forma[j.tipo]
        linhas.append(f'  {j.id.replace("-", "_")}{a}"{j.id}"{b}')
    for j in J.JORNADAS:
        for dep in j.depende_de:
            linhas.append(f'  {dep.replace("-", "_")} --> {j.id.replace("-", "_")}')
    linhas.append("```")
    linhas.append("")
    linhas.append("`[preparo]` · `(vídeo)` · `{apoio}` — a seta é "
                  "\"precisa do arquivo que aquela produz\".")
    return "\n".join(linhas)


def _jornada_md(j: J.Jornada) -> str:
    partes = [f"### `{j.id}` — {j.titulo}", ""]
    partes.append(f"**Tipo** {j.tipo} · **Quando** {j.quando}")
    partes.append("")
    partes.append(f"**Entrega** {j.entrega}")
    if j.depende_de:
        deps = ", ".join(f"`{d}`" for d in j.depende_de)
        partes.append("")
        partes.append(f"**Depende de** {deps}")
    if j.custo:
        partes.append("")
        partes.append(f"**Custo** {j.custo}")
    partes.append("")
    partes.append("| # | Notebook | Produz |")
    partes.append("|---|---|---|")
    for i, p in enumerate(j.passos, start=1):
        nomes = "<br>".join(
            (f"ou `{n}`" if k else f"`{n}`") for k, n in enumerate(p.notebooks))
        celula = nomes + (f"<br>{p.nota}" if p.nota else "")
        partes.append(f"| {i} | {celula} | {p.produz} |")
    if j.armadilha:
        partes.append("")
        partes.append(f"> ⚠️ {j.armadilha}")
    return "\n".join(partes)


def markdown() -> str:
    n_nb = len({n for j in J.JORNADAS for n in j.notebooks}) + len(J.EXCECOES)
    blocos = [CABECA % {"n_nb": n_nb}, "## O mapa", "", _mermaid(), ""]

    for tipo, titulo in ((J.PREPARO, "Preparo — uma vez, ou quando o estoque cresce"),
                         (J.VIDEO, "Vídeo — uma vez por vídeo"),
                         (J.APOIO, "Apoio")):
        blocos.append(f"## {titulo}")
        blocos.append("")
        for j in (x for x in J.JORNADAS if x.tipo == tipo):
            blocos.append(_jornada_md(j))
            blocos.append("")

    blocos.append("## Notebook fora de qualquer jornada")
    blocos.append("")
    blocos.append("| Notebook | Por que fica fora |")
    blocos.append("|---|---|")
    for nb, motivo in sorted(J.EXCECOES.items()):
        blocos.append(f"| `{nb}` | {motivo} |")
    blocos.append(RODAPE)
    return "\n".join(blocos).rstrip() + "\n"


# ── Versão publicável ────────────────────────────────────────────────────────

CSS = """
:root{--bg:#191510;--surface:#24201a;--surface-2:#2e2820;--line:#3a3327;
  --text:#ede3d1;--muted:#9c917d;--accent:#c99b4a;--ok:#5a8f6f;--warn:#c98a4a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);line-height:1.55;
  font-family:'IBM Plex Sans',system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px 90px}
header{padding:46px 0 22px;border-bottom:1px solid var(--line)}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--accent);margin:0 0 12px}
h1{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(27px,4.5vw,40px);
  line-height:1.1;margin:0 0 14px}
p.lede{max-width:680px;color:var(--muted);font-size:15px;margin:0 0 10px}
h2{font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:44px 0 4px;
  padding-bottom:9px;border-bottom:1px solid var(--line)}
h3{font-size:15.5px;font-weight:600;margin:0 0 10px}
code{font-family:'IBM Plex Mono',monospace;background:var(--surface-2);
  padding:1px 5px;border-radius:4px;font-size:.9em}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 6px}
.chip{font-family:'IBM Plex Mono',monospace;font-size:12px;padding:5px 11px;
  border:1px solid var(--line);border-radius:999px;color:var(--muted);
  background:var(--surface);cursor:pointer}
.chip.ativo{border-color:var(--accent);color:var(--accent)}
.j{border:1px solid var(--line);border-radius:11px;background:var(--surface);
  margin-top:14px;overflow:hidden}
.j.oculta{display:none}
.j-cab{padding:14px 20px;background:var(--surface-2);border-bottom:1px solid var(--line)}
.j-id{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--accent)}
.j-corpo{padding:15px 20px;display:flex;flex-direction:column;gap:11px}
.linha{display:flex;gap:10px;font-size:13.5px;flex-wrap:wrap}
.rot{font-family:'IBM Plex Mono',monospace;font-size:11px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);min-width:88px;flex-shrink:0;padding-top:2px}
.val{flex:1;min-width:220px;color:var(--text)}
ol.passos{margin:2px 0 0;padding-left:0;list-style:none;counter-reset:p}
ol.passos li{counter-increment:p;display:flex;gap:12px;padding:9px 0;
  border-top:1px solid var(--line)}
ol.passos li::before{content:counter(p);font-family:'IBM Plex Mono',monospace;
  font-size:11px;color:var(--accent);border:1px solid var(--line);border-radius:50%;
  width:22px;height:22px;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;margin-top:2px}
.passo-nb{font-family:'IBM Plex Mono',monospace;font-size:12.5px}
.passo-produz{color:var(--muted);font-size:12.5px;margin-top:3px}
.passo-nota{color:var(--muted);font-size:12.5px;margin-top:5px;font-style:italic}
.armadilha{border-left:3px solid var(--warn);background:rgba(201,138,74,.08);
  padding:10px 14px;border-radius:0 7px 7px 0;font-size:13px;color:var(--text)}
.deps{display:flex;gap:6px;flex-wrap:wrap}
.dep{font-family:'IBM Plex Mono',monospace;font-size:11.5px;padding:2px 8px;
  border:1px solid var(--line);border-radius:5px;color:var(--muted)}
pre.mermaid{background:var(--surface);border:1px solid var(--line);border-radius:11px;
  padding:18px;overflow-x:auto;margin:16px 0 0}
.aviso{border-left:3px solid var(--accent);background:rgba(201,155,74,.08);
  padding:12px 16px;border-radius:0 7px 7px 0;font-size:13.5px;margin-top:18px}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12px;font-family:'IBM Plex Mono',monospace}
table.simples{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}
table.simples th,table.simples td{text-align:left;padding:8px 12px;
  border-bottom:1px solid var(--line);vertical-align:top}
table.simples th{font-family:'IBM Plex Mono',monospace;font-size:11px;
  text-transform:uppercase;color:var(--muted);letter-spacing:.06em}
"""


def _j_html(j: J.Jornada) -> str:
    e = html.escape
    passos = []
    for p in j.passos:
        nbs = "<br>".join(
            (f"ou <code>{e(n)}</code>" if i else f"<code>{e(n)}</code>")
            for i, n in enumerate(p.notebooks))
        nota = f'<div class="passo-nota">{e(p.nota)}</div>' if p.nota else ""
        passos.append(f'<li><div><div class="passo-nb">{nbs}</div>'
                      f'<div class="passo-produz">→ {e(p.produz)}</div>{nota}</div></li>')
    deps = ""
    if j.depende_de:
        chips = "".join(f'<span class="dep">{e(d)}</span>' for d in j.depende_de)
        deps = f'<div class="linha"><div class="rot">depende de</div>' \
               f'<div class="val deps">{chips}</div></div>'
    custo = (f'<div class="linha"><div class="rot">custo</div>'
             f'<div class="val">{e(j.custo)}</div></div>') if j.custo else ""
    arm = f'<div class="armadilha">⚠️ {e(j.armadilha)}</div>' if j.armadilha else ""
    return f"""      <article class="j" data-tipo="{e(j.tipo)}">
        <div class="j-cab">
          <div class="j-id">{e(j.id)}</div>
          <h3>{e(j.titulo)}</h3>
        </div>
        <div class="j-corpo">
          <div class="linha"><div class="rot">quando</div><div class="val">{e(j.quando)}</div></div>
          <div class="linha"><div class="rot">entrega</div><div class="val">{e(j.entrega)}</div></div>
{deps}{custo}
          <ol class="passos">
{chr(10).join(passos)}
          </ol>
{arm}
        </div>
      </article>"""


def pagina_html() -> str:
    n_nb = len({n for j in J.JORNADAS for n in j.notebooks}) + len(J.EXCECOES)
    excecoes = "".join(
        f"<tr><td><code>{html.escape(nb)}</code></td><td>{html.escape(m)}</td></tr>"
        for nb, m in sorted(J.EXCECOES.items()))
    mermaid = _mermaid().replace("```mermaid\n", "").rsplit("```", 1)[0]
    return f"""<title>Jornadas do Pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>

<div class="wrap">
  <header>
    <p class="eyebrow">narrated_video · mapa de jornadas</p>
    <h1>O que rodar pra conseguir o quê</h1>
    <p class="lede">São {n_nb} notebooks. A pergunta que se faz na prática nunca é
      "o que este notebook faz?" — é a inversa: <b>eu quero um resultado assim,
      o que eu rodo?</b> Este mapa responde essa.</p>
    <p class="lede">Gerado de <code>pipeline/modulos/jornadas.py</code>, que se
      confere sozinho contra a pasta de notebooks — notebook novo que ninguém
      encaixou numa jornada é acusado, não some do mapa.</p>
  </header>

  <h2>O mapa</h2>
  <pre class="mermaid">{html.escape(mermaid.strip())}</pre>

  <div class="aviso"><b>Os quatro níveis de vídeo não são uma cadeia de
    arquivos.</b> Os três notebooks de burn leem todos o mesmo
    <code>NOME_VIDEO_BASE</code> — nenhum queima em cima do mp4 do nível
    anterior. Dá pra ir direto ao nível 3 sem nunca gerar o vídeo do nível 1, e
    os quatro mp4 convivem na mesma pasta. O que encadeia de verdade são os
    <b>SRT</b>, não os mp4 — por isso "depende de" aponta pra jornada cujo
    arquivo é pré-requisito, não pro nível de baixo.</div>

  <div class="chips" id="chips">
    <span class="chip ativo" data-f="todos">todas ({len(J.JORNADAS)})</span>
    <span class="chip" data-f="preparo">preparo</span>
    <span class="chip" data-f="vídeo">vídeo</span>
    <span class="chip" data-f="apoio">apoio</span>
  </div>

  <div id="lista">
{chr(10).join(_j_html(j) for j in J.JORNADAS)}
  </div>

  <h2>Notebook fora de qualquer jornada</h2>
  <table class="simples">
    <tr><th>Notebook</th><th>Por que fica fora</th></tr>
    {excecoes}
  </table>

  <h2>Conferir o mapa</h2>
  <table class="simples">
    <tr><th>Achado</th><th>Significa</th></tr>
    <tr><td><code>[órfão]</code></td><td>notebook novo na pasta que nenhuma jornada cita</td></tr>
    <tr><td><code>[fantasma]</code></td><td>jornada citando notebook renomeado ou apagado</td></tr>
    <tr><td><code>[dependência]</code></td><td><code>depende_de</code> apontando pra jornada que não existe</td></tr>
  </table>

  <footer>Gerado por <code>assets/gerar-jornadas.py</code> a partir de
    <code>pipeline/modulos/jornadas.py</code>. Referência de nomes de arquivo e
    parâmetros: <code>pipeline/CONFIGURACAO.md</code>.</footer>
</div>

<script>
document.getElementById('chips').addEventListener('click', function (e) {{
  var chip = e.target.closest('.chip');
  if (!chip) return;
  document.querySelectorAll('.chip').forEach(function (c) {{ c.classList.remove('ativo'); }});
  chip.classList.add('ativo');
  var f = chip.dataset.f;
  document.querySelectorAll('.j').forEach(function (j) {{
    j.classList.toggle('oculta', f !== 'todos' && j.dataset.tipo !== f);
  }});
}});
</script>
"""


def main() -> None:
    problemas = J.verificar_repo(RAIZ)
    if problemas:
        print("⚠️  o mapa não bate com a pasta — conserte antes de gerar:")
        for p in problemas:
            print("  ", p)
        raise SystemExit(1)

    SAIDA_MD.write_text(markdown(), encoding="utf-8")
    print(f"  -> {SAIDA_MD.relative_to(RAIZ)}  "
          f"({len(J.JORNADAS)} jornadas, {len(markdown().splitlines())} linhas)")
    SAIDA_HTML.write_text(pagina_html(), encoding="utf-8")
    print(f"  -> {SAIDA_HTML.relative_to(RAIZ)}  (mesma coisa, formato Artifact)")
    print("OK")


if __name__ == "__main__":
    main()
