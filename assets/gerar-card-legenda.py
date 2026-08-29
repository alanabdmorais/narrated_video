#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar-card-legenda.py — O card de legenda que abre e fecha os vídeos poliglotas.

    python3 assets/gerar-card-legenda.py          # só o HTML
    python3 assets/gerar-card-legenda.py --png    # HTML + PNG 1920x1080

Saídas (assets/):
    card-legenda-cores.html          5 idiomas (pt/en/es/fr/ko) — as 2 telas
    card-legenda-cores-zh.html       6 idiomas (+ chinês)
    card-legenda-cores*-artifact.html  as mesmas, no formato do Artifact
    card_legenda_cores_1.png         tela 1 — 5 idiomas
    card_legenda_cores_2.png         tela 2 — 5 idiomas
    card_legenda_cores_zh_1.png      tela 1 — 6 idiomas
    card_legenda_cores_zh_2.png      tela 2 — 6 idiomas

Os PNG são o produto: entram na planilha de imagens e o pipeline os coloca no
começo e/ou no fim do vídeo. O HTML é pra conferir antes.

## Duas versões, como as centrais

Um vídeo de 5 idiomas não pode exibir uma coluna 中文 — o espectador procuraria
no vídeo uma cor que não está lá. Mesma razão de existirem duas centrais e
blocos separados na colinha: a legenda tem que descrever o vídeo que está
tocando, não o pipeline inteiro.

## Por que DUAS telas e não uma

São 20 classes. Numa tela só, cada linha fica com 45 px de altura num vídeo
1080p — ilegível no celular, que é onde a maior parte do público assiste. Em
duas, a linha dobra pra 85 px e a mesma tabela cabe confortável.

O corte não é arbitrário: as 10 primeiras cobrem **99,4%** das palavras de um
capítulo (medição em cores.ORDEM_FREQUENCIA). Quem só vir a tela 1 já consegue
ler o vídeo inteiro; a tela 2 é o resto — o que aparece uma vez a cada duzentas
palavras, e o que só existe em inglês, coreano e chinês.

## Por que quadradinho de cor, e não o emoji

O emoji é uma muleta da DESCRIÇÃO do YouTube, que é texto puro e não aceita
cor. Aqui é imagem: dá pra pintar o hexadecimal exato que a legenda usa no
vídeo. Emoji dependeria da fonte de quem renderiza e mostraria uma cor
aproximada — justamente o problema que o 🧶 causou.

A borda fininha em cada quadradinho existe pro branco e o cinza-claro não
sumirem no fundo claro.

## As colunas

    cor   |  english · português · español · français  |  한국어 · 中文

Latino e CJK separados porque o coreano e o chinês são curtos e os latinos são
longos: numa coluna só, as quatro terminações coreanas empurravam o 한국어 pra
fora da tela.

A largura da coluna latina não está escrita em lugar nenhum: é `max-content`,
então mede o nome mais longo DAQUELA tela e o CJK fica com o que sobra. Por
isso a tela 2, das terminações coreanas, sai naturalmente com a coluna latina
mais larga que a tela 1 — sem ninguém ajustar número quando um nome muda.

Uma fonte de verdade: cor, nome e ordem saem todos de
pipeline/modulos/cores.py, os mesmos que a descrição do YouTube usa.
"""
from __future__ import annotations

import html as _html
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pipeline" / "modulos"))

import cores  # noqa: E402

ASSETS = RAIZ / "assets"

LARGURA, ALTURA = 1920, 1080

#: Altura extra pedida ao Chromium na hora do print — ver gerar_pngs().
FOLGA_JANELA = 320

#: DUAS telas, sempre. Não é o resultado de 20/10 dar certo: é regra.
#: Três telas custariam mais tempo de vídeo do que a informação vale, e o
#: espectador que precisa procurar uma cor em três lugares desiste. Se um dia
#: entrar uma classe nova, ela divide 21 em 11+10 e o texto encolhe -- ver
#: `_metricas()`. É a altura da linha que cede, nunca o número de telas.
NUM_TELAS = 2

#: As dez classes cuja frequência foi realmente medida (Mateus 2, 3.127
#: palavras) e que somam 99,4%. O rodapé da tela 1 só promete os "99%" quando
#: a primeira metade é exatamente esta -- se a divisão mudar, o número deixa
#: de valer, e a alternativa a conferir é anunciar uma cobertura inventada.
DEZ_MEDIDAS = cores.ORDEM_FREQUENCIA[:10]

#: Referência de tamanho: as medidas do CSS foram desenhadas pra 10 linhas.
LINHAS_REFERENCIA = 10

#: Inglês primeiro — idioma anfitrião, mesma ordem da pilha na tela
#: (constants.POSICOES_Y) e da legenda na descrição do YouTube.
IDIOMAS_LATINOS = ("en", "pt", "es", "fr")

VARIANTES = {
    "card-legenda-cores.html": {
        "idiomas": ["en", "pt", "es", "fr", "ko"],
        "cjk": ("ko",),
        "sufixo_png": "",
    },
    "card-legenda-cores-zh.html": {
        "idiomas": ["en", "pt", "es", "fr", "ko", "zh"],
        "cjk": ("ko", "zh"),
        "sufixo_png": "_zh",
    },
}

TELAS = (
    {
        "n": 1,
        "selo": "mais frequentes · most frequent",
        "rodape": lambda v, fatia: (
            (f"Estas {len(fatia)} cobrem 99% das palavras.",
             f"These {len(fatia)} cover 99% of all words.")
            if tuple(fatia) == DEZ_MEDIDAS else
            ("As mais usadas — quase toda palavra do vídeo está aqui.",
             "The most used — nearly every word in the video is here.")),
    },
    {
        "n": 2,
        "selo": "menos frequentes · less frequent",
        # Os idiomas saem da variante: o card de 5 idiomas não pode prometer
        # uma classe exclusiva do chinês que aquele vídeo não tem.
        "rodape": lambda v, fatia: (
            f"O restante, e o que só existe em {_lista(v, 'e')}.",
            f"The rest, plus what only {_lista(v, 'and')} have."),
    },
)

#: "Legenda de cores" em cada idioma. Montado a partir dos idiomas da
#: variante, pelo mesmo motivo das colunas: um card de 5 idiomas com 颜色图例
#: no título anuncia um chinês que aquele vídeo não tem.
TITULO_IDIOMA = {
    "pt": "Legenda de cores", "en": "Colour key", "es": "Clave de colores",
    "fr": "Clé des couleurs", "ko": "색상 범례", "zh": "颜色图例",
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#e8e4dc;-webkit-font-smoothing:antialiased;
  font-family:Arial,'Liberation Sans','Helvetica Neue',Helvetica,
  'Noto Sans CJK KR','Noto Sans CJK SC',sans-serif}

/* A tela tem o tamanho exato do frame do vídeo. O print sai 1:1, sem
   reescala -- reescalar texto de 1080p é o que deixa legenda borrada. */
.tela{width:%(W)dpx;height:%(H)dpx;background:#faf8f4;color:#1c1a17;
  display:flex;flex-direction:column;padding:42px 74px 30px;overflow:hidden}

.cabeca{display:flex;align-items:baseline;gap:22px;padding-bottom:16px}
.cabeca h1{font-size:33px;font-weight:700;letter-spacing:-.01em;flex:1;
  white-space:nowrap}
.selo{font-size:20px;color:#7d746a;font-weight:500;white-space:nowrap}
.pagina{font-size:22px;font-weight:700;color:#faf8f4;background:#1c1a17;
  border-radius:999px;padding:5px 16px;white-space:nowrap}

/* Uma grade só pra tabela inteira, cabeçalho junto. Duas consequências que
   valem a estrutura:
     - `max-content` faz a coluna latina medir o nome mais longo DAQUELA tela,
       então a tela das terminações coreanas alarga sozinha;
     - `grid-auto-rows:1fr` divide a altura que sobra entre as linhas em
       partes iguais, sem ninguém contar quantas são -- 10, 11 ou 12, a
       tabela nunca transborda o frame, não importa quanto texto quebre.
   Sem column-gap: o respiro vem do padding das células, e assim a faixa
   escura do cabeçalho sai contínua em vez de listrada. */
.tabela{flex:1;display:grid;column-gap:0;
  grid-template-columns:150px max-content 1fr;
  grid-template-rows:auto;grid-auto-rows:1fr}

.ch{background:#1c1a17;color:#faf8f4;font-size:19px;font-weight:700;
  letter-spacing:.07em;text-transform:uppercase;padding:13px 28px 13px 0;
  align-self:stretch;display:flex;align-items:center}
.ch:first-child{padding-left:24px;border-radius:11px 0 0 11px}
.ch:last-child{border-radius:0 11px 11px 0;padding-right:24px}

.c{display:flex;align-items:center;border-bottom:1px solid #dedad1;
  padding:var(--padv) 28px var(--padv) 0;overflow:hidden}
.c:first-child{padding-left:24px}
/* última linha sem risco embaixo: risco encostado no rodapé vira ruído */
.tabela > .c:nth-last-child(-n+3){border-bottom:none}

/* Borda fina: sem ela o branco e o cinza-claro somem no fundo claro. */
.sw{width:112px;height:var(--swh);border-radius:8px;border:1px solid #00000038;
  box-shadow:inset 0 -1px 0 #00000012}

.latino{font-size:var(--lat);line-height:1.26;color:#242019}
.cjk{font-size:var(--cjk);line-height:1.28;color:#4d463d}

/* As duas metades do rodapé afastadas: com " · " entre elas, o separador se
   confundia com o " · " que separa os idiomas dentro da própria frase. */
.rodape{padding-top:16px;font-size:19px;color:#8a8177;text-align:center;
  display:flex;justify-content:center;gap:54px}
"""


def _titulo(v: dict) -> str:
    return cores.SEPARADOR_IDIOMA.join(
        TITULO_IDIOMA[l] for l in v["idiomas"] if l in TITULO_IDIOMA)


def _lista(v: dict, conjuncao: str) -> str:
    """"EN, KO e ZH" / "EN and KO" — os idiomas com classe exclusiva nesta
    variante, na sigla, que é o que cabe no rodapé."""
    siglas = [l.upper() for l in ("en", *v["cjk"])]
    return f"{', '.join(siglas[:-1])} {conjuncao} {siglas[-1]}"


def _nomes(classe: str, idiomas) -> str:
    tabela = cores.NOMES_CLASSE_IDIOMA[classe]
    return cores.SEPARADOR_IDIOMA.join(
        _html.escape(tabela[l]) for l in idiomas if l in tabela)


def _cabecalho(idiomas) -> str:
    """Cada idioma nomeado na própria língua — ver cores.NOMES_IDIOMA_NATIVO."""
    return cores.SEPARADOR_IDIOMA.join(
        _html.escape(cores.NOMES_IDIOMA_NATIVO[l]) for l in idiomas)


def _tela_html(tela: dict, classes: list[str], v: dict) -> str:
    celulas = []
    for classe in classes:
        celulas.append(
            f'      <div class="c"><div class="sw" '
            f'style="background:{cores.CORES_HTML[classe]}"></div></div>\n'
            f'      <div class="c latino">{_nomes(classe, IDIOMAS_LATINOS)}</div>\n'
            f'      <div class="c cjk">{_nomes(classe, v["cjk"])}</div>'
        )
    pt, en = tela["rodape"](v, classes)
    return f"""  <div class="tela" id="tela{tela['n']}" style="{_metricas(len(classes))}">
    <div class="cabeca">
      <h1>{_titulo(v)}</h1>
      <span class="selo">{tela['selo']}</span>
      <span class="pagina">{tela['n']} / {len(TELAS)}</span>
    </div>
    <div class="tabela">
      <div class="ch">cor</div>
      <div class="ch">{_cabecalho(IDIOMAS_LATINOS)}</div>
      <div class="ch">{_cabecalho(v["cjk"])}</div>
{chr(10).join(celulas)}
    </div>
    <div class="rodape"><span>{pt}</span><span>{en}</span></div>
  </div>"""


def _dividir(classes: list[str]) -> list[list[str]]:
    """Divide as classes em exatamente NUM_TELAS fatias, a maior primeiro.

    Ímpar não vira uma terceira tela: 21 sai 11+10. A tela mais cheia é a
    primeira de propósito -- é a das classes frequentes, a que o espectador
    realmente lê, e é onde os nomes latinos são mais curtos.
    """
    n = len(classes)
    base, sobra = divmod(n, NUM_TELAS)
    fatias, i = [], 0
    for k in range(NUM_TELAS):
        tam = base + (1 if k < sobra else 0)
        fatias.append(classes[i:i + tam])
        i += tam
    assert sum(len(f) for f in fatias) == n
    return fatias


def _metricas(linhas: int) -> str:
    """As medidas da tela, como `style` inline pra ela — ver o CSS.

    Vão como variável, e não numa folha de estilo por tela, porque as duas
    telas convivem na mesma página de conferência: variável no elemento cada
    uma leva a sua sem ninguém ter que escopar seletor.

    O CSS foi desenhado pra 10 linhas. Com mais que isso tudo encolhe na mesma
    proporção, em vez de a tabela transbordar ou virar uma terceira tela. Com
    menos, não cresce: linha gigante não fica mais legível, fica estranha.
    """
    e = min(1.0, LINHAS_REFERENCIA / linhas)
    return (f"--lat:{26 * e:.1f}px;--cjk:{27 * e:.1f}px;"
            f"--swh:{max(26, round(44 * e))}px;--padv:{max(3, round(6 * e))}px")


def montar(v: dict) -> tuple[str, list[str]]:
    """Devolve (html de conferência com as telas, [html de cada tela sozinha])."""
    ordem = [c for c in cores.ORDEM_FREQUENCIA
             if c in set(cores.classes_para_idiomas(v["idiomas"]))]
    fatias = _dividir(ordem)
    assert len(fatias) == len(TELAS), (
        f"{len(fatias)} fatias pra {len(TELAS)} telas descritas em TELAS")

    css = CSS % {"W": LARGURA, "H": ALTURA}
    partes, isoladas = [], []
    for tela, fatia in zip(TELAS, fatias):
        corpo = _tela_html(tela, fatia, v)
        partes.append(corpo)
        isoladas.append(_pagina(css, corpo, so_uma=True))

    # Página de conferência: cada tela vai dentro de uma moldura que a REDUZ
    # pra caber na janela. A tela em si continua com 1920x1080 exatos -- é o
    # tamanho do frame do vídeo, e mexer nele mudaria o que o PNG mostra. Quem
    # encolhe é a moldura, com transform, que não recalcula layout nenhum.
    css_folha = css + (
        "\n.folha{display:flex;flex-direction:column;align-items:center;"
        "gap:26px;padding:26px}"
        "\n.moldura{overflow:hidden}"
        "\n.moldura > .tela{transform-origin:top left}")
    corpo = ('<div class="folha">\n'
             + "\n".join(f'  <div class="moldura">\n{t}\n  </div>' for t in partes)
             + "\n</div>\n" + AJUSTE_JS)
    return _pagina(css_folha, corpo), isoladas


#: Só a página de conferência usa isto. A tela continua 1920x1080; a moldura
#: em volta encolhe pra caber na janela -- sem isso a página rolaria de lado
#: em qualquer tela menor que 1920, e o Artifact não deixa o corpo rolar
#: horizontalmente.
AJUSTE_JS = """<script>
(function () {
  function ajustar() {
    var f = Math.min(1, (document.documentElement.clientWidth - 52) / %d);
    document.querySelectorAll('.moldura').forEach(function (m) {
      var t = m.querySelector('.tela');
      t.style.transform = 'scale(' + f + ')';
      m.style.width = (%d * f) + 'px';
      m.style.height = (%d * f) + 'px';
    });
  }
  addEventListener('resize', ajustar);
  ajustar();
})();
</script>""" % (LARGURA, LARGURA, ALTURA)


def _pagina(css: str, corpo: str, so_uma: bool = False) -> str:
    margem = "body{margin:0}" if so_uma else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Card de Legenda Poliglota</title>
<style>{css}{margem}</style>
</head>
<body>
{corpo}
</body>
</html>
"""


def para_artifact(html: str) -> str:
    """Mesma conversão do gerar-central-cores.py: o Artifact monta o esqueleto,
    então o arquivo publica só título, estilo e corpo."""
    for tag in ("<!DOCTYPE html>", "</head>", "<body>", "</body>", "</html>"):
        html = html.replace(tag, "")
    html = re.sub(r'<html[^>]*>|<head>|<meta[^>]*>', "", html)
    return re.sub(r"\n{3,}", "\n\n", html).strip() + "\n"


def _chromium() -> str | None:
    achados = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    return str(achados[-1]) if achados else None


def gerar_pngs(isoladas: list[str], sufixo: str) -> None:
    """Renderiza cada tela em PNG 1920x1080 pelo Chromium headless.

    Print à mão também funciona, mas depende do tamanho da janela e do zoom do
    navegador. Aqui o tamanho é argumento, então o PNG sai sempre exatamente no
    frame do vídeo.

    ## Por que renderiza grande e depois corta

    No headless, `--window-size` é a JANELA, não a área da página: a página
    recebe ~87 px a menos, e esse desconto muda com a versão do Chromium.
    Pedir 1920x1080 direto entrega uma imagem de 1080 px com só 993 px de
    página dentro — o rodapé sai cortado, calado, e nada avisa.

    Então renderiza com folga (a página inteira cabe, sobra fundo embaixo) e
    corta os 1920x1080 do canto superior esquerdo, que é a tela. A folga de
    320 px absorve qualquer desconto de versão futura.
    """
    chrome = _chromium()
    if not chrome:
        print("  !! Chromium não encontrado — só o HTML foi gerado.")
        return
    if not shutil.which("ffmpeg"):
        print("  !! ffmpeg não encontrado — só o HTML foi gerado.")
        return

    for i, pagina in enumerate(isoladas, start=1):
        tmp_html = ASSETS / f".card_tela{sufixo}_{i}.html"
        tmp_png = ASSETS / f".card_tela{sufixo}_{i}.png"
        saida = ASSETS / f"card_legenda_cores{sufixo}_{i}.png"
        tmp_html.write_text(pagina, encoding="utf-8")
        subprocess.run([
            chrome, "--headless", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--window-size={LARGURA},{ALTURA + FOLGA_JANELA}",
            f"--screenshot={tmp_png}", tmp_html.as_uri(),
        ], check=True, capture_output=True)
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp_png),
            "-vf", f"crop={LARGURA}:{ALTURA}:0:0", str(saida),
        ], check=True, capture_output=True)
        tmp_html.unlink()
        tmp_png.unlink()
        print(f"  -> {saida.name}  ({saida.stat().st_size/1024:.0f} KB)")


def main() -> None:
    com_png = "--png" in sys.argv
    for nome, v in VARIANTES.items():
        print(f"{len(v['idiomas'])} idiomas:")
        pagina, isoladas = montar(v)
        (ASSETS / nome).write_text(pagina, encoding="utf-8")
        print(f"  -> {nome}  (as 2 telas, pra conferir)")
        nome_art = nome.replace(".html", "-artifact.html")
        (ASSETS / nome_art).write_text(para_artifact(pagina), encoding="utf-8")
        print(f"  -> {nome_art}")
        if com_png:
            gerar_pngs(isoladas, v["sufixo_png"])
    if not com_png:
        print("(sem --png: rode com --png pra gerar as imagens 1920x1080)")
    print("OK")


if __name__ == "__main__":
    main()
