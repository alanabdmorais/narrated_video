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


# ─────────────────────────────────────────────────────────────────────────────
# Compilação ATRAVÉS de capítulos (versículos sortidos da Bíblia inteira)
#
# A compilar_versiculos() acima trabalha dentro de UM capítulo e depende de um
# SRT por versículo. Aqui a seleção atravessa livros, e os tempos vêm do
# tempos_cache -- que já sabe dizer quais capítulos ainda faltam calcular.
# ─────────────────────────────────────────────────────────────────────────────

def parsear_selecao(selecao):
    """Lê a seleção escrita na Configuração -> [(Livro, capítulo, [versículos])].

        [("Ps", 23, "1-3"), ("Ps", 42, "5"), ("Isa", 40, "31")]

    Aceita "1-3", "5", "1-3,6,9-11" ou uma lista de int. A ordem é a que você
    escreveu -- é ela que vira a ordem do vídeo, e não precisa ser sequencial.

    Valida contra a tabela canônica: livro inexistente ou versículo fora do
    capítulo quebram aqui, na leitura da config, e não vinte minutos depois no
    meio do corte.
    """
    import biblia_livros as bl

    itens = []
    for entrada in selecao:
        sigla, capitulo, versiculos = entrada
        livro = bl.por_sigla(sigla)
        if not 1 <= capitulo <= livro.capitulos:
            raise ValueError(
                f"{livro.nome} tem {livro.capitulos} capítulos; pediram {capitulo}")

        if isinstance(versiculos, str):
            numeros = []
            for pedaco in versiculos.split(","):
                pedaco = pedaco.strip()
                if not pedaco:
                    continue
                if "-" in pedaco:
                    ini, fim = (int(x) for x in pedaco.split("-", 1))
                    if fim < ini:
                        raise ValueError(f"Intervalo invertido: {pedaco!r}")
                    numeros.extend(range(ini, fim + 1))
                else:
                    numeros.append(int(pedaco))
        else:
            numeros = [int(v) for v in versiculos]

        if not numeros:
            raise ValueError(f"{livro.nome} {capitulo}: nenhum versículo na seleção")
        itens.append((livro, capitulo, numeros))
    return itens


def capitulos_da_selecao(itens):
    """Nomes de capítulo (40_Matt_02) da seleção, sem repetir, na ordem."""
    vistos, saida = set(), []
    for livro, capitulo, _ in itens:
        nome = livro.nome_projeto(capitulo)
        if nome not in vistos:
            vistos.add(nome)
            saida.append(nome)
    return saida


def _cortar_segmento(caminho_audio, inicio_ms, fim_ms, destino,
                     taxa=44100, canais=1):
    """Corta um trecho e NORMALIZA o formato.

    Dois motivos pra decodificar em vez de `-c copy`:

    1. A fonte é mp3, e corte por cópia gruda na fronteira do frame (~26 ms):
       a emenda entre versículos sai torta, com clique ou pedaço repetido.
    2. O concat por cópia exige que todos os segmentos tenham o MESMO codec,
       taxa e número de canais. Como a seleção atravessa capítulos (arquivos
       diferentes, possivelmente gravados/codificados em épocas diferentes),
       normalizar aqui é o que garante que a junção depois funcione.

    `-ss` e `-t` vêm DEPOIS do `-i` de propósito: seek exato, à custa de ler o
    arquivo até o ponto. Capítulo tem poucos minutos, então o custo é baixo e
    a precisão é o que mantém o versículo inteiro dentro do corte.
    """
    duracao_s = (fim_ms - inicio_ms) / 1000.0
    if duracao_s <= 0:
        raise ValueError(f"Duração inválida: {inicio_ms}ms -> {fim_ms}ms")

    resultado = subprocess.run(
        ["ffmpeg", "-y", "-i", str(caminho_audio),
         "-ss", f"{inicio_ms / 1000.0:.3f}", "-t", f"{duracao_s:.3f}",
         "-ar", str(taxa), "-ac", str(canais), "-c:a", "pcm_s16le",
         str(destino)],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falhou cortando {Path(caminho_audio).name} "
            f"[{inicio_ms}-{fim_ms}ms]: {resultado.stderr[-400:]}")
    return destino


def compilar_selecao(itens, pasta_audio, pasta_cache, texto_de, pasta_saida,
                     nome_base, taxa=44100, canais=1):
    """Corta e concatena versículos de capítulos DIFERENTES.

    Args:
        itens:       saída de parsear_selecao()
        pasta_audio: onde estão os mp3 por capítulo (assets/biblia_audio)
        pasta_cache: onde estão os tempos (assets/biblia_tempos)
        texto_de:    função (livro, capitulo, versiculo) -> str, pro SRT
        pasta_saida: onde gravar
        nome_base:   nome dos três arquivos de saída

    Gera {nome_base}.wav, .srt e .json (manifesto: de qual versículo original
    veio cada trecho do compilado -- é o que a montagem de vídeo usa depois
    pra achar a mídia certa de cada trecho).
    """
    import tempos_cache as tc

    pasta_audio, pasta_cache = Path(pasta_audio), Path(pasta_cache)
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_temp = pasta_saida / "_segmentos_temp"
    pasta_temp.mkdir(exist_ok=True)

    # Carrega o cache de cada capítulo ANTES de cortar qualquer coisa: melhor
    # falhar apontando o que falta do que parar na metade com arquivos soltos.
    tempos_por_capitulo = {}
    for nome in capitulos_da_selecao(itens):
        guardado, motivo = tc.carregar(pasta_cache, nome)
        if guardado is None:
            raise ValueError(f"Sem tempos pra {nome}: {motivo}")
        tempos_por_capitulo[nome] = guardado

    segmentos, blocos_srt, manifesto = [], [], []
    acumulado_s, indice = 0.0, 0

    try:
        for livro, capitulo, versiculos in itens:
            nome_cap = livro.nome_projeto(capitulo)
            audio = pasta_audio / f"{nome_cap}.mp3"
            if not audio.exists():
                raise FileNotFoundError(f"Áudio não encontrado: {audio}")
            guardado = tempos_por_capitulo[nome_cap]

            for v in versiculos:
                indice += 1
                inicio_ms, fim_ms = guardado.intervalo(v)
                destino = pasta_temp / f"seg_{indice:03d}_{nome_cap}_v{v}.wav"
                _cortar_segmento(audio, inicio_ms, fim_ms, destino, taxa, canais)
                segmentos.append(destino)

                duracao_s = (fim_ms - inicio_ms) / 1000.0
                ini_s, fim_s = acumulado_s, acumulado_s + duracao_s
                blocos_srt.append(
                    f"{indice}\n{_formatar_tempo_srt(ini_s)} --> "
                    f"{_formatar_tempo_srt(fim_s)}\n{texto_de(livro, capitulo, v)}\n")
                manifesto.append({
                    "segmento": indice,
                    "capitulo": nome_cap,
                    "livro": livro.nome,
                    "sigla": livro.sigla,
                    "numero_capitulo": capitulo,
                    "versiculo": v,
                    "origem_inicio_ms": inicio_ms,
                    "origem_fim_ms": fim_ms,
                    "inicio_compilado_s": round(ini_s, 3),
                    "fim_compilado_s": round(fim_s, 3),
                })
                acumulado_s = fim_s

        if not segmentos:
            raise ValueError("A seleção não produziu nenhum segmento.")

        lista_concat = pasta_temp / "lista_concat.txt"
        with open(lista_concat, "w", encoding="utf-8") as f:
            for s in segmentos:
                # Caminho ABSOLUTO: o demuxer concat resolve caminho relativo
                # em relação à pasta do arquivo de lista, não ao diretório de
                # trabalho -- relativo aqui duplica o prefixo da pasta.
                f.write(f"file '{s.resolve()}'\n")

        caminho_audio_final = pasta_saida / f"{nome_base}.wav"
        resultado = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(lista_concat), "-c", "copy", str(caminho_audio_final)],
            capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou concatenando: {resultado.stderr[-400:]}")

        caminho_srt = pasta_saida / f"{nome_base}.srt"
        caminho_srt.write_text("\n".join(blocos_srt), encoding="utf-8")

        caminho_manifesto = pasta_saida / f"{nome_base}.json"
        caminho_manifesto.write_text(
            json.dumps({
                "nome": nome_base,
                "segmentos": len(manifesto),
                "duracao_s": round(acumulado_s, 3),
                "trechos": manifesto,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

        return str(caminho_audio_final), str(caminho_srt), str(caminho_manifesto)

    finally:
        # Limpa o temporário mesmo se algo estourou no meio -- senão a próxima
        # execução acha segmento velho de uma tentativa que deu errado.
        for s in segmentos:
            s.unlink(missing_ok=True)
        for resto in pasta_temp.glob("*"):
            resto.unlink(missing_ok=True)
        if pasta_temp.exists():
            pasta_temp.rmdir()
