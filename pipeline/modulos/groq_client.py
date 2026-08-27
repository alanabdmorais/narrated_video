# -*- coding: utf-8 -*-
"""
groq_client.py — Cliente de IA com Mistral (primária) e Groq (fallback).

Versão enxuta, portada de oracao_v1/groq_client.py — traz só o que
Language Subtitles precisa (redistribuir texto nos blocos da legenda
mestre). Métodos de classificação morfológica/vocabulário litúrgico não
foram portados ainda — isso é responsabilidade de quando a etapa de
classificação (hoje inativa) for reconstruída neste projeto.

Fluxo de chamada:
  1. Tenta Mistral (mistral-small-latest) com delay entre chamadas.
  2. Se Mistral retornar rate limit (429), chama Groq imediatamente (sem delay).
  3. Se Groq também falhar com rate limit, aguarda e tenta novamente.
  4. Após max_tentativas falhas em ambas as APIs, lança GroqError.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GroqError(Exception):
    pass


# ── Configurações de API ──────────────────────────────────────────────────────

_APIS = [
    {
        "nome":     "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "model":    "mistral-small-latest",
        "key_attr": "_mistral_key",
    },
    {
        "nome":     "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model":    "llama-3.3-70b-versatile",
        "key_attr": "_groq_key",
    },
]

DELAY_ENTRE_CHAMADAS: float = 6.0   # segundos entre chamadas normais
MAX_TENTATIVAS: int = 3              # tentativas por API antes de desistir


def _is_rate_limit(exc: Exception) -> bool:
    """Retorna True se a exceção é de rate limit (429)."""
    msg = str(exc).lower()
    return "rate limit" in msg or "429" in msg or "too many" in msg


class GroqClient:
    """
    Cliente de IA com Mistral como primária e Groq como fallback.
    Use GroqClient.get() para obter o singleton (recomendado).
    """

    _instance: Optional["GroqClient"] = None

    def __init__(
        self,
        mistral_key: str = "",
        groq_key: str = "",
        nome_oracao: str = "",
        delay: float = DELAY_ENTRE_CHAMADAS,
        max_tentativas: int = MAX_TENTATIVAS,
    ) -> None:
        self._mistral_key = mistral_key
        self._groq_key = groq_key
        self.nome_oracao = nome_oracao
        self.delay = delay
        self.max_tentativas = max_tentativas
        self.model = _APIS[0]["model"]

        from openai import OpenAI
        self._clients: dict[str, object] = {}
        if mistral_key:
            self._clients["Mistral"] = OpenAI(
                api_key=mistral_key, base_url="https://api.mistral.ai/v1"
            )
        if groq_key:
            self._clients["Groq"] = OpenAI(
                api_key=groq_key, base_url="https://api.groq.com/openai/v1"
            )

        if not self._clients:
            raise GroqError("Nenhuma API key fornecida (MISTRAL_KEY ou GROQ_KEY)")

        nomes = list(self._clients.keys())
        logger.info("GroqClient inicializado: %s", " → ".join(nomes))

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get(
        cls,
        mistral_key: str = "",
        groq_key: str = "",
        nome_oracao: str = "",
    ) -> "GroqClient":
        """Retorna (ou cria) o singleton. Se já existir, retorna sem recriar."""
        if cls._instance is None:
            cls._instance = cls(
                mistral_key=mistral_key,
                groq_key=groq_key,
                nome_oracao=nome_oracao,
            )
        return cls._instance

    # ── Chamadas internas com fallback ────────────────────────────────────────

    def _call_text(
        self, user_prompt: str, system_prompt: str, max_tokens: int = 300
    ) -> str:
        """Chama Mistral (se disponível) → fallback Groq."""
        apis_ordem = [a for a in _APIS if a["nome"] in self._clients]

        for idx_api, api in enumerate(apis_ordem):
            client = self._clients[api["nome"]]
            model  = api["model"]

            for tentativa in range(1, self.max_tentativas + 1):
                try:
                    resposta = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=max_tokens,
                    )
                    texto = resposta.choices[0].message.content.strip()
                    logger.debug("_call_text: %s OK (%d tokens)", api["nome"], max_tokens)
                    time.sleep(self.delay)
                    return texto

                except Exception as exc:
                    if _is_rate_limit(exc):
                        logger.warning(
                            "%s rate limit — %s",
                            api["nome"],
                            "trocando para próxima API" if idx_api + 1 < len(apis_ordem)
                            else f"aguardando {self.delay}s antes de tentar novamente",
                        )
                        if idx_api + 1 < len(apis_ordem):
                            break
                        else:
                            time.sleep(self.delay)
                    else:
                        logger.warning(
                            "%s tentativa %d/%d: %s",
                            api["nome"], tentativa, self.max_tentativas, str(exc)[:80],
                        )
                        if tentativa < self.max_tentativas:
                            time.sleep(self.delay)

        raise GroqError("Falha após todas as tentativas em todas as APIs")

    def _call_json(
        self, user_prompt: str, system_prompt: str, max_tokens: int = 1000
    ) -> dict | list:
        """Idem a _call_text, mas parseia o resultado como JSON."""
        apis_ordem = [a for a in _APIS if a["nome"] in self._clients]

        for idx_api, api in enumerate(apis_ordem):
            client = self._clients[api["nome"]]
            model  = api["model"]

            for tentativa in range(1, self.max_tentativas + 1):
                try:
                    resposta = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt},
                        ],
                        temperature=0.1,
                        max_tokens=max_tokens,
                    )
                    texto = resposta.choices[0].message.content.strip()
                    logger.debug("_call_json: %s OK", api["nome"])
                    time.sleep(self.delay)
                    return self._parse_json(texto)

                except Exception as exc:
                    if _is_rate_limit(exc):
                        logger.warning(
                            "%s rate limit — %s",
                            api["nome"],
                            "trocando para próxima API" if idx_api + 1 < len(apis_ordem)
                            else f"aguardando {self.delay}s",
                        )
                        if idx_api + 1 < len(apis_ordem):
                            break
                        else:
                            time.sleep(self.delay)
                    else:
                        logger.warning(
                            "%s tentativa %d/%d: %s",
                            api["nome"], tentativa, self.max_tentativas, str(exc)[:80],
                        )
                        if tentativa < self.max_tentativas:
                            time.sleep(self.delay)

        raise GroqError("Falha após todas as tentativas em todas as APIs")

    # ── Métodos públicos ─────────────────────────────────────────────────────

    def redistribuir_texto(self, texto_corrido: str, textos_referencia: list[str], lang: str) -> list[str]:
        """
        Redistribui um texto contínuo em N partes, seguindo os cortes de
        conteúdo de `textos_referencia` (os textos da legenda mestre, na
        ordem). Não trunca o texto de entrada — o prompt é dimensionado
        para o tamanho real do conteúdo.

        Levanta GroqError se a IA falhar completamente (a decisão de
        ajustar/aceitar um número de partes diferente do esperado é do
        chamador — ver ajustar_para_n_partes em srt_utils.py).
        """
        n = len(textos_referencia)
        referencia_numerada = "\n".join(f"{i+1}. {t}" for i, t in enumerate(textos_referencia))

        PROMPT = (
            f"Você é um especialista em alinhamento de legendas multilíngues.\n\n"
            f"TEXTO COMPLETO EM {lang.upper()} (a ser dividido):\n{texto_corrido}\n\n"
            f"Abaixo está a mesma fala dividida em {n} blocos em outro idioma "
            f"(a REFERÊNCIA de onde cada bloco deve cortar, pelo CONTEÚDO/ordem, "
            f"não pela tradução literal palavra por palavra):\n\n{referencia_numerada}\n\n"
            f"Divida o texto em {lang.upper()} em EXATAMENTE {n} partes, na mesma "
            f"ordem, cada uma correspondendo ao conteúdo do bloco de mesma posição "
            f"na referência.\n\n"
            "REGRAS:\n"
            "- Mantenha a ordem original do texto\n"
            "- Não invente nem traduza do zero — use o texto fornecido, apenas divida\n"
            "- Não repita nem omita nenhuma palavra do texto original\n\n"
            f'Responda APENAS com JSON: {{"partes": ["parte1", "parte2", ..., "parte{n}"]}}'
        )
        resultado = self._call_json(PROMPT, "Especialista em alinhamento de legendas multilíngues", max_tokens=4000)
        partes = resultado.get("partes", []) if isinstance(resultado, dict) else []
        if not isinstance(partes, list):
            raise GroqError(f"Resposta da IA não é uma lista de partes: {resultado!r}")
        return partes

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_json(self, texto: str) -> dict | list:
        limpo = re.sub(r"```json|```", "", texto).strip()
        try:
            return json.loads(limpo)
        except json.JSONDecodeError:
            match = re.search(r"(\[.*\]|\{.*\})", limpo, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise GroqError(f"JSON inválido: {limpo[:200]}")
