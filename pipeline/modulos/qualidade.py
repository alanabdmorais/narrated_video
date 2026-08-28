# -*- coding: utf-8 -*-
"""
qualidade.py — Portão de qualidade: confere o vídeo ANTES de publicar.

Existe por causa de uma família de bugs que o pipeline tem e que **não dá
erro nenhum** — só aparece no vídeo pronto:

  - idioma novo caindo no cinza de fallback em vez da cor da paleta
  - fonte sem o glifo do idioma, virando quadradinho (tofu) na tela
  - legenda posicionada fora da área segura
  - áudio estourando depois da mistura com trilha e efeito

Nenhum desses levanta exceção. Todos são baratos de detectar antes de subir.

Duas camadas, e a primeira é a que pega mais:

  verificar_ass()   -- estático, no .ass. Roda em milissegundos, antes de
                       queimar. Pega cor, fonte, posição e tempo.
  verificar_video() -- no .mp4 já queimado. Precisa de ffmpeg. Pega áudio
                       estourado, duração e resolução.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import cores


@dataclass
class Achado:
    gravidade: str   # "erro" (não publique) | "aviso" (olhe antes)
    categoria: str
    mensagem: str
    detalhe: str = ""

    def __str__(self) -> str:
        marca = "❌" if self.gravidade == "erro" else "⚠️ "
        linha = f"{marca} [{self.categoria}] {self.mensagem}"
        return f"{linha}\n     {self.detalhe}" if self.detalhe else linha


@dataclass
class Relatorio:
    achados: list[Achado] = field(default_factory=list)

    @property
    def erros(self) -> list[Achado]:
        return [a for a in self.achados if a.gravidade == "erro"]

    @property
    def avisos(self) -> list[Achado]:
        return [a for a in self.achados if a.gravidade == "aviso"]

    @property
    def aprovado(self) -> bool:
        return not self.erros

    def __str__(self) -> str:
        if not self.achados:
            return "✅ Nada a apontar."
        return "\n".join(str(a) for a in self.achados)


# ── .ass: leitura ────────────────────────────────────────────────────────────

_DIALOGUE = re.compile(r"^Dialogue:\s*[^,]*,([^,]+),([^,]+),([^,]*),", re.M)
_COR = re.compile(r"\\([13])c(&H[0-9A-Fa-f]{6,8})&?")
_POS = re.compile(r"\\pos\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")
_FONTE = re.compile(r"\\fn([^\\}]+)")
_TAGS = re.compile(r"\{[^}]*\}")


def _tempo_ms(t: str) -> int:
    h, m, s = t.strip().split(":")
    return int((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


def _ass_para_rgb(cor_ass: str) -> str:
    """&H00BBGGRR (ou &HBBGGRR) -> "#RRGGBB"."""
    h = cor_ass.upper().replace("&H", "")
    h = h[-6:].zfill(6)          # descarta o byte de alpha, se vier
    b, g, r = h[0:2], h[2:4], h[4:6]
    return f"#{r}{g}{b}"


@dataclass
class Bloco:
    inicio_ms: int
    fim_ms: int
    texto_visivel: str
    cores_rgb: list[str]
    posicao: tuple[float, float] | None
    fonte: str | None
    linha: int


def ler_ass(caminho: Path) -> tuple[dict, list[Bloco]]:
    """Lê o .ass -> (info_do_script, blocos)."""
    bruto = Path(caminho).read_text(encoding="utf-8-sig")

    info = {}
    for chave in ("PlayResX", "PlayResY"):
        m = re.search(rf"^{chave}:\s*(\d+)", bruto, re.M)
        if m:
            info[chave] = int(m.group(1))

    m = re.search(r"^Style:\s*Default\s*,\s*([^,]+)", bruto, re.M)
    info["fonte_padrao"] = m.group(1).strip() if m else None

    blocos: list[Bloco] = []
    for n, linha in enumerate(bruto.splitlines(), 1):
        if not linha.startswith("Dialogue:"):
            continue
        partes = linha.split(",", 9)
        if len(partes) < 10:
            continue
        _, inicio, fim = partes[0], partes[1], partes[2]
        texto = partes[9]
        m_pos = _POS.search(texto)
        m_fn = _FONTE.search(texto)
        blocos.append(Bloco(
            inicio_ms=_tempo_ms(inicio),
            fim_ms=_tempo_ms(fim),
            texto_visivel=_TAGS.sub("", texto).replace("\\N", " ").strip(),
            cores_rgb=[_ass_para_rgb(c) for _, c in _COR.findall(texto)],
            posicao=(float(m_pos.group(1)), float(m_pos.group(2))) if m_pos else None,
            fonte=m_fn.group(1).strip() if m_fn else None,
            linha=n,
        ))
    return info, blocos


# ── Fontes ───────────────────────────────────────────────────────────────────

def _resolver_fonte(nome: str) -> tuple[str, str] | None:
    """Pergunta ao fontconfig qual arquivo atende esse nome -> (familia, arquivo).

    ⚠️ O fc-match SEMPRE devolve alguma coisa: pedir "Noto Sans CJK SC" numa
    máquina sem ela devolve DejaVu, calado. Por isso devolvemos a família
    resolvida junto -- quem chama compara com o que pediu. É exatamente esse
    silêncio que faz o texto CJK virar quadradinho sem ninguém perceber.
    """
    try:
        saida = subprocess.run(
            ["fc-match", "-f", "%{family}|%{file}", nome],
            capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    if "|" not in saida:
        return None
    familia, arquivo = saida.split("|", 1)
    return familia.strip(), arquivo.strip()


def _glifos_da_fonte(arquivo: str) -> set[int] | None:
    """Codepoints que a fonte cobre. None se não der pra ler."""
    try:
        from fontTools.ttLib import TTFont, TTLibError
    except ImportError:
        return None
    try:
        cobertos: set[int] = set()
        fonte = TTFont(arquivo, fontNumber=0, lazy=True)
        for tabela in fonte["cmap"].tables:
            cobertos.update(tabela.cmap.keys())
        fonte.close()
        return cobertos
    except Exception:
        return None


# ── Verificação estática do .ass ─────────────────────────────────────────────

def verificar_ass(caminho: Path,
                  margem_segura: float = 0.05,
                  checar_fontes: bool = True) -> Relatorio:
    """Confere o .ass antes de queimar. Barato -- rode sempre."""
    rel = Relatorio()
    info, blocos = ler_ass(caminho)

    if not blocos:
        rel.achados.append(Achado("erro", "vazio", "O .ass não tem nenhum bloco Dialogue."))
        return rel

    # ── 1. Cores fora da paleta ──────────────────────────────────────────────
    # Válidas: as 21 da paleta + preto/branco do texto + o cinza da sigla de
    # livro (ffmpeg_utils o escreve fixo, não vem da paleta).
    validas = {c.upper() for c in cores.PALETA_EMOJI} | {"#000000", "#FFFFFF", "#808080"}
    fora: dict[str, list[int]] = {}
    for b in blocos:
        for cor in b.cores_rgb:
            if cor.upper() not in validas:
                fora.setdefault(cor.upper(), []).append(b.linha)

    if fora:
        amostra = ", ".join(
            f"{cor} ({len(linhas)}x, 1ª na linha {linhas[0]})"
            for cor, linhas in sorted(fora.items(), key=lambda kv: -len(kv[1]))[:6])
        rel.achados.append(Achado(
            "erro", "paleta",
            f"{len(fora)} cor(es) fora das 21 da paleta.",
            f"{amostra}\n     Cor fora da paleta não tem emoji — a legenda da "
            f"descrição do YouTube não consegue representar essa cor."))

    # ── 2. Fonte cobre os glifos usados? ─────────────────────────────────────
    if checar_fontes:
        rel.achados.extend(_conferir_fontes(info, blocos))

    # ── 3. Área segura ───────────────────────────────────────────────────────
    largura, altura = info.get("PlayResX"), info.get("PlayResY")
    if largura and altura:
        mx, my = largura * margem_segura, altura * margem_segura
        fora_area = [b for b in blocos if b.posicao and not
                     (mx <= b.posicao[0] <= largura - mx and my <= b.posicao[1] <= altura - my)]
        if fora_area:
            b = fora_area[0]
            rel.achados.append(Achado(
                "aviso", "area-segura",
                f"{len(fora_area)} bloco(s) posicionados fora da margem de "
                f"{margem_segura:.0%} ({largura}x{altura}).",
                f"1º na linha {b.linha}, em {b.posicao}"))

    # ── 4. Tempos ────────────────────────────────────────────────────────────
    ruins = [b for b in blocos if b.fim_ms <= b.inicio_ms]
    if ruins:
        b = ruins[0]
        rel.achados.append(Achado(
            "erro", "tempo",
            f"{len(ruins)} bloco(s) com duração zero ou negativa.",
            f"1º na linha {b.linha}: {b.inicio_ms}ms -> {b.fim_ms}ms"))

    # Sobreposição só conta DENTRO da mesma faixa da tela: o vídeo multi-idioma
    # empilha idiomas de propósito, e ali sobrepor no tempo é o esperado.
    por_faixa: dict[float, list[Bloco]] = {}
    for b in blocos:
        por_faixa.setdefault(b.posicao[1] if b.posicao else -1, []).append(b)
    sobrepostos = 0
    for faixa in por_faixa.values():
        faixa.sort(key=lambda b: b.inicio_ms)
        sobrepostos += sum(1 for a, b in zip(faixa, faixa[1:]) if b.inicio_ms < a.fim_ms)
    if sobrepostos:
        rel.achados.append(Achado(
            "aviso", "tempo",
            f"{sobrepostos} sobreposição(ões) de tempo na mesma faixa da tela.",
            "Dois blocos disputando o mesmo lugar piscam um por cima do outro."))

    # ── 5. Blocos sem texto ──────────────────────────────────────────────────
    vazios = [b for b in blocos if not b.texto_visivel]
    if vazios:
        rel.achados.append(Achado(
            "aviso", "vazio",
            f"{len(vazios)} bloco(s) sem texto visível.",
            f"1º na linha {vazios[0].linha}"))

    return rel


def _conferir_fontes(info: dict, blocos: list[Bloco]) -> list[Achado]:
    achados: list[Achado] = []
    fonte_padrao = info.get("fonte_padrao")

    # Junta os caracteres usados por fonte declarada.
    por_fonte: dict[str, set[str]] = {}
    for b in blocos:
        nome = b.fonte or fonte_padrao
        if not nome:
            continue
        por_fonte.setdefault(nome, set()).update(b.texto_visivel)

    for nome, caracteres in sorted(por_fonte.items()):
        resolvida = _resolver_fonte(nome)
        if resolvida is None:
            achados.append(Achado(
                "aviso", "fonte",
                f"Não deu pra resolver a fonte {nome!r} (fontconfig indisponível)."))
            continue

        familia, arquivo = resolvida
        substituiu = (nome.lower() not in familia.lower()
                      and familia.lower() not in nome.lower())

        cobertos = _glifos_da_fonte(arquivo)
        if cobertos is None:
            achados.append(Achado(
                "aviso", "fonte",
                f"Não deu pra ler os glifos de {nome!r} — instale fontTools "
                f"(`pip install fonttools`) pra esta checagem valer."))
            continue

        faltando = sorted(
            c for c in caracteres
            if not c.isspace() and ord(c) not in cobertos)

        # A gravidade vem do RESULTADO, não da substituição em si. O projeto
        # declara "Arial", que não existe em Linux/Colab -- o fontconfig troca
        # por Liberation Sans, que é metricamente compatível e cobre latim
        # inteiro. Se isso fosse erro, o portão gritaria em todo vídeo e você
        # aprenderia a ignorá-lo, que é pior que não ter portão. O que quebra
        # a tela é glifo faltando, e isso é erro sempre.
        if faltando:
            amostra = " ".join(f"{c}(U+{ord(c):04X})" for c in faltando[:12])
            origem = (f"{nome!r} não está instalada, o fontconfig caiu em "
                      f"{familia!r}, e essa") if substituiu else f"{nome!r}"
            achados.append(Achado(
                "erro", "fonte",
                f"{origem} não cobre {len(faltando)} caractere(s) da legenda.",
                f"{amostra}{' ...' if len(faltando) > 12 else ''}\n"
                f"     Cada um vira um quadradinho (tofu) na tela."))
        elif substituiu:
            achados.append(Achado(
                "aviso", "fonte",
                f"{nome!r} não está instalada — o fontconfig usa {familia!r}.",
                "Cobre todos os glifos usados, então a tela sai certa; o "
                "desenho das letras é que muda um pouco."))

    return achados


# ── Verificação do vídeo queimado ────────────────────────────────────────────

def verificar_video(caminho: Path,
                    duracao_esperada_ms: int | None = None,
                    tolerancia_ms: int = 2000) -> Relatorio:
    """Confere o .mp4 pronto. Precisa de ffmpeg/ffprobe no PATH."""
    rel = Relatorio()
    caminho = Path(caminho)

    if not caminho.exists():
        rel.achados.append(Achado("erro", "arquivo", f"Não existe: {caminho}"))
        return rel

    try:
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height,r_frame_rate",
             "-of", "default=noprint_wrappers=1", str(caminho)],
            capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError) as e:
        rel.achados.append(Achado("aviso", "ffprobe", f"ffprobe não rodou: {e}"))
        return rel

    campos = dict(l.split("=", 1) for l in saida.splitlines() if "=" in l)

    if "audio" not in saida:
        rel.achados.append(Achado("erro", "audio", "O vídeo não tem faixa de áudio."))

    if duracao_esperada_ms is not None and "duration" in campos:
        real_ms = int(float(campos["duration"]) * 1000)
        if abs(real_ms - duracao_esperada_ms) > tolerancia_ms:
            rel.achados.append(Achado(
                "erro", "duracao",
                f"Duração {real_ms/1000:.1f}s, esperava {duracao_esperada_ms/1000:.1f}s.",
                "Diferença grande costuma ser legenda cortada no fim ou "
                "concatenação incompleta."))

    # Áudio estourado: a mistura narração + trilha + efeito pode passar de 0 dB
    # e distorcer. volumedetect dá o pico do arquivo inteiro.
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", str(caminho), "-af", "volumedetect",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=600)
        m = re.search(r"max_volume:\s*(-?[\d.]+) dB", proc.stderr)
        if m:
            pico = float(m.group(1))
            if pico >= -0.1:
                rel.achados.append(Achado(
                    "erro", "audio",
                    f"Áudio no teto ({pico:+.1f} dB) — provável clipping.",
                    "Baixe VOLUME_MUSICA ou VOLUME_NARRACAO e remonte."))
            elif pico >= -1.0:
                rel.achados.append(Achado(
                    "aviso", "audio",
                    f"Áudio quase no teto ({pico:+.1f} dB)."))
            elif pico < -6.0:
                rel.achados.append(Achado(
                    "aviso", "audio",
                    f"Áudio baixo (pico {pico:+.1f} dB) — vai soar fraco."))
    except (OSError, subprocess.SubprocessError):
        rel.achados.append(Achado("aviso", "audio", "volumedetect não rodou."))

    return rel
