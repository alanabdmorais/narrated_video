# -*- coding: utf-8 -*-
"""
pixabay_urls.py — as regras de link do Pixabay, num lugar só.

A API do Pixabay entrega dois links por imagem, e só um deles dura:

    largeImageURL  https://pixabay.com/get/g<assinatura>_1280.jpg   ASSINADO, expira
    previewURL     https://cdn.pixabay.com/photo/…/nome_150.jpg     arquivo direto, permanente

Guardar o primeiro numa planilha é uma bomba-relógio: funciona no dia da
semeadura e responde **400 Bad Request** meses depois, em todas as linhas de
uma vez, sem nada ter mudado na planilha. Foi assim que 45 de 45 imagens
morreram juntas no primeiro teste do Matt 02.

O segundo continua servindo, e a mesma pasta do CDN tem as outras resoluções
— basta trocar o `_150` do fim.

Este módulo existe porque a regra estava prestes a ficar em três lugares
(o pipeline de vídeo, o semeador, e o Apps Script da planilha de busca). Nos
dois primeiros dá pra ter uma fonte só; o terceiro vive fora do repo e é
copiado à mão, o que já é motivo suficiente pra o lado de cá não se repetir
também.
"""
from __future__ import annotations

import re

# Thumbnail: https://cdn.pixabay.com/photo/2016/11/29/05/45/nome-1867616_150.jpg
# O host `cdn.pixabay.com` serve o arquivo direto e não expira.
_RE_THUMB = re.compile(r"^(https://cdn\.pixabay\.com/photo/\S+?)_\d+(\.\w+)$")

# O link assinado: .../get/g<hex longo>_<largura>.<ext>. Casa pela FORMA e não
# pelo host — o Pixabay já serviu esses links de mais de um domínio, e é a
# assinatura no caminho que os identifica, não o domínio.
_RE_ASSINADO = re.compile(r"/get/g[0-9a-f]{8,}_\d+\.\w+$", re.I)

# Do maior pro menor. O 1280 é o que o vídeo usa; os menores existem pra o
# caso raro de a foto não ter a resolução maior no CDN.
TAMANHOS = (1280, 960, 640, 340, 150)


def e_link_assinado(url: str) -> bool:
    """O link é do tipo que expira?"""
    return bool(_RE_ASSINADO.search((url or "").strip()))


def urls_alternativas(url_thumbnail: str) -> list[str]:
    """Do link do thumbnail, deriva links estáveis do MESMO arquivo, maiores.

    Devolve os candidatos do maior pro menor. Lista vazia se a URL não for um
    thumbnail do Pixabay — aí não há o que derivar, e chutar seria pior que
    falhar.
    """
    m = _RE_THUMB.match((url_thumbnail or "").strip())
    if not m:
        return []
    base, ext = m.groups()
    return [f"{base}_{tamanho}{ext}" for tamanho in TAMANHOS]


def url_estavel(hit: dict) -> str:
    """O melhor link permanente pra um `hit` da API do Pixabay.

    Cai no `largeImageURL` só quando não dá pra derivar do preview — melhor um
    link que vence do que nenhum, mas aí a linha gravada tem prazo de validade.
    """
    derivadas = urls_alternativas(str(hit.get("previewURL") or ""))
    if derivadas:
        return derivadas[0]
    return str(hit.get("largeImageURL") or hit.get("webformatURL") or "")
