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
registro o `verificar_repo()` acusaria os mesmos 20 nomes pra sempre, e um
verificador que sempre reclama é um verificador que ninguém lê -- a mesma
armadilha da checagem de fonte no portão de qualidade.

## Três defeitos diferentes

GRAFIA (`conferir`) é como o nome se escreve: kebab, snake, maiúscula.
FORMA (`conferir_forma_notebook`) é a ordem das partes: a ação vai por último.
REFERÊNCIA (`referencias_fantasma`) é o resto do repositório apontando pra um
nome que não existe mais.

As duas primeiras olham o arquivo; a terceira olha quem fala dele. Um nome
pode estar impecável nas duas primeiras e ainda assim meia dúzia de módulos
mandarem você rodar o nome antigo.

## Por que a terceira existe

Renomear não quebra arquivo -- quebra REFERÊNCIA, e referência quebrada é
calada: o notebook continua rodando, só que a mensagem de erro manda você
rodar um notebook que não existe mais.

Não é hipótese. A onda de rename anterior deste projeto deixou 14 delas, três
em mensagem de erro que o usuário vê na hora do aperto ("Rode o
video-base.ipynb primeiro" — não existe). A pasta `notebooks.backup/` guardava
os arquivos antigos e não protegeu nenhuma dessas, porque não era o arquivo
que estava em risco.

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

#: Palavras de AÇÃO usadas em nome de notebook. A regra: quando uma delas
#: aparece, ela vai POR ÚLTIMO.
#:
#:     biblia-audio-baixar        ✓  área, alvo, ação
#:     organizar-trilha-audio     ✗  ação na frente
#:
#: Não é preciosismo: verbo no fim faz a ordenação alfabética agrupar por
#: assunto. Com o verbo na frente, `organizar-trilha-audio` fica longe de
#: `trilha-*`, que é justamente o que ele manipula -- e você procura pelo
#: assunto, não pela ação.
ACOES = frozenset({
    # português
    "baixar", "montar", "gerar", "queimar", "compilar", "organizar",
    "sincronizar", "extrair", "conferir", "publicar",
    # inglês, da era em que os notebooks nasceram assim
    "generate", "burn", "gather", "seed", "match", "build",
})


def conferir_forma_notebook(nome: str) -> str | None:
    """Confere a FORMA do nome do notebook: ação por último.

    Devolve None se está certo, ou a explicação do que está torto. Separado
    do `conferir()` de grafia porque são dois defeitos diferentes -- um nome
    pode estar em kebab-case perfeito e ainda assim com o verbo no lugar
    errado.
    """
    segmentos = nome.split("-")
    posicoes = [i for i, seg in enumerate(segmentos) if seg in ACOES]
    if not posicoes:
        return None  # sem verbo: `portao-qualidade`, `video-base-*`
    if posicoes[-1] != len(segmentos) - 1:
        verbo = segmentos[posicoes[-1]]
        return (f"a ação {verbo!r} não está no fim — "
                f"tente {'-'.join(s for s in segmentos if s != verbo)}-{verbo}")
    return None


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
    Excecao("organizar-efeitos-audio", "notebook",
            "Ação na frente. Renomear quebra o link salvo no Colab; a regra "
            "vale pros próximos."),
    Excecao("organizar-trilha-audio", "notebook", "idem"),
    Excecao("sincronizar-evento-titulo-tags", "notebook", "idem"),
    Excecao("pixabay-image-seed-biblia-completa", "notebook",
            "Ação 'seed' no meio, entre o alvo e o qualificador."),
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


#: Onde procurar por citação a notebook. Notebook cita notebook (o markdown
#: diz qual vem depois), módulo cita notebook (docstring e mensagem de erro), e
#: a documentação cita os dois.
ONDE_CITAM = (
    "pipeline/modulos/*.py",
    "pipeline/notebooks/*.ipynb",
    "pipeline/*.md",
    "assets/*.py",
    "README.md",
)

#: Só pega nome literal. `video-base-*.ipynb` e `caption-*-zh-*.ipynb` são
#: PADRÃO, não nome -- o `(?<![*\-\w])` descarta tudo que vem depois de curinga
#: ou hífen, senão `video-base-*-versiculo.ipynb` viraria uma citação ao
#: inexistente "versiculo.ipynb". Citar pelo padrão é a forma honesta de falar
#: dos seis notebooks de vídeo base de uma vez, então ela fica de fora da
#: checagem de propósito.
_CITACAO = re.compile(r"(?<![*\-\w])([a-z0-9][a-z0-9_-]*)\.ipynb")


#: Citação a notebook que NÃO existe e está certa assim: o texto fala da
#: ausência dele, ou propõe um nome pro futuro. Registrada por (arquivo, nome)
#: e não só por nome, porque o mesmo nome pode ser proposta num documento e
#: referência podre num módulo.
MENCOES_DE_AUSENCIA: frozenset[tuple[str, str]] = frozenset({
    ("caption-multicolor-burn.ipynb", "caption-multicolor-zh-burn"),
    # "Não existe um caption-multicolor-zh-burn porque não precisa" -- a frase
    # explica justamente que ele não existe.
    ("CONFIGURACAO.md", "video-base"),
    # Decisão adiada 9.1 propõe consolidar os seis num `video-base.ipynb`. É
    # nome de proposta, não referência a arquivo.
    ("nomenclatura.py", "video-base"),
    ("nomenclatura.py", "versiculo"),
    # Este arquivo. A docstring cita nomes mortos como EXEMPLO do defeito que o
    # `referencias_fantasma()` procura, e o comentário do `_CITACAO` cita o
    # falso positivo que o lookbehind existe pra evitar. Achar os próprios
    # exemplos foi o primeiro acerto do checador -- mas exemplo não é
    # referência, então ficam registrados em vez de reescritos.
})


@dataclass
class Fantasma:
    arquivo: str      # onde a citação aparece (nome do arquivo)
    citado: str       # o notebook citado, sem .ipynb
    linha: int

    def __str__(self) -> str:
        return f"  [{self.arquivo}:{self.linha}] cita {self.citado + '.ipynb'!r}, que não existe"


def referencias_fantasma(raiz: Path | str) -> list[Fantasma]:
    """Quem no repositório aponta pra um notebook que não existe mais.

    É a checagem que sobra depois de renomear: o arquivo novo está lá, o nome
    velho sumiu, e ninguém releu os seis módulos que mandavam rodar o velho.
    """
    raiz = Path(raiz)
    existem = {p.stem for p in (raiz / "pipeline" / "notebooks").glob("*.ipynb")}

    achados: list[Fantasma] = []
    for padrao in ONDE_CITAM:
        for caminho in sorted(raiz.glob(padrao)):
            if "notebooks.backup" in caminho.parts or "__pycache__" in caminho.parts:
                continue
            try:
                texto = caminho.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for n, linha in enumerate(texto.splitlines(), start=1):
                for m in _CITACAO.finditer(linha):
                    nome = m.group(1)
                    if nome in existem:
                        continue
                    if (caminho.name, nome) in MENCOES_DE_AUSENCIA:
                        continue
                    achados.append(Fantasma(caminho.name, nome, n))
    return achados


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
            continue  # grafia torta já foi reportada; forma vem depois
        if not eh_excecao(caminho.stem, "notebook"):
            problema = conferir_forma_notebook(caminho.stem)
            if problema:
                achados.append(Divergencia("notebook", caminho.stem, problema))

    for caminho in sorted((raiz / "pipeline" / "modulos").glob("*.py")):
        if caminho.name == "__init__.py":
            continue
        d = conferir(caminho.stem, "modulo")
        if d:
            achados.append(d)

    return achados


def relatorio(raiz: Path | str) -> str:
    achados = verificar_repo(raiz)
    fantasmas = referencias_fantasma(raiz)

    if not achados and not fantasmas:
        return (f"✅ Todo nome segue a convenção ({len(EXCECOES)} exceção(ões) "
                f"registrada(s)) e ninguém cita notebook que não existe.")

    linhas: list[str] = []
    if achados:
        linhas.append(f"⚠️  {len(achados)} nome(s) fora da convenção:")
        linhas += [str(d) for d in achados]
        linhas.append("")
        linhas.append("Conserte o nome, ou registre em EXCECOES com o motivo.")
    if fantasmas:
        if linhas:
            linhas.append("")
        linhas.append(f"⚠️  {len(fantasmas)} referência(s) a notebook inexistente:")
        linhas += [str(f) for f in fantasmas]
        linhas.append("")
        linhas.append("Aponte pro nome atual. Se o texto fala da AUSÊNCIA do "
                      "notebook de propósito, registre em MENCOES_DE_AUSENCIA.")
    return "\n".join(linhas)


if __name__ == "__main__":
    import sys
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    print(relatorio(raiz))
