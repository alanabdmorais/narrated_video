# -*- coding: utf-8 -*-
"""
tempos_cache.py — Guarda o tempo de cada versículo, por capítulo, pra sempre.

O áudio de um capítulo nunca muda, então o tempo dos versículos dele também
não. Transcrever com Whisper e alinhar custa minutos; reaproveitar custa
milissegundos. Uma compilação que usa Mateus 2 paga uma vez — a próxima que
repetir o capítulo não paga nada.

Um arquivo por capítulo em `assets/biblia_tempos/`, espelhando o
`assets/biblia_audio/`. Não é um JSON só porque o cache **cresce aos poucos**:
arquivo por capítulo grava só o que mudou, dá pra abrir e conferir um
capítulo isolado, e duas execuções em paralelo não brigam pelo mesmo arquivo.

## O ponto todo é a invalidação

Tempo de versículo é dado DERIVADO de duas entradas: o áudio e o texto de
referência. Se qualquer uma mudar, o tempo guardado está errado — e errado em
silêncio, porque um número continua sendo um número.

Por isso o que se guarda junto é a impressão digital das duas entradas, e o
cache **erra pro lado do miss**: entrada diferente = não achou, recalcula. Ele
nunca devolve tempo velho achando que serve.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

VERSAO_FORMATO = 1


@dataclass(frozen=True)
class Impressao:
    """Identidade das entradas que produziram os tempos."""
    audio_sha256: str
    texto_sha256: str
    modelo_whisper: str

    def bate_com(self, outra: "Impressao") -> tuple[bool, str]:
        """(igual?, motivo da diferença) — o motivo é o que torna um miss
        diagnosticável em vez de misterioso."""
        if self.audio_sha256 != outra.audio_sha256:
            return False, "o áudio do capítulo é outro arquivo"
        if self.texto_sha256 != outra.texto_sha256:
            return False, "o texto de referência mudou"
        if self.modelo_whisper != outra.modelo_whisper:
            return False, (f"transcrito com Whisper {outra.modelo_whisper!r}, "
                           f"agora pediram {self.modelo_whisper!r}")
        return True, ""


@dataclass
class TemposCapitulo:
    capitulo: str                 # "40_Matt_02"
    tempos: dict[int, int]        # {número do versículo: início em ms}
    fim_ms: int                   # fim do último versículo (= fim do áudio)
    impressao: Impressao
    calculado_em: str

    @property
    def versiculos(self) -> list[int]:
        return sorted(self.tempos)

    def intervalo(self, versiculo: int) -> tuple[int, int]:
        """(início_ms, fim_ms) de um versículo.

        O fim é o início do PRÓXIMO versículo — é assim que o corte de áudio
        fica sem buraco nem sobreposição entre versículos consecutivos. O
        último termina no fim do áudio.
        """
        ordenados = self.versiculos
        if versiculo not in self.tempos:
            raise KeyError(f"{self.capitulo} não tem tempo pro versículo {versiculo}")
        inicio = self.tempos[versiculo]
        pos = ordenados.index(versiculo)
        fim = self.tempos[ordenados[pos + 1]] if pos + 1 < len(ordenados) else self.fim_ms
        return inicio, fim


# ── Impressão digital ────────────────────────────────────────────────────────

def _sha256_arquivo(caminho: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for pedaco in iter(lambda: f.read(bloco), b""):
            h.update(pedaco)
    return h.hexdigest()


def _sha256_texto(texto: str) -> str:
    """Hash do texto com o espaço em branco normalizado.

    Sem normalizar, reformatar o roteiro (quebrar linha diferente) invalidaria
    o cache à toa -- o `alinhar_versiculos()` colapsa quebra de linha, então
    isso não muda tempo nenhum.
    """
    return hashlib.sha256(re.sub(r"\s+", " ", texto).strip().encode()).hexdigest()


def impressao_de(caminho_audio: Path | str, texto_referencia: str,
                 modelo_whisper: str) -> Impressao:
    return Impressao(
        audio_sha256=_sha256_arquivo(Path(caminho_audio)),
        texto_sha256=_sha256_texto(texto_referencia),
        modelo_whisper=modelo_whisper,
    )


# ── Leitura e escrita ────────────────────────────────────────────────────────

def caminho_de(pasta_cache: Path | str, capitulo: str) -> Path:
    return Path(pasta_cache) / f"{capitulo}.json"


def carregar(pasta_cache: Path | str, capitulo: str,
             impressao: Impressao | None = None) -> tuple[TemposCapitulo | None, str]:
    """Lê os tempos do capítulo -> (tempos, motivo).

    Devolve (None, motivo) quando não dá pra usar o que está guardado. Passe
    `impressao` pra validar contra as entradas atuais -- sem ela, lê sem
    conferir (útil só pra inspecionar).
    """
    caminho = caminho_de(pasta_cache, capitulo)
    if not caminho.exists():
        return None, "ainda não foi calculado"

    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return None, f"arquivo de cache ilegível ({e})"

    if bruto.get("versao_formato") != VERSAO_FORMATO:
        return None, (f"formato v{bruto.get('versao_formato')} do cache, "
                      f"o código lê v{VERSAO_FORMATO}")

    guardada = Impressao(**bruto["impressao"])
    if impressao is not None:
        igual, motivo = impressao.bate_com(guardada)
        if not igual:
            return None, motivo

    return TemposCapitulo(
        capitulo=bruto["capitulo"],
        tempos={int(k): int(v) for k, v in bruto["tempos"].items()},
        fim_ms=int(bruto["fim_ms"]),
        impressao=guardada,
        calculado_em=bruto["calculado_em"],
    ), "ok"


def salvar(pasta_cache: Path | str, capitulo: str, tempos: dict[int, int],
           fim_ms: int, impressao: Impressao) -> Path:
    """Grava os tempos de um capítulo. Cria a pasta se precisar."""
    if not tempos:
        raise ValueError(f"{capitulo}: nenhum tempo pra gravar")

    pasta = Path(pasta_cache)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = caminho_de(pasta, capitulo)

    caminho.write_text(json.dumps({
        "versao_formato": VERSAO_FORMATO,
        "capitulo": capitulo,
        "calculado_em": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "impressao": asdict(impressao),
        "fim_ms": int(fim_ms),
        "tempos": {str(k): int(v) for k, v in sorted(tempos.items())},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return caminho


# ── Visão geral ──────────────────────────────────────────────────────────────

def capitulos_no_cache(pasta_cache: Path | str) -> list[str]:
    pasta = Path(pasta_cache)
    if not pasta.exists():
        return []
    return sorted(p.stem for p in pasta.glob("*.json"))


def faltando(pasta_cache: Path | str, capitulos: list[str]) -> list[str]:
    """Quais desses capítulos ainda não têm tempo calculado.

    É o que o notebook de compilação usa pra te dizer, de uma vez, quais
    capítulos vão precisar de transcrição -- em vez de descobrir um por um no
    meio do processo.
    """
    ja = set(capitulos_no_cache(pasta_cache))
    return [c for c in capitulos if c not in ja]
