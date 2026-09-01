# -*- coding: utf-8 -*-
"""
youtube_utils.py — Utilitários de download via yt-dlp (áudio dublado e
legendas do YouTube), compartilhados entre os notebooks de Language
Subtitles.

Concentra a lógica de runtime JS (Deno) + cookies que resolvemos por
tentativa e erro no projeto anterior:
  - O YouTube exige que o yt-dlp resolva desafios de JavaScript para
    enxergar TODAS as faixas (áudio dublado, legendas em outros idiomas).
    Sem isso, a lista de faixas fica truncada.
  - Deno é o runtime recomendado oficialmente pelo yt-dlp para isso — Node
    tem um bug conhecido em que --js-runtimes node é ignorado em várias
    versões recentes, por isso Deno vem primeiro, Node só como fallback.
  - IPs de datacenter (Colab incluso) são frequentemente bloqueados pelo
    YouTube ("Sign in to confirm you're not a bot") — cookies de uma sessão
    logada de verdade ajudam, mas não garantem 100%.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from config import PipelineConfig
from drive_utils import DriveClient

logger = logging.getLogger(__name__)


class YoutubeDownloadError(Exception):
    """Erro ao baixar algo do YouTube via yt-dlp."""


def garantir_yt_dlp_atualizado() -> None:
    """Atualiza o yt-dlp para a versão mais recente (necessário para os
    recursos de runtime JS usados abaixo)."""
    subprocess.run(["pip", "install", "-q", "-U", "yt-dlp"], capture_output=True, text=True)


def garantir_runtime_js() -> list[str]:
    """
    Garante um runtime JS disponível (Deno preferencialmente, Node como
    fallback) e retorna os argumentos extras para o yt-dlp.

    Retorna lista vazia se não conseguir nenhum runtime — nesse caso, o
    yt-dlp ainda funciona, mas a lista de faixas pode ficar truncada.
    """
    js_runtime: Optional[str] = None

    if shutil.which("deno"):
        js_runtime = "deno"
    else:
        instalar = subprocess.run(
            "curl -fsSL https://deno.land/install.sh | sh -s -- -y",
            shell=True, capture_output=True, text=True,
        )
        deno_bin = Path.home() / ".deno" / "bin"
        if (deno_bin / "deno").exists():
            import os
            os.environ["PATH"] = f"{deno_bin}:{os.environ.get('PATH', '')}"
            js_runtime = "deno"
        elif shutil.which("node"):
            js_runtime = "node"
            logger.warning(
                "Deno não instalou — usando Node como alternativa (pode não "
                "funcionar devido a um bug conhecido do yt-dlp com --js-runtimes node)."
            )
        else:
            logger.warning("Não foi possível instalar Deno nem achar Node. Detalhe: %s",
                            instalar.stderr[-300:] if instalar.stderr else "?")

    if not js_runtime:
        return []
    return ["--js-runtimes", js_runtime, "--remote-components", "ejs:github"]


# Argumentos fixos para contornar limitações atuais do YouTube em formatos
# áudio-only (comum em faixas de dublagem automática, menos comum na faixa
# original/mestre):
#   - formats=missing_pot: permite usar formatos que apareceriam ocultos
#     por exigirem "PO Token" (verificação anti-bot do YouTube)
#   - player_client=default,tv_downgraded: o client "default" às vezes não
#     lista as faixas de dublagem; "tv_downgraded" costuma expô-las quando
#     há cookies de uma conta logada (ver yt-dlp PO Token Guide)
# Isso é um alvo móvel do lado do YouTube — muda com frequência e pode não
# resolver 100% dos casos. Se mesmo assim continuar falhando para algum
# idioma específico, use FORMATO_MANUAL_AUDIO com o ID exato (via "-F").
ARGS_PO_TOKEN_WORKAROUND: list[str] = [
    "--extractor-args", "youtube:formats=missing_pot;player_client=default,tv_downgraded",
]


def resolver_cookies(config: PipelineConfig) -> Optional[Path]:
    """Copia o cookies.txt do Drive (config.pasta_assets/NOME_COOKIES) para
    local, se existir. Retorna o caminho local, ou None se não encontrado.

    SEMPRE baixa fresco do Drive (nunca reaproveita uma cópia local já
    existente) — se os cookies foram renovados no Drive durante a mesma
    sessão do Colab, isso garante que a versão nova seja usada, em vez de
    ficar preso numa cópia antiga/expirada que já estava em /content.
    """
    drive = DriveClient.get()
    cookies_drive = config.pasta_assets / config.NOME_COOKIES
    cookies_local = Path(config.NOME_COOKIES)
    if drive.download(config.pasta_assets, config.NOME_COOKIES, cookies_local):
        return cookies_local
    logger.warning("Nenhum cookies.txt encontrado em %s — seguindo sem cookies.", cookies_drive)
    return None


def _extra_args_cookies(cookies_path: Optional[Path]) -> list[str]:
    if cookies_path and cookies_path.exists():
        return ["--cookies", str(cookies_path)]
    return []


#: Uma vez que o YouTube diz "cookies no longer valid" nesta execução, todo
#: "Sign in to confirm" que vier depois é quase certamente o MESMO problema --
#: o yt-dlp só não repete a mensagem específica a cada chamada. Sem lembrar
#: disso, um lote de 4 idiomas sai com o primeiro dizendo "troque o cookie" e
#: os outros três dizendo "é o IP do Colab, espere" -- dois consertos opostos
#: pro mesmo defeito, e o conselho errado em 3 de 4.
_COOKIE_JA_ACUSADO_EXPIRADO = False

_TROQUE_O_COOKIE = (
    "Exporte um cookies.txt novo de uma aba REALMENTE logada em youtube.com "
    "(não uma aba em branco) e substitua o arquivo no Drive."
)


def _diagnosticar_stderr(stderr: str) -> Optional[str]:
    """Reconhece os erros mais comuns do yt-dlp e devolve uma mensagem
    acionável, ou None se não reconhecer nada específico."""
    global _COOKIE_JA_ACUSADO_EXPIRADO
    if "no longer valid" in stderr or "have likely been rotated" in stderr:
        _COOKIE_JA_ACUSADO_EXPIRADO = True
        return "Cookies expirados — o YouTube invalidou essa sessão. " + _TROQUE_O_COOKIE
    if "Sign in to confirm" in stderr:
        if _COOKIE_JA_ACUSADO_EXPIRADO:
            return (
                "Cookies expirados — o YouTube já acusou isso nesta execução, num "
                "idioma anterior. Este erro de 'bot' é o mesmo problema sem a "
                "mensagem específica; não é o IP do Colab. " + _TROQUE_O_COOKIE
            )
        return (
            "Bloqueio de bot do YouTube (comum em IPs de nuvem como o Colab). "
            "Antes de culpar o IP, confirme que o cookies.txt não venceu — "
            "cookie expirado dá exatamente este erro, muitas vezes sem a "
            "mensagem 'no longer valid'. Se o cookie está novo e mesmo assim "
            "persiste, aí sim é limitação do YouTube contra o IP do Colab."
        )
    if "Requested format is not available" in stderr:
        return (
            "Formato/faixa não encontrado. Causa mais provável: exigência de "
            "'PO Token' do YouTube para formatos áudio-only (comum em faixas "
            "de dublagem automática) — o formato aparece na listagem mas "
            "falha ao baixar. Já aplicamos o contorno padrão "
            f"(--extractor-args {ARGS_PO_TOKEN_WORKAROUND[1]}); se mesmo assim "
            "continuar falhando, pode ser instabilidade temporária da faixa "
            "em si — rode 'yt-dlp -F URL' de novo para conferir os IDs "
            "atuais, ou use formato_manual com o ID exato (ex: '251-11'). "
            "Se você acabou de atualizar youtube_utils.py, também vale "
            "REINICIAR O RUNTIME do Colab — o Python mantém módulos já "
            "importados em cache, então só substituir o arquivo no Drive "
            "não é suficiente na mesma sessão."
        )
    return None


def baixar_audio_idioma(
    url: str,
    lang: str,
    destino: Path,
    extra_args: list[str],
    cookies_path: Optional[Path],
    formato_manual: Optional[str] = None,
) -> bool:
    """Baixa a faixa de áudio dublado automático de um idioma específico.

    `formato_manual`: se informado, usa esse ID de formato exato (ex:
    "251-11", visto num "yt-dlp -F URL") em vez do filtro automático por
    idioma. Útil quando o filtro automático falha com "Requested format is
    not available" — as faixas de dublagem automática do YouTube às vezes
    ficam temporariamente indisponíveis/instáveis; rode "-F" de novo para
    conferir os IDs atuais antes de usar isso.

    Retorna True se conseguiu salvar em `destino`, False caso contrário
    (o motivo fica logado como warning, com diagnóstico quando reconhecido).
    """
    formato = formato_manual or f"ba[language^={lang}]/bestaudio[language^={lang}]"
    temp_saida = Path(f"temp_audio_{lang}.%(ext)s")

    cmd = [
        "yt-dlp", *extra_args, *ARGS_PO_TOKEN_WORKAROUND, *_extra_args_cookies(cookies_path),
        "-f", formato,
        "--extract-audio", "--audio-format", "wav",
        "-o", str(temp_saida),
        url,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)

    temp_wav = Path(f"temp_audio_{lang}.wav")
    if temp_wav.exists():
        temp_wav.replace(destino)
        return True

    diagnostico = _diagnosticar_stderr(resultado.stderr)
    if diagnostico:
        logger.warning("   ⚠️  [%s] %s", lang, diagnostico)
    else:
        logger.warning("   ⚠️  [%s] Falha ao baixar áudio: %s", lang, resultado.stderr[-300:])
    return False


def baixar_legenda_youtube(
    url: str,
    lang: str,
    destino: Path,
    extra_args: list[str],
    cookies_path: Optional[Path],
    codigo_youtube: Optional[str] = None,
) -> bool:
    """Baixa a legenda (manual ou automática) do YouTube para um idioma.

    `lang` é o código CANÔNICO do projeto (usado para nomear o arquivo e
    nas mensagens de log) — `codigo_youtube` é o código que o YouTube
    realmente usa para esse idioma nesse vídeo, se for diferente (ex: "zh"
    internamente vs "zh-Hans"/"zh-Hant" no YouTube). Se não informado, usa
    o próprio `lang`.

    Tenta legenda manual primeiro (--write-sub), cai para automática
    (--write-auto-sub) se não existir. Salva em formato SRT.

    Retorna True se conseguiu salvar em `destino`, False caso contrário.
    """
    codigo = codigo_youtube or lang
    prefixo = f"temp_legenda_{lang}"
    cmd = [
        "yt-dlp", *extra_args, *ARGS_PO_TOKEN_WORKAROUND, *_extra_args_cookies(cookies_path),
        "--skip-download",
        "--write-sub", "--write-auto-sub",
        "--sub-langs", codigo,
        "--sub-format", "srt",
        "-o", prefixo,
        url,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)

    candidatos = list(Path(".").glob(f"{prefixo}*.srt"))
    if candidatos:
        candidatos[0].replace(destino)
        for sobra in candidatos[1:]:
            sobra.unlink(missing_ok=True)
        return True

    diagnostico = _diagnosticar_stderr(resultado.stderr)
    if diagnostico:
        logger.warning("   ⚠️  [%s] %s", lang, diagnostico)
    else:
        logger.warning(
            "   ⚠️  [%s] Nenhuma legenda encontrada (manual ou automática) para o código "
            "'%s' neste idioma. Rode a célula de diagnóstico (--list-subs) para ver os "
            "códigos disponíveis nesse vídeo e ajuste CODIGO_LEGENDA_YOUTUBE se necessário.",
            lang, codigo,
        )
    return False
