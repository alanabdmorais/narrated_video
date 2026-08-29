# -*- coding: utf-8 -*-
"""
biblia_texto.py — Lê o texto bíblico em USFM e gera o roteiro por versículo.

Por que USFM e não PDF nem HTML: o formato do `roteiro_versiculos.txt` que o
pipeline já usa é exatamente a estrutura que o USFM carrega -- versículos
correndo dentro de um parágrafo, com quebra de linha na poesia. PDF de duas
colunas embaralha, HTML muda de estrutura sem aviso; o USFM marca isso
explicitamente (\\p, \\q1) e é o formato em que o ebible.org publica.

O consumidor final é o `alinhar_versiculos()` (srt_utils.py), que casa este
texto contra a transcrição do Whisper pra derivar o tempo de cada versículo.
Ele lê os números de versículo como tokens isolados no fluxo e colapsa as
quebras de linha -- então a quebra é cosmética (pra leitura humana) e o que
importa é a sequência de palavras.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import biblia_livros as bl


@dataclass(frozen=True)
class Versiculo:
    numero: int
    texto: str
    quebra: bool  # começa em linha nova (parágrafo novo ou verso de poesia)


# Marcadores que ABREM linha nova: parágrafo, poesia, citação recuada.
_MARCA_QUEBRA = re.compile(r"^\\(p|m|pi\d?|q\d?|qr|qc|b|nb|cls|pc|pmo|pm|pmc|pmr)\b")
# Marcadores de "conteúdo fora do versículo": títulos, referências, cabeçalho.
_MARCA_IGNORAR = re.compile(r"^\\(id|ide|h|toc\d?|toca\d?|mt\d?|ms\d?|mr|s\d?|sr|r|sp|d|cl|cp|rem|sts|periph)\b")

# Notas de rodapé e referências cruzadas: conteúdo INTEIRO fora, não só a marca.
_NOTA = re.compile(r"\\(f|fe|x)\b.*?\\\1\*", re.S)
# Marcação de caractere que embrulha texto que FICA (palavras de Jesus, etc).
_CARACTERE = re.compile(r"\\\+?[a-z]+\d?\*?")
# \w palavra|lemma="x"\w*  -> fica só a palavra
_PALAVRA_ANOTADA = re.compile(r"\\\+?w\s+([^|\\]+?)(?:\|[^\\]*?)?\\\+?w\*")


def _limpar(linha: str) -> str:
    """Tira a marcação USFM de uma linha, preservando o texto."""
    linha = _NOTA.sub("", linha)
    linha = _PALAVRA_ANOTADA.sub(r"\1", linha)
    linha = _CARACTERE.sub("", linha)
    linha = linha.replace("~", " ")        # espaço inquebrável do USFM
    linha = linha.replace("//", " ")       # quebra de linha opcional
    return re.sub(r"\s+", " ", linha).strip()


def parsear_usfm(conteudo: str) -> tuple[bl.Livro, dict[int, list[Versiculo]]]:
    """Lê um arquivo USFM de UM livro -> (livro, {capítulo: [Versiculo, ...]}).

    Levanta ValueError se não achar o \\id ou se o livro não for reconhecido.
    """
    m = re.search(r"^\\id\s+(\w+)", conteudo, re.M)
    if not m:
        raise ValueError("USFM sem marcador \\id -- não dá pra saber que livro é")
    livro = bl.por_usfm(m.group(1))

    capitulos: dict[int, list[Versiculo]] = {}
    cap_atual: int | None = None
    quebra_pendente = True   # o primeiro versículo do capítulo sempre abre linha

    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha:
            continue

        if _MARCA_QUEBRA.match(linha):
            quebra_pendente = True
            linha = re.sub(r"^\\\w+\d?\s*", "", linha)
            if not linha:
                continue
        elif _MARCA_IGNORAR.match(linha):
            continue

        m_cap = re.match(r"^\\c\s+(\d+)", linha)
        if m_cap:
            cap_atual = int(m_cap.group(1))
            capitulos.setdefault(cap_atual, [])
            quebra_pendente = True
            continue

        if cap_atual is None:
            continue  # ainda no cabeçalho do arquivo

        # Uma linha pode trazer mais de um \v; parte em cada um.
        for pedaco in re.split(r"(?=\\v\s)", linha):
            pedaco = pedaco.strip()
            if not pedaco:
                continue
            m_v = re.match(r"^\\v\s+(\d+)(?:-\d+)?\s*(.*)$", pedaco, re.S)
            if m_v:
                texto = _limpar(m_v.group(2))
                capitulos[cap_atual].append(
                    Versiculo(int(m_v.group(1)), texto, quebra_pendente))
                quebra_pendente = False
            elif capitulos[cap_atual]:
                # continuação do versículo anterior (texto que veio na linha
                # seguinte, sem \v próprio)
                extra = _limpar(pedaco)
                if extra:
                    ultimo = capitulos[cap_atual][-1]
                    capitulos[cap_atual][-1] = Versiculo(
                        ultimo.numero,
                        f"{ultimo.texto} {extra}".strip(),
                        ultimo.quebra)

    return livro, capitulos


def gerar_roteiro(versiculos: list[Versiculo]) -> str:
    """Monta o texto no formato do `<nome>_roteiro_versiculos.txt`.

    Número do versículo como token isolado antes do texto; versículo marcado
    com `quebra` começa linha nova. É o formato que `extrair_marcadores_
    versiculo()` (srt_utils.py) já sabe ler.
    """
    partes: list[str] = []
    for v in versiculos:
        if not v.texto:
            continue
        sep = "\n" if (v.quebra and partes) else (" " if partes else "")
        partes.append(f"{sep}{v.numero} {v.texto}")
    return "".join(partes)


def gerar_narracao(versiculos: list[Versiculo]) -> str:
    """O mesmo texto, SEM os números de versículo — pro `<nome>_roteiro.txt`.

    Os dois arquivos existem porque servem a coisas opostas:

        <nome>_roteiro_versiculos.txt   `1 Now when Jesus... 2 Where is he...`
            o número é dado: é por ele que o match casa cena com versículo e
            que a legenda sabe qual referência mostrar.

        <nome>_roteiro.txt              `Now when Jesus... Where is he...`
            o número é lixo: vira TEXTO_ORACAO, e o Edge TTS leria "um.
            Agora quando Jesus... dois. Onde está aquele..." em voz alta.

    Gravar um no lugar do outro não dá erro — dá uma narração contando números.
    """
    return " ".join(v.texto for v in versiculos if v.texto)


# ── Ler de volta o web-biblia.json ───────────────────────────────────────────
#
# O `biblia-texto-baixar.ipynb` grava a Bíblia inteira num JSON; daqui pra
# frente qualquer capítulo é uma consulta. É o que faz o roteiro deixar de ser
# algo que você fornece e virar algo que o sistema busca.

import json as _json
from pathlib import Path as _Path

NOME_BIBLIA_JSON = "web-biblia.json"


def carregar_biblia(caminho: _Path | str) -> dict:
    """Lê o web-biblia.json. Erro claro quando ele ainda não existe -- é o
    caso mais comum, e "KeyError: 'livros'" não diria a ninguém que o que
    falta é rodar um notebook."""
    caminho = _Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"{caminho} não existe. Rode o biblia-texto-baixar.ipynb uma vez — "
            f"ele baixa a WEB do ebible.org e grava esse arquivo.")
    dados = _json.loads(caminho.read_text(encoding="utf-8"))
    if "livros" not in dados:
        raise ValueError(f"{caminho} não parece um web-biblia.json (sem 'livros')")
    return dados


def versiculos_de(biblia: dict, sigla: str, capitulo: int) -> list[Versiculo]:
    """Os versículos de um capítulo, de volta ao formato que o resto usa."""
    livros = biblia["livros"]
    if sigla not in livros:
        raise KeyError(f"{sigla!r} não está no web-biblia.json "
                       f"({len(livros)} livros lidos)")
    caps = livros[sigla]
    chave = str(capitulo)
    if chave not in caps:
        raise KeyError(f"{sigla} {capitulo} não está no web-biblia.json "
                       f"(o livro tem {len(caps)} capítulos lá)")
    return [Versiculo(numero=v["n"], texto=v["t"], quebra=v["q"]) for v in caps[chave]]


def roteiro_do_capitulo(nome_projeto: str, caminho_biblia: _Path | str) -> str:
    """Roteiro por versículo de "40_Matt_02", direto do web-biblia.json.

    Fecha o ciclo: `biblia_livros.de_nome_projeto()` traduz o nome do vídeo em
    (livro, capítulo), e isto devolve o texto no mesmo formato do
    `<nome>_roteiro_versiculos.txt` -- byte a byte o mesmo `gerar_roteiro()`
    que o notebook de download usa, então não há dois formatos concorrentes.
    """
    livro, capitulo = bl.de_nome_projeto(nome_projeto)
    biblia = carregar_biblia(caminho_biblia)
    return gerar_roteiro(versiculos_de(biblia, livro.sigla, capitulo))


def narracao_do_capitulo(nome_projeto: str, caminho_biblia: _Path | str) -> str:
    """O texto de "40_Matt_02" sem números de versículo — ver gerar_narracao."""
    livro, capitulo = bl.de_nome_projeto(nome_projeto)
    biblia = carregar_biblia(caminho_biblia)
    return gerar_narracao(versiculos_de(biblia, livro.sigla, capitulo))


# ── Comparação com um roteiro já existente ───────────────────────────────────

def _normalizar(texto: str) -> list[str]:
    """Palavras comparáveis: sem marcador de versículo, sem pontuação, minúsculas.

    Aspas curvas viram retas e acentos caem, senão diferença puramente
    tipográfica entre duas edições apareceria como divergência de texto.
    """
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("\u2019", "'").replace("\u2018", "'")
    texto = texto.replace("\u201c", '"').replace("\u201d", '"')
    texto = texto.replace("\u2014", " ").replace("\u2013", " ")
    palavras = []
    for tok in texto.lower().split():
        if re.fullmatch(r"\d{1,3}", tok):
            continue  # marcador de versículo
        tok = re.sub(r"[^\w']", "", tok)
        if tok:
            palavras.append(tok)
    return palavras


@dataclass
class Comparacao:
    palavras_a: int
    palavras_b: int
    iguais: int
    diferencas: list[tuple[str, str, str]]  # (tipo, trecho_a, trecho_b)

    @property
    def similaridade(self) -> float:
        total = max(self.palavras_a, self.palavras_b)
        return self.iguais / total if total else 1.0

    @property
    def identico(self) -> bool:
        return not self.diferencas


def comparar(texto_a: str, texto_b: str, contexto: int = 6) -> Comparacao:
    """Compara dois roteiros palavra a palavra e lista onde divergem.

    Ignora número de versículo, pontuação, acento e tipo de aspas -- sobra a
    sequência de palavras, que é o que o alinhamento com o Whisper usa.
    """
    import difflib

    a, b = _normalizar(texto_a), _normalizar(texto_b)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)

    iguais = 0
    diferencas: list[tuple[str, str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            iguais += i2 - i1
        else:
            diferencas.append((
                tag,
                " ".join(a[max(0, i1 - contexto):i2 + contexto]),
                " ".join(b[max(0, j1 - contexto):j2 + contexto]),
            ))
    return Comparacao(len(a), len(b), iguais, diferencas)
