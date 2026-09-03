# -*- coding: utf-8 -*-
"""
moldura.py — A versão do vídeo em que a imagem vira MINIATURA.

O problema: com a foto ocupando a tela inteira atrás de seis linhas de
legenda colorida, a leitura fica poluída -- o olho não sabe se está lendo ou
olhando. As duas coisas competem pelo mesmo pixel.

A saída: a foto sai de trás do texto e vira uma miniatura ABAIXO da pilha de
idiomas, sobre uma IMAGEM MESTRE limpa (papel, cor lisa, o que for) que passa
a ser o fundo do vídeo inteiro. A foto continua ilustrando; só para de
disputar.

Aqui mora só a GEOMETRIA e o preparo do fundo. A composição é do
ffmpeg_utils.queimar_legendas_ass(..., miniatura=...), que faz fundo +
miniatura + legendas num passe de codificação só.

── Quanto espaço sobra, de verdade ─────────────────────────────────────────
Medido com o .ass real do Mateus 2 (renderizado, tinta contada pixel a
pixel), numa tela de 1280x720, com os seis idiomas:

    passo entre linhas   tinta ocupa      menor folga    miniatura 16:9
        80 (hoje)         y 73..502          47px          356x200
        72                y 73..462          39px          428x240
        66                y 73..432          33px          482x270
        58                y 73..392          25px          552x310
        50                y 73..352          17px          624x350

Cada linha de legenda tem ~31px de tinta. A folga é o branco ENTRE duas
linhas: abaixo de ~25px as faixas coloridas começam a se ler como um bloco
só, e a vantagem de ter uma cor por idioma se perde. Por isso o padrão
compacto é 66 -- folga de 33px, do tamanho da própria linha, e uma miniatura
com 2,4x a área da que cabe no espaçamento de hoje.

Nada disso é chute: `caixa_miniatura` DERIVA a caixa das posições que
estiverem valendo. Mudou o espaçamento, ou tirou um idioma, a caixa
acompanha sozinha.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

from constants import ALTURA_TELA, LARGURA_TELA, POSICOES_Y, POS_SIGLA_Y

# A tinta de uma linha desce um pouco abaixo do y do \pos (âncora an2 =
# base do texto, mas a borda de 6px e os descendentes passam). Medido: 2 a 3px.
DESCIDA_DA_LINHA = 4

# Distância entre o y da legenda e o y da sigla do idioma na margem (medida
# fixa em constants: 100-65, 180-145, ...). Guardada aqui porque quem muda o
# espaçamento das linhas tem que mover as siglas junto -- esquecer disso
# deixaria as siglas paradas, apontando pra linha errada.
DELTA_SIGLA = POSICOES_Y["en"] - POS_SIGLA_Y["en"]

FOLGA_ABAIXO_DA_LEGENDA = 10   # respiro entre a última linha e o topo da foto
MARGEM_RODAPE = 8              # respiro entre a foto e a borda de baixo
MARGEM_LATERAL_MINIATURA = 40  # limite de largura, pra não encostar nas beiradas
ALTURA_MINIMA = 90             # abaixo disso a miniatura não ilustra mais nada


class ErroDeMoldura(Exception):
    """Geometria que não fecha, ou .ass que não dá pra reposicionar."""


class Caixa(NamedTuple):
    """Retângulo da miniatura, em pixels da tela."""
    x: int
    y: int
    largura: int
    altura: int

    @property
    def base(self) -> int:
        return self.y + self.altura

    def __str__(self) -> str:
        return f"{self.largura}x{self.altura} em ({self.x},{self.y})"


def _par(n: float) -> int:
    """Dimensão par: o yuv420p subamostra o croma de dois em dois pixels, e
    largura/altura/posição ímpar deixa franja colorida na borda."""
    return int(n) // 2 * 2


def caixa_miniatura(
    idiomas: Iterable[str],
    posicoes_y: Optional[dict] = None,
    largura_tela: int = LARGURA_TELA,
    altura_tela: int = ALTURA_TELA,
    proporcao: float = 16 / 9,
    folga: int = FOLGA_ABAIXO_DA_LEGENDA,
    margem_rodape: int = MARGEM_RODAPE,
    margem_lateral: int = MARGEM_LATERAL_MINIATURA,
) -> Caixa:
    """A maior miniatura que cabe embaixo da legenda, centralizada.

    DERIVADA das posições que estão valendo, nunca fixa: tirar um idioma ou
    apertar o espaçamento tem que aumentar a foto sozinho. Caixa fixa num
    canto do código seria a primeira coisa a ficar errada.
    """
    posicoes_y = posicoes_y or POSICOES_Y
    idiomas = [i for i in idiomas if i in posicoes_y]
    if not idiomas:
        raise ErroDeMoldura("nenhum idioma conhecido — sem legenda não há de "
                            "onde derivar a caixa")
    return _caixa_abaixo_de(max(posicoes_y[i] for i in idiomas),
                            largura_tela, altura_tela, proporcao,
                            folga, margem_rodape, margem_lateral)


def _caixa_abaixo_de(ultima_linha_y: int,
                     largura_tela: int = LARGURA_TELA,
                     altura_tela: int = ALTURA_TELA,
                     proporcao: float = 16 / 9,
                     folga: int = FOLGA_ABAIXO_DA_LEGENDA,
                     margem_rodape: int = MARGEM_RODAPE,
                     margem_lateral: int = MARGEM_LATERAL_MINIATURA) -> Caixa:
    base_legenda = ultima_linha_y + DESCIDA_DA_LINHA
    topo = base_legenda + folga
    altura = _par(altura_tela - margem_rodape - topo)
    largura = _par(altura * proporcao)

    largura_maxima = _par(largura_tela - 2 * margem_lateral)
    if largura > largura_maxima:
        largura = largura_maxima
        altura = _par(largura / proporcao)

    if altura < ALTURA_MINIMA:
        raise ErroDeMoldura(
            f"sobram só {altura}px abaixo da legenda (mínimo {ALTURA_MINIMA}): "
            f"a última linha termina em y={base_legenda} e a tela tem "
            f"{altura_tela}. Aperte o espaçamento (ver posicoes_compactas) ou "
            f"tire um idioma.")

    return Caixa(_par((largura_tela - largura) / 2),
                 _par(altura_tela - margem_rodape - altura), largura, altura)


def posicoes_compactas(passo: int, posicoes_y: Optional[dict] = None
                       ) -> tuple[dict, dict]:
    """As posições das linhas e das siglas com outro espaçamento.

    Devolve (posicoes_y, pos_sigla_y). A primeira linha não sai do lugar: é
    o topo que está encostado no indicador de versículo e no título, que ficam
    acima dela.
    """
    posicoes_y = posicoes_y or POSICOES_Y
    if passo < 1:
        raise ErroDeMoldura(f"passo {passo} não faz sentido")
    ordem = sorted(posicoes_y, key=posicoes_y.get)
    primeiro = posicoes_y[ordem[0]]
    novas = {idioma: primeiro + passo * n for n, idioma in enumerate(ordem)}
    return novas, {idioma: y - DELTA_SIGLA for idioma, y in novas.items()}


_POS = re.compile(r"\\pos\((\d+),(\d+)\)")


def mapa_de_reposicionamento(passo: int, posicoes_y: Optional[dict] = None,
                             pos_sigla_y: Optional[dict] = None) -> dict[int, int]:
    """{y_atual: y_novo} pra reescrever um .ass já pronto.

    Cobre as duas famílias de y do arquivo -- as linhas e as siglas da margem.
    """
    posicoes_y = posicoes_y or POSICOES_Y
    pos_sigla_y = pos_sigla_y or POS_SIGLA_Y
    novas, novas_siglas = posicoes_compactas(passo, posicoes_y)
    mapa = {posicoes_y[i]: novas[i] for i in posicoes_y}
    mapa.update({pos_sigla_y[i]: novas_siglas[i] for i in pos_sigla_y if i in novas_siglas})
    return mapa


def reposicionar_ass(origem: Path | str, destino: Path | str,
                     mapa: dict[int, int]) -> Path:
    """Reescreve os \\pos de um .ass pronto — sem rodar o Stanza de novo.

    A legenda multicor custa caro pra gerar (análise morfológica dos seis
    idiomas). Mudar só a ALTURA das linhas é uma troca de texto, então a
    variante em miniatura sai do mesmo .ass da variante de tela cheia.

    Y que não está no mapa LEVANTA. Deixar passar seria o pior resultado
    possível: uma linha parada no lugar antigo, atravessando a miniatura, e
    nenhum erro pra explicar.
    """
    origem, destino = Path(origem), Path(destino)
    texto = origem.read_text(encoding="utf-8-sig")

    desconhecidos = {int(y) for _, y in _POS.findall(texto)} - set(mapa)
    if desconhecidos:
        raise ErroDeMoldura(
            f"{origem.name} tem linha(s) em y={sorted(desconhecidos)}, que não "
            f"estão nas posições conhecidas ({sorted(mapa)}). Reposicionar "
            f"assim deixaria essas linhas paradas, por cima da miniatura.")

    novo = _POS.sub(lambda m: f"\\pos({m.group(1)},{mapa[int(m.group(2))]})", texto)
    destino.write_text(novo, encoding="utf-8-sig")
    return destino


def caixa_para_ass(caminho_ass: Path | str, **kwargs) -> Caixa:
    """A caixa derivada do .ass QUE VAI SER QUEIMADO, não de uma lista à parte.

    O arquivo é a verdade: ele já sabe quantos idiomas tem e com que
    espaçamento. Derivar de uma lista digitada noutro lugar é abrir a porta
    pro caso em que as duas discordam -- e o sintoma seria a última linha
    invadindo a foto, ou um vão de 80px sem motivo.
    """
    caminho_ass = Path(caminho_ass)
    ys = [int(y) for _, y in _POS.findall(caminho_ass.read_text(encoding="utf-8-sig"))]
    if not ys:
        raise ErroDeMoldura(
            f"{caminho_ass.name} não tem nenhuma linha com \\pos — sem saber "
            f"onde a legenda termina não dá pra pôr a miniatura embaixo dela.")
    return _caixa_abaixo_de(max(ys), **kwargs)


def gerar_fundo_liso(caminho: Path | str, cor: str = "#F2EEE6",
                     largura: int = LARGURA_TELA, altura: int = ALTURA_TELA) -> Path:
    """Uma imagem mestre provisória de cor lisa, pra rodar a variante ANTES de
    ter a imagem definitiva. Trocar depois é trocar o arquivo -- nada no
    pipeline depende de qual imagem é.
    """
    caminho = Path(caminho)
    cor_ffmpeg = "0x" + cor.lstrip("#")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         # `,format=rgb24` DENTRO do lavfi: sem isso a fonte gera em YUV e a
         # volta pra RGB no PNG erra 1 em cada canal (#F2EEE6 vira #F1EDE5).
         # Não muda nada na tela, mas faz a cor que sai ser outra da que se
         # pediu -- e é a cor pedida que vai ser comparada com a marca.
         "-f", "lavfi", "-i", f"color=c={cor_ffmpeg}:s={largura}x{altura},format=rgb24",
         "-frames:v", "1", "-update", "1", str(caminho)],
        check=True)
    return caminho
