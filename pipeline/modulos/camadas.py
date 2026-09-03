# -*- coding: utf-8 -*-
"""
camadas.py — Quais camadas este vídeo tem, declarado UMA vez.

O problema que isto resolve: as camadas opcionais do vídeo (siglas de idioma,
indicador de livro:versículo, título do trecho) eram decididas em interruptores
espalhados por três notebooks. Declarar num e esquecer no outro dava um vídeo
sem a camada -- ou pior, um notebook gerando um arquivo que outro nunca ia usar,
os dois em silêncio.

Aqui a declaração é UMA, mora no Drive junto do vídeo
(`<nome>_camadas.json`), e todo notebook a lê e obedece. Qualquer um pode
REdeclarar; os outros passam a seguir a nova.

E declarar tem consequência: camada declarada cujo arquivo não existe vira
ERRO na queima, não aviso. O modo de falhar que não se aceita aqui é ligar
uma camada e receber o vídeo sem ela.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

FORMATO = 1

# Padrão conservador: só as siglas, que não dependem de arquivo nenhum. As
# outras duas precisam de um SRT gerado antes, então começam desligadas -- ligar
# sozinha uma camada cujo arquivo não existe só produziria erro na primeira
# queima de todo vídeo novo.
PADRAO: dict[str, bool] = {
    "siglas_idioma": True,        # PT/EN/ES/FR/KO/ZH na margem esquerda
    "indicador_versiculo": False,  # "Matt/마/太 2:16" no canto superior esquerdo
    "titulo_trecho": False,        # "The Massacre of the Innocents" à direita
}

DESCRICAO: dict[str, str] = {
    "siglas_idioma": "siglas de idioma na margem esquerda",
    "indicador_versiculo": "indicador de livro:versículo (canto superior esquerdo)",
    "titulo_trecho": "título do trecho em inglês (canto superior direito)",
}

# De quem é cada camada: quem GERA o arquivo que ela precisa. Entra nas
# mensagens de erro, porque "falta o arquivo X" sem dizer quem faz o X manda a
# pessoa procurar.
QUEM_GERA: dict[str, str] = {
    "siglas_idioma": "",   # não precisa de arquivo: sai junto do .ass da legenda
    "indicador_versiculo": "a célula de indicador do caption-multilang-burn.ipynb",
    "titulo_trecho": "a última célula do match-scene-verse.ipynb",
}


class ErroDeCamada(Exception):
    """Declaração inválida, ou camada declarada sem o arquivo dela."""


def _conferir(camadas: dict) -> dict[str, bool]:
    """Recusa chave desconhecida em vez de ignorar: chave com erro de digitação
    seria silenciosa -- a camada simplesmente não ligaria, e ninguém saberia por
    quê."""
    sobra = set(camadas) - set(PADRAO)
    if sobra:
        raise ErroDeCamada(
            f"camada(s) que não existem: {', '.join(sorted(sobra))}. "
            f"As que existem: {', '.join(sorted(PADRAO))}")
    return {nome: bool(camadas.get(nome, PADRAO[nome])) for nome in PADRAO}


def carregar(caminho: Path | str) -> tuple[dict[str, bool], bool]:
    """Lê a declaração -> (camadas, existia). `existia=False` devolve o padrão.

    Formato desconhecido LEVANTA: ler pela metade ligaria ou desligaria camada
    sem ninguém pedir.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        return dict(PADRAO), False
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    if bruto.get("formato") != FORMATO:
        raise ErroDeCamada(f"{caminho.name} está no formato {bruto.get('formato')!r}, "
                           f"e este módulo lê o {FORMATO}.")
    return _conferir(bruto.get("camadas", {})), True


def salvar(camadas: dict, caminho: Path | str) -> Path:
    caminho = Path(caminho)
    caminho.write_text(json.dumps({
        "formato": FORMATO,
        "_leia-me": "Quais camadas este vídeo tem. Lido por todos os notebooks "
                    "de legenda; qualquer um pode redeclarar. Camada ligada cujo "
                    "arquivo não existe vira ERRO na queima, não aviso.",
        "camadas": _conferir(camadas),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return caminho


def descrever(camadas: dict[str, bool], origem: str = "") -> str:
    """Uma linha por camada, pra cada notebook imprimir o que está valendo.
    Todo notebook mostra o mesmo quadro: é o que faz a declaração ser única na
    prática, e não só no arquivo."""
    linhas = [f"🎬 Camadas deste vídeo{f' ({origem})' if origem else ''}:"]
    for nome in PADRAO:
        marca = "✅" if camadas.get(nome) else "  "
        linhas.append(f"   {marca} {DESCRICAO[nome]}")
    return "\n".join(linhas)


def exigir(camadas: dict[str, bool], nome: str, arquivo_existe: bool) -> None:
    """Camada declarada tem que ter o arquivo dela. Levanta se não tiver.

    É de propósito mais duro que um aviso: quem declarou a camada espera vê-la
    no vídeo, e um aviso no meio de uma saída longa passa batido -- aí o vídeo
    sai sem ela e só se descobre assistindo.
    """
    if not camadas.get(nome) or arquivo_existe:
        return
    quem = QUEM_GERA.get(nome, "")
    raise ErroDeCamada(
        f"'{nome}' está declarada ({DESCRICAO[nome]}) mas o arquivo dela não "
        f"está no Drive." + (f" Ele sai de {quem}." if quem else "") +
        f" Ou gere o arquivo, ou desligue a camada na declaração.")


def resolver(camadas_locais: Path | str, declaracao: Optional[dict] = None
             ) -> tuple[dict[str, bool], bool]:
    """O que vale agora -> (camadas, mudou).

    `declaracao=None` (o normal) usa o que já está declarado. Um dict
    REdeclara, e aí quem chama grava o arquivo pra todos os outros notebooks
    obedecerem.
    """
    atual, existia = carregar(camadas_locais)
    if declaracao is None:
        return atual, not existia          # "mudou" = precisa gravar a 1ª vez
    nova = _conferir(declaracao)
    return nova, (nova != atual or not existia)
