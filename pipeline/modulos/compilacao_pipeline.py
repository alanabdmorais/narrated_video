# -*- coding: utf-8 -*-
"""
compilacao_pipeline.py — Corta e concatena áudio + roteiro de versículos
NÃO consecutivos de um capítulo já narrado, gerando um áudio compilado,
um SRT recalculado, e um manifesto (pra saber depois, na montagem de
vídeo, de qual versículo original cada trecho veio).

Testado com dados reais de 40_Matt_02 antes de virar notebook.
"""
from __future__ import annotations

import re
import subprocess
import json
import unicodedata
from pathlib import Path

PREFIXO_COMPILACAO = "comp"


def nome_compilacao(tema: str, prefixo: str = PREFIXO_COMPILACAO) -> str:
    """Transforma um tema editorial livre no nome de projeto da compilação.

        nome_compilacao("Salmos Esperança")  ->  "comp_salmos_esperanca"

    O tema é escolha sua e muda a cada vídeo -- não dá pra o código adivinhar,
    então ele vem da célula de Configuração. O que o código faz é só deixar o
    texto utilizável como nome de pasta e de arquivo: acento, cedilha, espaço e
    pontuação atravessam Drive, shell e linha de comando do ffmpeg, e cada um
    desses quebra de um jeito diferente e chato de diagnosticar.

    O prefixo separa compilação de capítulo. Sem ele, `salmos_esperanca` e
    `19_Ps_023` moram juntos em videos/ sem nada dizendo o que é o quê -- e uma
    compilação batizada por acaso com o nome de um capítulo sobrescreveria a
    pasta dele.
    """
    limpo = unicodedata.normalize("NFKD", tema)
    limpo = "".join(c for c in limpo if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", limpo).strip("_").lower()

    if not limpo:
        raise ValueError(
            f"O tema {tema!r} não sobrou nada depois de normalizar -- "
            f"use pelo menos uma letra ou número.")

    return f"{prefixo}_{limpo}" if prefixo else limpo


def conflita_com_capitulo(nome: str) -> bool:
    """O nome colide com o de algum dos 1189 capítulos da Bíblia?

    Serve pra célula de Configuração avisar antes de criar a pasta, não pra
    proibir. Com o prefixo padrão isso nunca acontece; a checagem existe pra
    quem passar `prefixo=""`.
    """
    try:
        import biblia_livros as bl
    except ImportError:
        return False
    # Sem diferenciar maiúscula: o normalizador devolve tudo minúsculo, e
    # "40_matt_02" contra "40_Matt_02" é a mesma pasta pra qualquer efeito
    # prático (o Drive e o macOS nem distinguem). Comparar sensível deixaria
    # passar exatamente a colisão que esta função existe pra pegar.
    alvo = nome.casefold()
    return any(livro.nome_projeto(cap).casefold() == alvo
               for livro, cap in bl.todos_capitulos())


def parsear_srt_por_versiculo(caminho_srt):
    """Lê um SRT tipo '..._versiculo_multilingue.srt' -- bloco N do SRT
    = versículo N (sequencial, sem pular número) -- devolve dict
    {versiculo: (inicio_s, fim_s)}."""
    with open(caminho_srt, encoding="utf-8") as f:
        conteudo = f.read()

    blocos = re.split(r"\n\n+", conteudo.strip())
    resultado = {}
    for i, bloco in enumerate(blocos, start=1):
        linhas = bloco.strip().split("\n")
        if len(linhas) < 2:
            continue
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})", linhas[1])
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        inicio = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        fim = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        resultado[i] = (inicio, fim)
    return resultado


def parsear_roteiro_versiculos(caminho_txt):
    """Lê o `..._roteiro_versiculos.txt` (formato 'N texto N texto...',
    número de versículo colado direto no texto, separado só por espaço
    ou quebra de linha) -- devolve dict {versiculo: texto}."""
    with open(caminho_txt, encoding="utf-8") as f:
        conteudo = f.read()

    marcadores = list(re.finditer(r"(?:^|(?<=[\s\n]))(\d{1,3})[ \t]", conteudo))
    resultado = {}
    for i, m in enumerate(marcadores):
        v = int(m.group(1))
        inicio_texto = m.end()
        fim_texto = marcadores[i + 1].start() if i + 1 < len(marcadores) else len(conteudo)
        texto = re.sub(r"\s+", " ", conteudo[inicio_texto:fim_texto].strip())
        resultado[v] = texto
    return resultado


def _formatar_tempo_srt(segundos):
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int(round((segundos - int(segundos)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def compilar_versiculos(caminho_audio, caminho_srt_versiculo, caminho_roteiro_txt,
                          livro_pt, capitulo, versiculos_alvo, pasta_saida,
                          nome_base="compilado"):
    """
    Corta e concatena os `versiculos_alvo` (lista de números, na ORDEM
    que você quer no compilado -- não precisa ser sequencial nem
    consecutiva) do áudio/roteiro de um capítulo já narrado.

    Gera 3 arquivos em `pasta_saida`:
    - {nome_base}.wav    -- áudio compilado
    - {nome_base}.srt    -- legenda recalculada (tempo do zero)
    - {nome_base}.json   -- manifesto: pra cada segmento do compilado,
      de qual (livro, capítulo, versículo) ORIGINAL ele veio -- usado
      depois pra montagem de vídeo, pra saber qual mídia buscar na
      biblioteca_match pra cada trecho.

    Devolve (caminho_audio, caminho_srt, caminho_manifesto).
    """
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_temp = pasta_saida / "_segmentos_temp"
    pasta_temp.mkdir(exist_ok=True)

    tempos_originais = parsear_srt_por_versiculo(caminho_srt_versiculo)
    textos = parsear_roteiro_versiculos(caminho_roteiro_txt)

    faltando = [v for v in versiculos_alvo if v not in tempos_originais or v not in textos]
    if faltando:
        raise ValueError(f"Versículo(s) não encontrado(s) no SRT ou no roteiro: {faltando}")

    segmentos, blocos_srt, manifesto = [], [], []
    tempo_acumulado = 0.0

    for i, v in enumerate(versiculos_alvo, start=1):
        inicio, fim = tempos_originais[v]
        duracao = fim - inicio
        arquivo_seg = pasta_temp / f"seg_{i:02d}_v{v}.wav"
        resultado = subprocess.run(
            ["ffmpeg", "-y", "-i", str(caminho_audio), "-ss", str(inicio), "-t", str(duracao),
             "-c", "copy", str(arquivo_seg)],
            capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou cortando versículo {v}: {resultado.stderr[-500:]}")
        segmentos.append(arquivo_seg)

        novo_inicio, novo_fim = tempo_acumulado, tempo_acumulado + duracao
        blocos_srt.append(f"{i}\n{_formatar_tempo_srt(novo_inicio)} --> {_formatar_tempo_srt(novo_fim)}\n{textos[v]}\n")
        manifesto.append({
            "segmento": i, "livro_pt": livro_pt, "capitulo": capitulo, "versiculo": v,
            "inicio_compilado_s": round(novo_inicio, 3), "fim_compilado_s": round(novo_fim, 3),
        })
        tempo_acumulado = novo_fim

    lista_concat = pasta_temp / "lista_concat.txt"
    with open(lista_concat, "w") as f:
        for s in segmentos:
            # caminho ABSOLUTO -- o demuxer concat do ffmpeg resolve
            # caminho relativo em relação à PASTA do próprio arquivo de
            # lista, não ao diretório de trabalho -- usar caminho
            # relativo aqui duplicava o prefixo da pasta (bug real que
            # apareceu no teste com dados reais)
            f.write(f"file '{s.resolve()}'\n")

    caminho_audio_final = pasta_saida / f"{nome_base}.wav"
    resultado = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista_concat), "-c", "copy", str(caminho_audio_final)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou concatenando: {resultado.stderr[-500:]}")

    caminho_srt_final = pasta_saida / f"{nome_base}.srt"
    with open(caminho_srt_final, "w", encoding="utf-8") as f:
        f.write("\n".join(blocos_srt))

    caminho_manifesto_final = pasta_saida / f"{nome_base}.json"
    with open(caminho_manifesto_final, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)

    for s in segmentos:
        s.unlink()
    lista_concat.unlink()
    pasta_temp.rmdir()

    return str(caminho_audio_final), str(caminho_srt_final), str(caminho_manifesto_final)
