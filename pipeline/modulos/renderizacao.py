# -*- coding: utf-8 -*-
"""
renderizacao.py — Geração de legenda ASS com a classificação nova
(núcleo compartilhado + extensões EN/KO).

Adaptado de ffmpeg_utils.gerar_ass() do sistema antigo — MESMA técnica de
caixa colorida (texto preto/branco por contraste + borda grossa com a cor
da classe), só com duas correções necessárias pro nosso caso:

  1. _escapar() do sistema antigo remove acentos e caracteres não-ASCII
     (normalização NFD + encode ascii) — destruiria o texto coreano por
     completo e degradaria acentos de PT/FR. Aqui só escapamos os
     caracteres que o formato ASS exige (chaves, barra invertida).

  2. O coreano tem PEDAÇOS dentro da mesma palavra escrita (sem espaço
     entre eles) — a função antiga sempre bota espaço depois de cada
     "palavra". Aqui cada item pode marcar `colado_anterior=True` pra
     não ter espaço antes dele (usado só nos pedaços 2+ de uma palavra
     coreana).

Não modifica nenhum arquivo do sistema antigo — é um módulo novo, próprio
pro notebook novo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple, Optional

from config import PipelineConfig
from cores import cor_html as cor_html_classe


class PecaColorida(NamedTuple):
    """Um pedaço de texto com sua classe gramatical, pronto pra renderizar.
    `colado_anterior=True` = sem espaço antes desse pedaço (só pro coreano,
    pedaços 2+ da mesma palavra escrita).

    `upos`, `lema` e `feats` são a análise CRUA (Stanza: PROPN, ADP, SCONJ...
    e "VerbForm=Inf|Number=Sing"; Kiwi: NNP, JKS, EF...). Não entram na cor.
    Servem a duas coisas:

      - a revisão distingue "o analisador errou" de "a regra mapeou errado",
        que se consertam em lugares diferentes;
      - a central de correções (revisao_classes) casa as regras contra eles,
        e é o que deixa a regra ver o CONTEXTO: "a" vira preposição quando o
        que vem depois é VERB com VerbForm=Inf.

    Vêm do bruto (analise.py) e ficam repetidos aqui de propósito: com eles a
    classificação salva basta pra reaplicar as regras, sem precisar abrir o
    arquivo do bruto. Custam uns 30% do JSON, que já era o menor arquivo da
    pasta. Opcionais: ficam "" em classificação salva antes disto.

    `classe_automatica` é a classe que as REGRAS produziram. Quando ela
    difere de `classe`, a diferença é humana: alguém trocou na revisão. É só
    por causa dela que dá pra refazer a classificação com regra nova sem
    apagar correção manual -- antes disto, o arquivo não sabia distinguir uma
    coisa da outra, e por isso o reaproveitamento tinha que ser cego.
    """
    texto: str
    classe: str
    colado_anterior: bool = False
    upos: str = ""
    lema: str = ""
    feats: str = ""
    classe_automatica: str = ""


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {largura}
PlayResY: {altura}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{tamanho_fonte},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
_LINHA_DIALOGO = "Dialogue: 0,{inicio},{fim},Default,,0,0,0,,{texto}\n"


def _ms_para_ass(ms: int) -> str:
    h  = ms // 3_600_000
    m  = (ms % 3_600_000) // 60_000
    s  = (ms % 60_000) // 1_000
    cc = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cc:02d}"


def _escapar(texto: str) -> str:
    """Escapa só o que o ASS exige (chave, barra invertida) — preserva
    acentos e qualquer script (coreano incluído)."""
    return texto.replace("\\", "").replace("{", "").replace("}", "")


def _html_para_ass_cor(html_hex: str) -> str:
    h = html_hex.replace("#", "").upper().zfill(6)
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}"


def _texto_visivel(pecas: list[PecaColorida], espaco_colado: str) -> str:
    """O que o espectador lê nesta linha, com os separadores que vão pra tela.
    É isto que se mede pra saber se a linha cabe entre as margens."""
    partes = []
    for peca in pecas:
        if not peca.texto.strip():
            continue
        partes.append((espaco_colado if peca.colado_anterior else " ") + peca.texto)
    return "".join(partes).strip()


def _linha_colorida_ass(pecas: list[PecaColorida], box_border: int, tamanho_fonte: int,
                          x: int, y: int, fonte_tag: str = "", escala: int = 100,
                          espaco_colado: str = "\u2009") -> str:
    """Monta a string de conteúdo ASS (com as tags override) pra uma linha
    inteira de pedaços coloridos — mesma técnica do sistema antigo: \\1c
    (texto, preto/branco por contraste) + \\3c (borda grossa = cor da
    classe, simula caixa preenchida).

    `espaco_colado` é PARÂMETRO, não global: já foi global por engano entre
    668734d e hoje, e o defeito ficou escondido porque o `if` não avalia o
    ramo quando a peça não é colada -- e peça colada só existe em coreano.
    Nenhum dos cinco idiomas latinos exercitava a linha.

    `fonte_tag` (ex: "\\\\fnNoto Sans CJK KR") — usado pros idiomas CJK
    (coreano e chinês, ver config.fonte_cjk), cuja fonte padrão (Arial) não
    tem os caracteres Hangul/Han e mostraria quadradinhos (□) no lugar do
    texto."""
    # A borda encolhe junto: o \\fscx do fim desta função encolhe os GLIFOS,
    # mas não o \\bord -- sem isto, a linha encolhida sai com caixas
    # proporcionalmente mais gordas que as das outras linhas.
    borda = max(1, round(box_border * escala / 100))
    partes: list[str] = []
    for peca in pecas:
        texto_safe = _escapar(peca.texto)
        if not texto_safe.strip():
            continue
        cor_html = cor_html_classe(peca.classe)
        cor_fundo = _html_para_ass_cor(cor_html)
        r, g, b = int(cor_html[1:3], 16), int(cor_html[3:5], 16), int(cor_html[5:7], 16)
        luminancia = 0.299 * r + 0.587 * g + 0.114 * b
        cor_texto = "&H00000000" if luminancia > 128 else "&H00FFFFFF"

        # Peça colada é morfema dentro da MESMA palavra escrita (só coreano):
        # separar com espaço normal quebraria a palavra. Mas juntar com nada
        # faz as bordas coloridas de 6px encostarem, e as sílabas saem
        # espremidas -- foi o que apareceu na primeira queima. Um espaço fino
        # (U+2009) dá folga pras caixas sem abrir a palavra.
        #
        # Se a fonte não tiver o glifo e aparecer um quadrado, troque por ""
        # e reduza o box_border: o problema é a borda, o espaço só a compensa.
        espaco_antes = espaco_colado if peca.colado_anterior else " "
        partes.append(
            f"{espaco_antes}{{\\1c{cor_texto}\\3c{cor_fundo}\\bord{borda}\\shad0{fonte_tag}}}{texto_safe}"
        )

    texto_combinado = "".join(partes).strip()
    # \fscx/\fscy valem daqui até o fim da linha: as tags de cor que vêm
    # depois não os reinicializam.
    ajuste = f"\\fscx{escala}\\fscy{escala}" if escala != 100 else ""
    return f"{{\\an2\\pos({x},{y})\\fs{tamanho_fonte}{ajuste}}}{texto_combinado}"


# ── Quanto uma linha ocupa na tela ───────────────────────────────────────────
# Avanço de cada caractere no Arial, em múltiplos do tamanho da fonte. Extraído
# do Liberation Sans (métrica-compatível com Arial, que é a fonte do estilo) e
# conferido contra as 215 linhas do Mateus 2: erro máximo de 0,019%.
#
# Existe porque o ASS não tem "encolher pra caber": a decisão de encolher tem
# que ser tomada aqui, ANTES de escrever o arquivo. E depender de um arquivo de
# fonte em disco não serve -- no Colab não dá pra garantir qual está instalada.
_AVANCO: dict[str, float] = {}
for _largura, _chars in {
    0.1909: "'",
    0.2002: "\u2009",                      # espaço fino (entre morfemas coreanos)
    0.2222: "ijl\u2018\u2019",
    0.2598: "|",
    0.2778: " !,./:;I[\\]ftÌÍÎÏìíîï",
    0.3330: "()-`r¡\u201c\u201d",
    0.3340: "{}",
    0.3550: '"',
    0.3652: "º",
    0.3701: "ª",
    0.3892: "*",
    0.3999: "°",
    0.4692: "^",
    0.5000: "Jcksvxyzç",
    0.5562: "#$0123456789?L_abdeghnopqu«»àáâãäèéêëñòóôõöùúûü–",
    0.5840: "+<=>~",
    0.6108: "FTZ¿",
    0.6670: "&ABEKPSVXYÀÁÂÃÄÈÉÊË",
    0.7222: "CDHNRUwÇÑÙÚÛÜ",
    0.7778: "GOQÒÓÔÕÖ",
    0.8330: "Mm",
    0.8892: "%",
    0.9438: "W",
    1.0000: "—…",
    1.0151: "@",
}.items():
    for _c in _chars:
        _AVANCO[_c] = _largura

_AVANCO_PADRAO = 0.5562      # o mais comum entre as latinas
_X_SIGLA = 18                # recuo da sigla dentro da margem esquerda
_INICIO_CJK = 0x2E80         # daqui pra cima é largura cheia (medido: exatamente 1.0)


def largura_texto(texto: str, tamanho_fonte: int) -> float:
    """Largura aproximada do texto em pixels, no Arial do tamanho dado.

    Hangul e ideograma são largura cheia -- medido, dá exatamente 1.0 × o
    tamanho da fonte, sem exceção nos 5 idiomas do projeto.
    """
    total = 0.0
    for ch in texto:
        if ch in _AVANCO:
            total += _AVANCO[ch]
        elif ord(ch) >= _INICIO_CJK:
            total += 1.0
        else:
            total += _AVANCO_PADRAO
    return total * tamanho_fonte


def _linhas_sigla(blocos_por_idioma: dict[str, list[dict]], config) -> list[str]:
    """As siglas de idioma na margem esquerda, uma por linha da pilha, visíveis
    o vídeo inteiro.

    Do lado, e não acima da linha: é informação de consulta -- o espectador
    olha uma vez e sabe qual linha é a dele --, e no meio do texto ela
    disputaria atenção com a leitura a cada bloco.

    Ficam presas ao X da margem, não ao centro: o texto colorido é
    centralizado e muda de largura a cada bloco, então uma sigla centralizada
    "acompanharia" a legenda e não pararia quieta.
    """
    linhas: list[str] = []
    for idioma, blocos in blocos_por_idioma.items():
        if not blocos:
            continue
        fim = max((b["fim_ms"] for b in blocos), default=0) + 500
        sigla = config.SIGLAS_IDIOMAS.get(idioma, idioma.upper()).split("-")[0]
        y = config.POSICOES_Y.get(idioma, 100)
        texto = (f"{{\\an4\\pos({_X_SIGLA},{y})\\fs{config.TAMANHO_FONTE_SIGLA}"
                 f"\\1c&H00C0C0C0&\\3c&H00000000&\\bord3\\shad0\\b1}}{sigla}")
        linhas.append(_LINHA_DIALOGO.format(
            inicio=_ms_para_ass(0), fim=_ms_para_ass(fim), texto=texto))
    return linhas


def gerar_ass(
    blocos_por_idioma: dict[str, list[dict]],
    config: PipelineConfig,
    caminho_saida: Optional[Path | str] = None,
    box_border: int = 6,
    espaco_colado: str = "\u2009",
    margem_lateral: int = 70,
    mostrar_siglas: bool = True,
) -> Path:
    """
    Gera o .ass com a classificação nova.

    Args:
        blocos_por_idioma: { "pt": [bloco, ...], "ko": [...], ... } — cada
            bloco é um dict com "inicio_ms", "fim_ms", e "pecas" (lista de
            PecaColorida).
        config: PipelineConfig — usa LARGURA_TELA/ALTURA_TELA/POSICOES_Y/
            TAMANHO_FONTE_TAG (mesmos campos do sistema antigo).
        espaco_colado: o que separa duas peças da mesma palavra escrita.
            Padrão: espaço fino (U+2009).
        box_border: largura da borda em px (a "espessura" da caixa).
        margem_lateral: px reservados em cada lado. A da ESQUERDA é onde
            ficam as siglas de idioma; a da direita existe pra linha
            centralizada não ficar torta. Linha que não couber na largura
            restante é ENCOLHIDA pra caber (\fscx/\fscy) -- o ASS não tem
            "encolher pra caber" nativo, então a conta é feita aqui.
            0 tira a margem — mas NÃO o encolhimento: linha mais larga que a
            tela continua sendo reduzida, porque deixar texto sair da tela
            nunca é o que se quer (e era o que acontecia antes disto).
        mostrar_siglas: escreve PT/EN/ES/FR/KO/ZH na margem esquerda, na
            altura de cada linha. Fica de lado de propósito: é informação de
            consulta, e no meio do texto atrapalharia a leitura.

    Medido no Mateus 2 (215 linhas): com margem de 70px, 17 linhas precisam
    encolher, e a mediana delas encolhe 4%. Sem margem nenhuma, UMA linha (o
    francês do bloco 31) já transbordava a tela -- 1403px numa tela de 1280.
    """
    if caminho_saida is None:
        caminho_saida = Path(f"legendas_{config.NOME_ORACAO}.ass")
    else:
        caminho_saida = Path(caminho_saida)

    linhas = [_ASS_HEADER.format(
        largura=config.LARGURA_TELA, altura=config.ALTURA_TELA,
        tamanho_fonte=config.TAMANHO_FONTE_TAG,
    )]

    util = config.LARGURA_TELA - 2 * margem_lateral if margem_lateral else config.LARGURA_TELA

    if mostrar_siglas:
        linhas += _linhas_sigla(blocos_por_idioma, config)

    for idioma, blocos in blocos_por_idioma.items():
        y = config.POSICOES_Y.get(idioma, 100)
        x = config.LARGURA_TELA // 2
        # Arial (fonte padrão) não tem os caracteres Hangul — sem isso, o
        # coreano aparece como quadradinhos (□) em ambientes sem fallback
        # automático de fonte (ex: Colab sem a Noto Sans CJK instalada
        # visível pro libass)
        _fonte = config.fonte_cjk(idioma)
        fonte_tag = f"\\fn{_fonte}" if _fonte else ""
        for bloco in blocos:
            pecas = bloco.get("pecas", [])
            if not pecas:
                continue
            largura = largura_texto(_texto_visivel(pecas, espaco_colado),
                                    config.TAMANHO_FONTE_TAG) + 2 * box_border
            escala = 100 if largura <= util else max(50, int(100 * util / largura))
            texto_ass = _linha_colorida_ass(pecas, box_border, config.TAMANHO_FONTE_TAG,
                                            x, y, fonte_tag, escala, espaco_colado)
            linhas.append(_LINHA_DIALOGO.format(
                inicio=_ms_para_ass(bloco["inicio_ms"]),
                fim=_ms_para_ass(bloco["fim_ms"]),
                texto=texto_ass,
            ))

    caminho_saida.write_text("".join(linhas), encoding="utf-8-sig")
    return caminho_saida


def salvar_classificacao_multicolor(blocos: list[dict], caminho_saida: Path | str) -> Path:
    """Salva a classificação (Stanza/Kiwi já filtrada, ver classificacao.py/
    classificacao_ko.py) de UM idioma como JSON -- disponível pra baixar,
    corrigir manualmente (trocar a "classe" de alguma peça errada) e subir
    de volta com o mesmo nome, antes de gerar o .ass (ver
    carregar_classificacao_multicolor)."""
    caminho_saida = Path(caminho_saida)
    bruto = [
        {
            "inicio_ms": bloco["inicio_ms"],
            "fim_ms": bloco["fim_ms"],
            "pecas": [
                {"texto": p.texto, "classe": p.classe,
                 "colado_anterior": p.colado_anterior, "upos": p.upos,
                 "lema": p.lema, "feats": p.feats,
                 "classe_automatica": p.classe_automatica}
                for p in bloco.get("pecas", [])
            ],
        }
        for bloco in blocos
    ]
    caminho_saida.write_text(json.dumps(bruto, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho_saida


def classificacao_confere(blocos_salvos: list[dict], legendas) -> str | None:
    """A classificação salva no Drive corresponde ao SRT que está sendo usado
    agora? Devolve None se confere, ou o motivo da divergência.

    Existe porque o reaproveitamento é cego: o notebook multicolor carrega o
    JSON salvo e usa no lugar de rodar Stanza/Kiwi de novo -- e as peças
    carregam o TEXTO, não só a classe. Uma classificação de uma versão
    anterior da legenda faz o vídeo exibir as palavras antigas, com o SRT
    novo parado ao lado. Nada falha; sai errado.

    A comparação ignora espaço e pontuação: o tokenizador do Stanza separa
    "l'adorer" em duas peças e o Kiwi quebra a palavra coreana em morfemas.
    O que tem que bater são as letras, na ordem.
    """
    if len(blocos_salvos) != len(legendas):
        return (f"{len(blocos_salvos)} bloco(s) salvos contra {len(legendas)} "
                f"no SRT atual")

    def letras(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum())

    for i, (bloco, leg) in enumerate(zip(blocos_salvos, legendas), 1):
        do_json = letras("".join(p.texto for p in bloco.get("pecas", [])))
        do_srt  = letras(leg.texto)
        if do_json != do_srt:
            return f"o bloco {i} não bate com o SRT atual"
    return None


def carregar_classificacao_multicolor(caminho: Path | str) -> list[dict]:
    """Carrega de volta o JSON salvo por salvar_classificacao_multicolor()
    -- reconstrói as PecaColorida a partir dos dicts, no formato que
    gerar_ass() espera em blocos_por_idioma[idioma]."""
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return [
        {
            "inicio_ms": bloco["inicio_ms"],
            "fim_ms": bloco["fim_ms"],
            "pecas": [
                PecaColorida(p["texto"], p["classe"], p.get("colado_anterior", False),
                             p.get("upos", ""), p.get("lema", ""), p.get("feats", ""),
                             p.get("classe_automatica", ""))
                for p in bloco.get("pecas", [])
            ],
        }
        for bloco in bruto
    ]
