# -*- coding: utf-8 -*-
"""
biblia_livros.py — Tabela canônica dos 66 livros da Bíblia.

Fonte única de verdade pra:
  - o nome de projeto de um capítulo  -> "40_Matt_02"  (nome_projeto)
  - o nome do mp3 no AudioTreasure    -> "40_Matthew02" (stem_audio)
  - quantos capítulos cada livro tem  -> pra conferir download completo

A sigla segue o padrão OSIS, que é o mesmo que o projeto já usava à mão
("Matt" em 40_Matt_02) -- então capítulos antigos continuam batendo.

⚠️ Os nomes de arquivo do AudioTreasure são IRREGULARES. Por isso cada livro
carrega seu próprio `modelo_audio` em vez de o código tentar deduzir um
padrão que não existe:

    01_Genesis_01        underscore antes do número (a maioria)
    40_Matthew01         SEM underscore
    25_Lamentations03    SEM underscore
    19_Psalm_001         número com TRÊS dígitos
    22_Song_of_Soloman_01   "Soloman" escrito assim mesmo, na fonte

Deduzir isso em runtime só esconderia o problema; explícito, quebra alto se
a fonte mudar.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Livro:
    numero: int        # 1..66, a ordem canônica (é o prefixo do nome de arquivo)
    sigla: str         # abreviação OSIS usada pelo projeto -- "Matt"
    nome: str          # nome em inglês -- "Matthew"
    capitulos: int     # quantos capítulos o livro TEM (o cânone, não o que a fonte entregou)
    modelo_audio: str  # template do stem no AudioTreasure, formatado com cap=

    @property
    def largura_capitulo(self) -> int:
        """Quantos dígitos o número do capítulo usa NESTE livro (mínimo 2).

        Padding pela largura do próprio livro, não fixo: Mateus (28 caps) fica
        com 2 e continua 40_Matt_02 como sempre foi, e Salmos (150) fica com 3
        -- 19_Ps_001 .. 19_Ps_150. Com 2 fixos, Salmos ordenaria 01, 10, 100,
        11, 110... numa listagem de pasta.
        """
        return max(2, len(str(self.capitulos)))

    def nome_projeto(self, capitulo: int) -> str:
        """Nome do capítulo no padrão do projeto: 40_Matt_02."""
        self._validar(capitulo)
        return f"{self.numero:02d}_{self.sigla}_{capitulo:0{self.largura_capitulo}d}"

    def stem_audio(self, capitulo: int) -> str:
        """Nome do arquivo (sem .mp3) como o AudioTreasure publica."""
        self._validar(capitulo)
        return self.modelo_audio.format(cap=capitulo)

    def _validar(self, capitulo: int) -> None:
        if not 1 <= capitulo <= self.capitulos:
            raise ValueError(
                f"{self.nome} tem {self.capitulos} capítulos; pediram {capitulo}")


def _padrao(numero: int, nome: str) -> str:
    """O formato da maioria dos livros: 01_Genesis_01."""
    return f"{numero:02d}_{nome}_{{cap:02d}}"


LIVROS: tuple[Livro, ...] = (
    # ── Antigo Testamento ────────────────────────────────────────────────────
    Livro(1,  "Gen",    "Genesis",       50, _padrao(1,  "Genesis")),
    Livro(2,  "Exod",   "Exodus",        40, _padrao(2,  "Exodus")),
    Livro(3,  "Lev",    "Leviticus",     27, _padrao(3,  "Leviticus")),
    Livro(4,  "Num",    "Numbers",       36, _padrao(4,  "Numbers")),
    Livro(5,  "Deut",   "Deuteronomy",   34, _padrao(5,  "Deuteronomy")),
    Livro(6,  "Josh",   "Joshua",        24, _padrao(6,  "Joshua")),
    Livro(7,  "Judg",   "Judges",        21, _padrao(7,  "Judges")),
    Livro(8,  "Ruth",   "Ruth",           4, _padrao(8,  "Ruth")),
    Livro(9,  "1Sam",   "1 Samuel",      31, _padrao(9,  "1Samuel")),
    Livro(10, "2Sam",   "2 Samuel",      24, _padrao(10, "2Samuel")),
    Livro(11, "1Kgs",   "1 Kings",       22, _padrao(11, "1Kings")),
    Livro(12, "2Kgs",   "2 Kings",       25, _padrao(12, "2Kings")),
    Livro(13, "1Chr",   "1 Chronicles",  29, _padrao(13, "1Chronicles")),
    Livro(14, "2Chr",   "2 Chronicles",  36, _padrao(14, "2Chronicles")),
    Livro(15, "Ezra",   "Ezra",          10, _padrao(15, "Ezra")),
    Livro(16, "Neh",    "Nehemiah",      13, _padrao(16, "Nehemiah")),
    Livro(17, "Esth",   "Esther",        10, _padrao(17, "Esther")),
    Livro(18, "Job",    "Job",           42, _padrao(18, "Job")),
    Livro(19, "Ps",     "Psalms",       150, "19_Psalm_{cap:03d}"),      # 3 dígitos
    Livro(20, "Prov",   "Proverbs",      31, _padrao(20, "Proverbs")),
    Livro(21, "Eccl",   "Ecclesiastes",  12, _padrao(21, "Ecclesiastes")),
    Livro(22, "Song",   "Song of Songs",  8, "22_Song_of_Soloman_{cap:02d}"),  # sic
    Livro(23, "Isa",    "Isaiah",        66, _padrao(23, "Isaiah")),
    Livro(24, "Jer",    "Jeremiah",      52, _padrao(24, "Jeremiah")),
    Livro(25, "Lam",    "Lamentations",   5, "25_Lamentations{cap:02d}"),  # sem _
    Livro(26, "Ezek",   "Ezekiel",       48, _padrao(26, "Ezekiel")),
    Livro(27, "Dan",    "Daniel",        12, _padrao(27, "Daniel")),
    Livro(28, "Hos",    "Hosea",         14, _padrao(28, "Hosea")),
    Livro(29, "Joel",   "Joel",           3, _padrao(29, "Joel")),
    Livro(30, "Amos",   "Amos",           9, _padrao(30, "Amos")),
    Livro(31, "Obad",   "Obadiah",        1, _padrao(31, "Obadiah")),
    Livro(32, "Jonah",  "Jonah",          4, _padrao(32, "Jonah")),
    Livro(33, "Mic",    "Micah",          7, _padrao(33, "Micah")),
    Livro(34, "Nah",    "Nahum",          3, _padrao(34, "Nahum")),
    Livro(35, "Hab",    "Habakkuk",       3, _padrao(35, "Habakkuk")),
    Livro(36, "Zeph",   "Zephaniah",      3, _padrao(36, "Zephaniah")),
    Livro(37, "Hag",    "Haggai",         2, _padrao(37, "Haggai")),
    Livro(38, "Zech",   "Zechariah",     14, _padrao(38, "Zechariah")),
    Livro(39, "Mal",    "Malachi",        4, _padrao(39, "Malachi")),
    # ── Novo Testamento ──────────────────────────────────────────────────────
    Livro(40, "Matt",   "Matthew",       28, "40_Matthew{cap:02d}"),      # sem _
    Livro(41, "Mark",   "Mark",          16, _padrao(41, "Mark")),
    Livro(42, "Luke",   "Luke",          24, _padrao(42, "Luke")),
    Livro(43, "John",   "John",          21, _padrao(43, "John")),
    Livro(44, "Acts",   "Acts",          28, _padrao(44, "Acts")),
    Livro(45, "Rom",    "Romans",        16, _padrao(45, "Romans")),
    Livro(46, "1Cor",   "1 Corinthians", 16, _padrao(46, "1Corinthians")),
    Livro(47, "2Cor",   "2 Corinthians", 13, _padrao(47, "2Corinthians")),
    Livro(48, "Gal",    "Galatians",      6, _padrao(48, "Galatians")),
    Livro(49, "Eph",    "Ephesians",      6, _padrao(49, "Ephesians")),
    Livro(50, "Phil",   "Philippians",    4, _padrao(50, "Philippians")),
    Livro(51, "Col",    "Colossians",     4, _padrao(51, "Colossians")),
    Livro(52, "1Thess", "1 Thessalonians", 5, _padrao(52, "1Thessalonians")),
    Livro(53, "2Thess", "2 Thessalonians", 3, _padrao(53, "2Thessalonians")),
    Livro(54, "1Tim",   "1 Timothy",      6, _padrao(54, "1Timothy")),
    Livro(55, "2Tim",   "2 Timothy",      4, _padrao(55, "2Timothy")),
    Livro(56, "Titus",  "Titus",          3, _padrao(56, "Titus")),
    Livro(57, "Phlm",   "Philemon",       1, _padrao(57, "Philemon")),
    Livro(58, "Heb",    "Hebrews",       13, _padrao(58, "Hebrews")),
    Livro(59, "Jas",    "James",          5, _padrao(59, "James")),
    Livro(60, "1Pet",   "1 Peter",        5, _padrao(60, "1Peter")),
    Livro(61, "2Pet",   "2 Peter",        3, _padrao(61, "2Peter")),
    Livro(62, "1John",  "1 John",         5, _padrao(62, "1John")),
    Livro(63, "2John",  "2 John",         1, _padrao(63, "2John")),
    Livro(64, "3John",  "3 John",         1, _padrao(64, "3John")),
    Livro(65, "Jude",   "Jude",           1, _padrao(65, "Jude")),
    Livro(66, "Rev",    "Revelation",    22, _padrao(66, "Revelation")),
)

# ── Códigos USFM (3 letras), na ordem canônica ───────────────────────────────
# É como o ebible.org nomeia os arquivos e como o marcador \id vem dentro
# deles. Tupla paralela a LIVROS: SIGLAS_USFM[i] é o código de LIVROS[i].
SIGLAS_USFM: tuple[str, ...] = (
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
)

# O Novo Testamento começa em Mateus -- usado pra escolher qual zip baixar.
PRIMEIRO_LIVRO_NT: int = 40

TOTAL_CAPITULOS: int = sum(l.capitulos for l in LIVROS)  # 1189

_POR_SIGLA = {l.sigla.lower(): l for l in LIVROS}
_POR_NUMERO = {l.numero: l for l in LIVROS}

assert len(LIVROS) == 66, f"esperava 66 livros, tem {len(LIVROS)}"
assert len(_POR_SIGLA) == 66, "sigla duplicada na tabela"
assert TOTAL_CAPITULOS == 1189, f"esperava 1189 capítulos, deu {TOTAL_CAPITULOS}"


def por_sigla(sigla: str) -> Livro:
    """Busca por sigla, sem diferenciar maiúscula: por_sigla("matt")."""
    chave = sigla.lower()
    if chave not in _POR_SIGLA:
        raise KeyError(f"sigla desconhecida: {sigla!r}")
    return _POR_SIGLA[chave]


def por_numero(numero: int) -> Livro:
    """Busca pela posição canônica: por_numero(40) -> Mateus."""
    if numero not in _POR_NUMERO:
        raise KeyError(f"número de livro fora de 1..66: {numero}")
    return _POR_NUMERO[numero]


def antigo_testamento() -> tuple[Livro, ...]:
    return tuple(l for l in LIVROS if l.numero < PRIMEIRO_LIVRO_NT)


def novo_testamento() -> tuple[Livro, ...]:
    return tuple(l for l in LIVROS if l.numero >= PRIMEIRO_LIVRO_NT)


def todos_capitulos(livros: tuple[Livro, ...] | None = None):
    """Gera (livro, capitulo) pra cada capítulo, na ordem canônica."""
    for livro in (livros if livros is not None else LIVROS):
        for cap in range(1, livro.capitulos + 1):
            yield livro, cap


# ── USFM <-> livro ───────────────────────────────────────────────────────────
assert len(SIGLAS_USFM) == 66, f"esperava 66 codigos USFM, tem {len(SIGLAS_USFM)}"
assert len(set(SIGLAS_USFM)) == 66, "codigo USFM duplicado"

_POR_USFM = {u: l for u, l in zip(SIGLAS_USFM, LIVROS)}


def usfm(livro: Livro) -> str:
    """Código USFM de 3 letras do livro: Mateus -> "MAT"."""
    return SIGLAS_USFM[livro.numero - 1]


def por_usfm(codigo: str) -> Livro:
    """Busca pelo código USFM, sem diferenciar maiúscula: por_usfm("mat")."""
    chave = codigo.strip().upper()
    if chave not in _POR_USFM:
        raise KeyError(f"código USFM desconhecido: {codigo!r}")
    return _POR_USFM[chave]
