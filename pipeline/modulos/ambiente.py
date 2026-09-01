# -*- coding: utf-8 -*-
"""
ambiente.py — o ambiente do Colab é o que este notebook precisa?

Existe por causa de um custo real: a cota de GPU do Colab é limitada e some
sem aviso. Em 01/set o ambiente parou de ser concedido no meio do teste do
Mateus 2 -- "não há back-ends disponíveis" --, e parte da cota tinha sido
gasta em notebooks que não usam GPU pra nada, rodando num ambiente com GPU
só porque a seleção ficou de antes.

A própria documentação do Colab recomenda voltar pra CPU quando não se está
usando o acelerador. O problema é que ninguém lembra, porque nada avisa.
"""
from __future__ import annotations

import shutil


def tem_gpu() -> bool:
    """Este ambiente tem GPU disponível de verdade?"""
    try:
        import torch                     # noqa: PLC0415
        return bool(torch.cuda.is_available())
    except Exception:
        # Sem torch instalado ainda: o nvidia-smi denuncia a máquina.
        return shutil.which("nvidia-smi") is not None


def avisar_gpu(precisa: bool) -> None:
    """Imprime um aviso quando o ambiente não combina com o que o notebook faz.

    Silencioso quando combina -- aviso que aparece sempre vira paisagem.
    """
    gpu = tem_gpu()
    if precisa and not gpu:
        print("   ⚠️  Este notebook roda Whisper e está SEM GPU. Vai funcionar,")
        print("      mas leva muito mais tempo. Ambiente de execução →")
        print("      Alterar o tipo → GPU, e rode esta célula de novo.")
    elif not precisa and gpu:
        print("   💡 Este notebook não usa GPU, e você está num ambiente COM GPU.")
        print("      Trocar pra CPU não muda nada aqui e poupa sua cota — que é")
        print("      limitada e some sem aviso (Ambiente de execução →")
        print("      Alterar o tipo → Nenhum).")
