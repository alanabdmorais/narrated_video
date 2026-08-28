# -*- coding: utf-8 -*-
"""
nomenclatura.py — A convenção de nomes do projeto, em código.

Nome de arquivo é contrato: notebook procura `40_Matt_02_roteiro.txt`, e se
alguém salvar `40_matt_02_roteiro.txt` o pipeline não acha e ninguém entende
por quê. Documentar a regra num .md ajuda, mas .md não é lido na hora do
aperto -- por isso a regra mora aqui, executável, e o `verificar()` diz quando
a realidade saiu dela.

## As sete famílias de nome

    notebook          biblia-audio-baixar.ipynb        kebab-case
    módulo            tempos_cache.py                  snake_case
    arquivo do vídeo  40_Matt_02_roteiro.txt           {projeto}_{papel}
    capítulo          40_Matt_02                       {NN}_{Sigla}_{CC}
    compilação        comp_salmos_esperanca            comp_{tema}
    aba de planilha   biblioteca_match                 snake_case
    pasta do Drive    assets/biblia_audio              snake_case

Quem CONSTRÓI cada nome já tem dono, e não é este módulo:

    arquivo do vídeo  ->  config.py (as propriedades nome_*)
    capítulo          ->  biblia_livros.Livro.nome_projeto()
    compilação        ->  compilacao_pipeline.nome_compilacao()

Aqui fica a regra que todos obedecem, e a conferência.

## Por que as exceções são registradas, e não consertadas

`EXCECOES` lista nome fora do padrão que fica como está, com o motivo. Sem esse
registro o `verificar()` acusaria os mesmos oito nomes pra sempre, e um
verificador que sempre reclama é um verificador que ninguém lê -- a mesma
armadilha da checagem de fonte no portão de qualidade.

Renomear tem custo real: aba de planilha viva quebra a planilha, e notebook
renomeado perde o link que você tem salvo no Colab. Exceção registrada é
decisão; exceção esquecida é bagunça.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ── As regras ────────────────────────────────────────────────────────────────

#: kebab-case: minúscula, dígito e hífen. Sem acento, sem underscore, sem
#: maiúscula -- nome de notebook vira URL no Colab e caminho no Drive.
PADRAO_NOTEBOOK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

#: snake_case, como manda o PEP 8.
PADRAO_MODULO = re.compile(r"^[a-z][a-z0-9_]*$")

#: Aba de planilha e pasta do Drive seguem snake_case também.
PADRAO_ABA = re.compile(r"^[a-z][a-z0-9_]*$")
PADRAO_PASTA = re.compile(r"^[a-z][a-z0-9_]*$")

#: Capítulo: 40_Matt_02. Sigla OSIS com inicial maiúscula, capítulo com pelo
#: menos 2 dígitos (Salmos usa 3 -- ver biblia_livros.largura_capitulo).
PADRAO_CAPITULO = re.compile(r"^\d{2}_[A-Z1-3][A-Za-z]+_\d{2,3}$")

#: Compilação: comp_ + tema normalizado, tudo minúsculo.
PADRAO_COMPILACAO = re.compile(r"^comp_[a-z0-9]+(?:_[a-z0-9]+)*$")

#: Arquivo dentro da pasta de um vídeo: {projeto}_{papel}.{ext}
PADRAO_ARQUIVO_VIDEO = re.compile(r"^(?P<projeto>.+?)_(?P<papel>[a-z0-9_]+)\.(?P<ext>[a-z0-9]+)$")

#: O idioma sempre entra como sufixo, nunca no meio:
#:     40_Matt_02_whisper_en.srt   ✓
#:     40_Matt_02_en_whisper.srt   ✗
#: Assim `nome.rsplit("_", 1)` devolve o idioma sem heurística.
IDIOMAS_CONHECIDOS = ("pt", "en", "es", "fr", "ko", "zh")


@dataclass(frozen=True)
class Excecao:
    nome: str
    familia: str
    motivo: str


#: Nome fora do padrão que FICA como está. Cada um com o motivo -- exceção sem
#: motivo escrito vira, seis meses depois, "isso aí é assim porque sim".
EXCECOES: tuple[Excecao, ...] = (
    Excecao("image-stock", "aba",
            "Aba viva da planilha de imagens, com dados dentro. Renomear "
            "quebraria a planilha e todo notebook que a lê, pra ganhar só "
            "consistência cosmética."),
    # A cadeia caption-* nasceu em inglês, antes de o projeto assentar em
    # português. Renomear quebra o link que você tem salvo no Colab de cada
    # uma -- custo real, ganho nenhum.
    Excecao("caption-multicolor-burn", "notebook", "Cadeia caption-*, nomeada em inglês antes do padrão assentar."),
    Excecao("caption-multicolor-generate", "notebook", "idem"),
    Excecao("caption-multicolor-zh-generate", "notebook", "idem"),
    Excecao("caption-multilang-burn", "notebook", "idem"),
    Excecao("caption-multilang-generate", "notebook", "idem"),
    Excecao("caption-multilang-sources-gather", "notebook", "idem"),
    Excecao("caption-multilang-zh-burn", "notebook", "idem"),
    Excecao("caption-multilang-zh-generate", "notebook", "idem"),
    Excecao("caption-multilang-zh-sources-gather", "notebook", "idem"),
    Excecao("caption-single-burn", "notebook", "idem"),
    Excecao("caption-single-generate", "notebook", "idem"),
    Excecao("match-scene-verse", "notebook", "Nomeado em inglês na mesma época da cadeia caption-*."),
    Excecao("pixabay-image-descriptions", "notebook", "idem"),
    Excecao("pixabay-video-descriptions", "notebook", "idem"),
    Excecao("compilar-versiculos-teste", "notebook",
            "Notebook de teste de um capítulo só, anterior ao compilacao-montar. "
            "Fica até a compilação rodar de verdade em produção."),
)

_EXCECAO_POR_NOME = {(e.familia, e.nome): e for e in EXCECOES}


def eh_excecao(nome: str, familia: str) -> Excecao | None:
    return _EXCECAO_POR_NOME.get((familia, nome))


# ── Conferência ──────────────────────────────────────────────────────────────

@dataclass
class Divergencia:
    familia: str
    nome: str
    esperado: str

    def __str__(self) -> str:
        return f"  [{self.familia}] {self.nome!r} — {self.esperado}"


_FAMILIAS = {
    "notebook": (PADRAO_NOTEBOOK, "kebab-case: minúscula, dígito e hífen"),
    "modulo":   (PADRAO_MODULO,   "snake_case (PEP 8)"),
    "aba":      (PADRAO_ABA,      "snake_case"),
    "pasta":    (PADRAO_PASTA,    "snake_case"),
    "capitulo": (PADRAO_CAPITULO, "{NN}_{SiglaOSIS}_{CC} — ex: 40_Matt_02"),
    "compilacao": (PADRAO_COMPILACAO, "comp_{tema} tudo minúsculo"),
}


def conferir(nome: str, familia: str) -> Divergencia | None:
    """Confere um nome contra a regra da família. None = está certo (ou é
    exceção registrada)."""
    if familia not in _FAMILIAS:
        raise KeyError(f"família desconhecida: {familia!r} — use {sorted(_FAMILIAS)}")
    if eh_excecao(nome, familia):
        return None
    padrao, descricao = _FAMILIAS[familia]
    if padrao.match(nome):
        return None
    return Divergencia(familia, nome, descricao)


def idioma_do_arquivo(nome: str) -> str | None:
    """Idioma no fim do nome, se houver: '..._whisper_en.srt' -> 'en'.

    Só funciona porque a regra manda o idioma ser SUFIXO. Nome com o idioma no
    meio precisaria de adivinhação, e adivinhação erra calada.
    """
    caule = Path(nome).stem
    if "_" not in caule:
        return None
    ultimo = caule.rsplit("_", 1)[1]
    return ultimo if ultimo in IDIOMAS_CONHECIDOS else None


def verificar_repo(raiz: Path | str) -> list[Divergencia]:
    """Varre o repositório e devolve os nomes fora da convenção.

    Confere o que o repositório tem: notebook e módulo. Aba de planilha e
    pasta do Drive vivem fora daqui -- pra essas, use conferir() na mão.
    """
    raiz = Path(raiz)
    achados: list[Divergencia] = []

    for caminho in sorted((raiz / "pipeline" / "notebooks").glob("*.ipynb")):
        d = conferir(caminho.stem, "notebook")
        if d:
            achados.append(d)

    for caminho in sorted((raiz / "pipeline" / "modulos").glob("*.py")):
        if caminho.name == "__init__.py":
            continue
        d = conferir(caminho.stem, "modulo")
        if d:
            achados.append(d)

    return achados


def relatorio(raiz: Path | str) -> str:
    achados = verificar_repo(raiz)
    if not achados:
        n = len(EXCECOES)
        return (f"✅ Todo nome segue a convenção "
                f"({n} exceção(ões) registrada(s), nenhuma surpresa).")
    linhas = [f"⚠️  {len(achados)} nome(s) fora da convenção:"]
    linhas += [str(d) for d in achados]
    linhas.append("")
    linhas.append("Conserte o nome, ou registre em EXCECOES com o motivo.")
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    print(relatorio(raiz))
