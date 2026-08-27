# -*- coding: utf-8 -*-
"""
whisper_utils.py — Carrega o modelo Whisper com detecção automática de GPU.

Usado por caption_pipeline.py (Single Subtitle) e language_captions_pipeline.py
(Language Subtitles) — centraliza a lógica de device para não duplicar.

No Colab, para ativar GPU: Ambiente de execução → Alterar tipo de ambiente
de execução → Acelerador de hardware → GPU (T4 no plano gratuito). Sem
isso, o Whisper roda normalmente na CPU — só mais devagar (pode ser bem
mais devagar em modelos maiores, tipo "small"/"medium").
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detectar_device() -> str:
    """Retorna 'cuda' se houver GPU disponível, senão 'cpu'."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def carregar_modelo_whisper(modelo: str):
    """
    Carrega o modelo Whisper, usando GPU (CUDA) automaticamente se
    disponível — senão cai para CPU (mais lento, mas funciona igual, sem
    precisar mudar nada no código ou na configuração).
    """
    import whisper

    device = detectar_device()
    if device == "cuda":
        try:
            import torch
            logger.info("🚀 GPU detectada: %s — Whisper vai rodar nela", torch.cuda.get_device_name(0))
        except Exception:
            logger.info("🚀 GPU detectada — Whisper vai rodar nela")
    else:
        logger.info(
            "── Nenhuma GPU disponível — Whisper vai rodar na CPU (mais lento). "
            "No Colab: Ambiente de execução → Alterar tipo de ambiente de execução "
            "→ Acelerador de hardware → GPU."
        )

    logger.info("── Whisper: carregando modelo '%s' (device=%s)", modelo, device)
    return whisper.load_model(modelo, device=device)
