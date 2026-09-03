# -*- coding: utf-8 -*-
"""
config.py — Configuração centralizada do pipeline (projeto Narrated Video).

Estrutura de pastas no Drive:
    narrated_video/
    ├── pipeline/modulos/          ← módulos genéricos (nunca muda)
    ├── pipeline/notebooks/        ← notebooks genéricos (nunca muda)
    ├── assets/
    │   ├── clipes/                ← clipes Pixabay reutilizáveis entre vídeos
    │   ├── logo/                  ← logomarca
    │   └── musica/                ← trilha sonora
    └── videos/
        └── 40_matt_02/            ← TUDO do vídeo, identificado pelo prefixo
            ├── 40_matt_02_audio.wav
            ├── 40_matt_02_video_base.mp4
            └── ...

Para adicionar novo vídeo: só mudar NOME_ORACAO e TEXTO_ORACAO na célula de
configuração do notebook (o nome do campo é NOME_ORACAO por herança do
projeto original — na prática representa o nome/identificador do vídeo).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from constants import (
    IDIOMAS, SIGLAS_IDIOMAS, POSICOES_Y, POS_SIGLA_Y,
    CORES_HTML, TEXTO_PRETO, LARGURA_TELA, ALTURA_TELA,
    TAMANHO_FONTE_TAG, TAMANHO_FONTE_SIGLA, BOX_BORDER,
    ESPACAMENTO_PALAVRA, LARGURA_CHAR,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """
    Configuração completa do pipeline.

    Para trocar de oração: altere apenas NOME_ORACAO e TEXTO_ORACAO.
    PASTA_DRIVE_RAIZ é fixo para todo o projeto ("oracao_v1").
    """

    # ── Identidade da oração ──────────────────────────────────────────────────
    NOME_ORACAO: str = "pai_nosso"

    # ── Pasta raiz no Google Drive ────────────────────────────────────────────
    # Fixo para todo o projeto — não muda entre vídeos
    PASTA_DRIVE_RAIZ: str = "narrated_video"

    # ── Texto para Edge TTS ───────────────────────────────────────────────────
    TEXTO_ORACAO: str = (
        "Pai Nosso que estais no céu,\n"
        "santificado seja o vosso nome.\n"
        "Venha a nós o vosso reino.\n"
        "Seja feita a vossa vontade,\n"
        "assim na terra como no céu.\n"
        "O pão nosso de cada dia nos dai hoje.\n"
        "Perdoai as nossas ofensas,\n"
        "assim como nós perdoamos a quem nos tem ofendido.\n"
        "E não nos deixeis cair em tentação,\n"
        "mas livrai-nos do mal. Amém."
    )

    # ── Voz e idiomas ─────────────────────────────────────────────────────────
    VOZ_EDGE: str = "pt-BR-AntonioNeural"
    IDIOMAS: list[str] = field(default_factory=lambda: IDIOMAS.copy())

    # ── IDs do Google Drive ───────────────────────────────────────────────────
    # Planilha Pixabay de VÍDEOS (compartilhada entre orações)
    ID_PLANILHA_DRIVE: str = "1bF7hnGSY7AALm4ZAS5owWNpiSTdgArW4ahAuVZaHPL0"
    # Como encaixar uma foto cuja proporção não é a do vídeo:
    #   "preencher"  amplia até cobrir e corta o que sobra  (padrão)
    #   "caber"      encolhe até caber e completa com preto
    # Ver ffmpeg_utils.imagem_para_clipe. Fundo existe pra ocupar a tela;
    # "caber" punha tarja preta na lateral de quase toda foto.
    ENQUADRAMENTO_IMAGEM: str = "preencher"

    # Descartar da planilha as fotos em pé (formato celular). Mesmo com
    # "preencher", uma foto 1080x1920 num quadro 16:9 perde ~2/3 da altura --
    # e o que sobra costuma ser o meio de uma pessoa, sem a cabeça. Usa as
    # colunas Largura/Altura da planilha; linha sem essas colunas passa, que
    # é o certo: não dá pra descartar pelo que não se sabe.
    DESCARTAR_IMAGEM_RETRATO: bool = True

    # Planilha Pixabay de IMAGENS (usada só quando MODO_CLIPE="imagem")
    ID_PLANILHA_IMAGENS_DRIVE: str = ""
    # Nome da coluna de status nas duas planilhas (marca quando cada linha foi usada)
    NOME_COLUNA_STATUS_PLANILHA: str = "Downloading Ok"
    # Cookies YouTube
    ID_PASTA_COOKIES:  str = "1ZuxVr-pofA-Naqo8ysfGxWpYjSaSt3aE"

    # ── Assets externos ───────────────────────────────────────────────────────
    NOME_ARQUIVO_LOGO:   str = "globo_cruz_logo.png"
    # Imagem mestre do canal (fundo da versão em miniatura), compartilhada
    # entre vídeos -- mora em assets/marca, ao lado do logo. Um vídeo pode ter
    # a sua própria (ver nome_imagem_mestre), que tem preferência.
    NOME_IMAGEM_MESTRE_PADRAO: str = "imagem_mestre.png"
    NOME_ARQUIVO_MUSICA: str = (
        "Calmo créditos Shattered Paths - Aakash Gandhi(Youtube Audio Library).mp3"
    )
    NOME_COOKIES: str = "cookies.txt"

    # ── Modo dos clipes de fundo: vídeo (padrão) ou imagem estática ───────────
    # "video"  → comportamento atual, corta clipes de vídeo do Pixabay.
    # "imagem" → usa fotos do Pixabay (ID_PLANILHA_IMAGENS_DRIVE), cada uma
    #            virando um segmento de DURACAO_CLIPE segundos — melhor para
    #            vídeos de estudo com muitas legendas simultâneas na tela
    #            (menos movimento de fundo compete com a leitura).
    MODO_CLIPE: str = "video"
    # Sufixo adicionado ao vídeo base e final quando MODO_CLIPE="imagem" — os
    # dois modos podem coexistir na mesma pasta sem um sobrescrever o outro.
    SUFIXO_MODO_IMAGEM: str = "_img"

    # ── Modo de roteiro: com versículo ou padrão ───────────────────────────────
    # Independente de MODO_CLIPE (vídeo/imagem) -- os dois são combináveis.
    # "versiculo" (padrão) → nome_palavras_mestre aponta pro roteiro COM
    #            números de versículo soltos no meio do texto
    #            (nome_roteiro_versiculos) -- usado pelos notebooks
    #            video-base-*-versiculo.ipynb.
    # "padrao"   → aponta pro roteiro normal, sem versículo (nome_roteiro) --
    #            usado pelos notebooks video-base-*-padrao.ipynb.
    MODO_ROTEIRO: str = "versiculo"

    # ── Parâmetros de vídeo ───────────────────────────────────────────────────
    # ── Montagem automática de clipe/imagem por versículo ─────────────────────
    # Segmentos mais curtos que isso (versículo muito breve) são absorvidos
    # pelo vizinho em vez de virar um corte de clipe próprio -- evita flicker
    # de trocar de cena a cada 1-2s.
    DURACAO_MINIMA_SEGMENTO_VERSICULO: float = 2.0

    DURACAO_CLIPE:   int   = 5
    TAMANHO_LOGO:    int   = 80
    VOLUME_NARRACAO: float = 1.0    # volume da voz/narração (1.0 = original)
    VOLUME_MUSICA:   float = 0.25   # volume da trilha sonora, relativo à narração
    VELOCIDADE_AUDIO: float = 1.0   # velocidade da narração (1.0 = original; 0.9 = 10% mais devagar)
    GROQ_MODEL:      str   = "llama-3.3-70b-versatile"

    # ── Normalização dos clipes (CORREÇÃO DO BUG DE DURAÇÃO) ──────────────────
    # Clipes do Pixabay vêm de autores diferentes, cada um com sua própria
    # resolução e taxa de quadros (fps). Concatenar clipes com parâmetros
    # DIFERENTES sem re-padronizar corrompe a duração do vídeo final de forma
    # silenciosa (o ffmpeg não trava, só gera timestamps errados). Por isso,
    # TODO clipe é re-padronizado pra essa resolução/fps antes de concatenar.
    LARGURA_CLIPE: int = 1280
    ALTURA_CLIPE:  int = 720
    FPS_CLIPE:     int = 25

    # ── Idioma mestre ─────────────────────────────────────────────────────────
    # Idioma do áudio/roteiro que serve de mestre de TIMESTAMPS (Whisper roda
    # nesse idioma) e de TEXTO (roteiro.txt ou legenda do YouTube nesse mesmo
    # idioma). Os outros idiomas são redistribuídos em cima desse molde.
    #
    # Continua sendo variável -- qualquer notebook passa outro valor. O padrão
    # é "en" porque a Bíblia poliglota é o uso corrente e a narração dela é a
    # do David Williams, em inglês. Errar esse valor não dá erro: as três
    # funções que baixam/transcrevem PULAM o idioma mestre de propósito (ele já
    # foi resolvido no caption-single-generate), então um "pt" esquecido aqui
    # protegeria o idioma errado -- pularia o português e sobrescreveria a
    # legenda inglesa corrigida à mão. Falha silenciosa e cara de desfazer.
    IDIOMA_MESTRE:   str   = "en"

    # ── Cores por idioma (modo simples — 1 cor por idioma) ───────────────────
    CORES_IDIOMAS: dict[str, str] = None  # preenchido no __post_init__

    def __post_init__(self):
        if self.CORES_IDIOMAS is None:
            # Cores tiradas da paleta emoji de cores.py (PALETA_EMOJI), pra
            # dar pra sinalizar cada idioma na descrição do YouTube — mesmo
            # critério da legenda multicor. Cada idioma manteve sua cor de
            # sempre, só migrada pro tom equivalente da paleta.
            # A ordem importa: os idiomas ficam EMPILHADOS na tela (POSICOES_Y
            # 100→500), então vizinhos não podem se parecer. Por isso o chinês
            # é roxo 🟣 e não lilás 🪻 — lilás encostaria no rosa 🩷 do
            # coreano, que é a linha logo acima dele.
            # Listado na ordem em que aparece na tela (ver POSICOES_Y):
            # inglês no topo, por ser o idioma anfitrião.
            object.__setattr__(self, 'CORES_IDIOMAS', {
                'en': '#66BB6A',   # 💚 verde claro
                'pt': '#FFFF00',   # 🟡 amarelo
                'es': '#FFA500',   # 🟠 laranja
                'fr': '#87CEEB',   # 🩵 azul claro
                'ko': '#FF69B4',   # 🩷 rosa
                'zh': '#800080',   # 🟣 roxo
            })

    # ── Layout de legenda ─────────────────────────────────────────────────────
    POSICOES_Y:          dict[str, int] = field(default_factory=lambda: POSICOES_Y.copy())
    POS_SIGLA_Y:         dict[str, int] = field(default_factory=lambda: POS_SIGLA_Y.copy())
    SIGLAS_IDIOMAS:      dict[str, str] = field(default_factory=lambda: SIGLAS_IDIOMAS.copy())
    CORES_HTML:          dict[str, str] = field(default_factory=lambda: CORES_HTML.copy())
    TEXTO_PRETO:         set[str]       = field(default_factory=lambda: TEXTO_PRETO.copy())
    LARGURA_TELA:        int = LARGURA_TELA
    ALTURA_TELA:         int = ALTURA_TELA
    TAMANHO_FONTE_TAG:   int = TAMANHO_FONTE_TAG
    TAMANHO_FONTE_SIGLA: int = TAMANHO_FONTE_SIGLA
    FONTE_CJK:           str = "Noto Sans CJK KR"  # fonte p/ coreano (Arial não cobre bem o Hangul;
                                                      # a família "Noto Sans CJK" cobre chinês/japonês/
                                                      # coreano — troque o sufixo se precisar de outro idioma)

    # ── Quais idiomas precisam de fonte CJK, e qual variante ──────────────────
    # Arial (fonte padrão do estilo ASS) não cobre Hangul nem Han: sem uma
    # fonte CJK explícita o texto vira quadradinhos (□) ou some. As variantes
    # regionais da família Noto Sans CJK compartilham os mesmos caracteres e
    # diferem só no traçado de alguns Han (unificação Han) -- por isso o
    # chinês usa a variante SC (simplificado) em vez da KR do coreano.
    # Idiomas fora de IDIOMAS_CJK usam a fonte padrão do estilo (latinos).
    IDIOMAS_CJK: set[str] = field(default_factory=lambda: {"ko", "zh"})
    # Override por idioma; quem não estiver aqui (ex: "ko") cai em FONTE_CJK,
    # preservando qualquer customização feita naquele campo.
    FONTE_CJK_POR_IDIOMA: dict[str, str] = field(default_factory=lambda: {
        "zh": "Noto Sans CJK SC",
    })

    def fonte_cjk(self, lang: str) -> str:
        """Nome da fonte CJK deste idioma, ou "" se ele não precisa de uma
        (idiomas latinos usam a fonte padrão do estilo ASS)."""
        if lang not in self.IDIOMAS_CJK:
            return ""
        return self.FONTE_CJK_POR_IDIOMA.get(lang, self.FONTE_CJK)
    BOX_BORDER:          int = BOX_BORDER
    ESPACAMENTO_PALAVRA: int = ESPACAMENTO_PALAVRA
    LARGURA_CHAR:        int = LARGURA_CHAR

    # ── Estilo da legenda única (Single Subtitle — texto simples, 1 faixa) ────
    # Independente de TAMANHO_FONTE_TAG (usado só no modo multi-idioma/palavra
    # colorida) — a legenda única é a única coisa na tela, então pode (e deve)
    # ser maior e mais legível.
    TAMANHO_FONTE_LEGENDA: int = 32
    CONTORNO_LEGENDA:      int = 3
    MARGEM_V_LEGENDA:      int = 30  # sem efeito com alinhamento central (ASS ignora
                                       # MarginV quando Alignment=5/meio — texto fica
                                       # sempre centralizado verticalmente na tela)

    # ── Modo de geração de vídeo ──────────────────────────────────────────────
    VIDEO_SIMPLES_SEM_MORFOLOGIA: bool = False

    # ── Retry / performance ───────────────────────────────────────────────────
    GROQ_MAX_TENTATIVAS:    int   = 3
    GROQ_DELAY_ENTRE_CALLS: float = 2.0
    DOWNLOAD_TIMEOUT:       int   = 30
    FFMPEG_NUM_THREADS:     int   = 3

    # ─────────────────────────────────────────────────────────────────────────
    # NOMES DE ARQUIVO — todos prefixados com NOME_ORACAO
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def NOME_AUDIO(self) -> str:
        return f"{self.NOME_ORACAO}_audio.wav"

    @property
    def _sufixo_modo(self) -> str:
        """Sufixo aplicado aos nomes de vídeo quando MODO_CLIPE='imagem'
        (string vazia em modo 'video', sem mudar nenhum nome existente)."""
        return self.SUFIXO_MODO_IMAGEM if self.MODO_CLIPE == "imagem" else ""

    @property
    def NOME_VIDEO_BASE(self) -> str:
        return f"{self.NOME_ORACAO}_video_base{self._sufixo_modo}.mp4"

    # ── Níveis de vídeo final ──────────────────────────────────────────────────
    # Cada nível soma um recurso em cima do anterior -- todos coexistem na
    # mesma pasta, sem um sobrescrever o outro (nomes diferentes de propósito).
    #   0. NOME_VIDEO_BASE            -- narração + clipes + trilha, sem legenda
    #   1. NOME_VIDEO_FINAL            -- + legenda única (1 idioma, texto simples)
    #   2. NOME_VIDEO_FINAL_IDIOMAS    -- + legendas multi-idioma empilhadas
    #                                     (1 cor por idioma, sem classificação)
    #   3. NOME_VIDEO_FINAL_MULTICOLOR -- mesmo nível 2, mas com classificação
    #                                     gramatical (Stanza/Kiwi, cor por classe)
    # NOME_VIDEO_FINAL_CLASSIFICACAO(_BASICO) é um ramo obsoleto, não um nível
    # -- ver docstring dele abaixo.

    # ── Sufixo de variante do CONJUNTO DE IDIOMAS ─────────────────────────────
    # Só afeta os dois níveis que dependem de quais idiomas entram (2 e 3).
    # Serve pra uma variante conviver com a original na mesma pasta em vez de
    # sobrescrevê-la -- ex: a versão de 6 idiomas (com chinês,
    # caption-multilang-zh-*.ipynb) usa "_zh" e gera
    # <nome>_final_idiomas_zh.mp4, deixando o <nome>_final_idiomas.mp4 de 5
    # idiomas intacto. Vazio (padrão) = nomes de sempre, nada muda.
    SUFIXO_VARIANTE_IDIOMAS: str = ""

    # ── Sufixo de variante de LAYOUT ──────────────────────────────────────────
    # Outro eixo, independente do de idiomas: a MESMA seleção de idiomas pode
    # sair com a cena ocupando a tela (padrão) ou encolhida numa miniatura
    # abaixo da legenda, sobre uma imagem mestre limpa (ver moldura.py). Os
    # dois vídeos convivem na pasta -- "_mini" no nome de quem é miniatura.
    # Vazio (padrão) = nomes de sempre.
    SUFIXO_VARIANTE_LAYOUT: str = ""

    @property
    def NOME_VIDEO_FINAL(self) -> str:
        """Vídeo final com legenda única (1 faixa simples) — Single Subtitle."""
        return f"{self.NOME_ORACAO}_final{self._sufixo_modo}.mp4"

    @property
    def NOME_VIDEO_FINAL_IDIOMAS(self) -> str:
        """Vídeo final com legendas multi-idioma empilhadas — Language Subtitles.
        Nome diferente de NOME_VIDEO_FINAL de propósito: os dois vídeos podem
        coexistir na mesma pasta sem um sobrescrever o outro."""
        return (f"{self.NOME_ORACAO}_final_idiomas{self._sufixo_modo}"
                f"{self.SUFIXO_VARIANTE_IDIOMAS}{self.SUFIXO_VARIANTE_LAYOUT}.mp4")

    @property
    def NOME_VIDEO_FINAL_CLASSIFICACAO(self) -> str:
        """⚠️ OBSOLETO -- era da classificação morfológica antiga via API de IA
        (descontinuada). O pipeline atual (Tanza/Kiwi) usa
        NOME_VIDEO_FINAL_MULTICOLOR. Mantido só por compatibilidade com
        vídeos antigos já gerados com esse nome -- não usar em código novo."""
        return f"{self.NOME_ORACAO}_final_classificacao.mp4"

    @property
    def NOME_VIDEO_FINAL_CLASSIFICACAO_BASICO(self) -> str:
        """⚠️ OBSOLETO -- ver NOME_VIDEO_FINAL_CLASSIFICACAO."""
        return f"{self.NOME_ORACAO}_final_classificacao_basico.mp4"

    @property
    def NOME_VIDEO_FINAL_MULTICOLOR(self) -> str:
        """Vídeo final com legenda multicor (classificação morfológica via
        Stanza/Kiwi, 5 idiomas) -- gerado por caption-multicolor-burn.ipynb.
        Nível 3 dos vídeos finais (ver bloco "Níveis de vídeo final" acima
        de NOME_VIDEO_FINAL) -- nome alinhado ao padrão _final/_final_idiomas
        dos outros níveis (antes era _com_legenda_colorida; vídeos já
        gerados antes dessa mudança, ex: 40_Matt_02, têm o arquivo real no
        Drive com o nome antigo -- renomeie manualmente)."""
        return (f"{self.NOME_ORACAO}_final_multicolor{self._sufixo_modo}"
                f"{self.SUFIXO_VARIANTE_IDIOMAS}{self.SUFIXO_VARIANTE_LAYOUT}.mp4")

    @property
    def NOME_SRT_PT_WHISPER(self) -> str:
        """Transcrição do Whisper sobre a narração — mestre de SEGMENTAÇÃO
        (tempos/blocos que os idiomas-alvo seguem). Usa IDIOMA_MESTRE (não é
        mais fixo em 'pt'). Nome usa "whisper" (não "edge") porque é sempre
        o Whisper que gera esse SRT, venha a narração do Edge TTS, de upload
        manual ou de dublagem baixada como mestre -- ver nome_legenda_mestre
        e nome_palavras_mestre/nome_audio_mestre abaixo pros outros 2 papéis
        de "mestre" do vídeo (palavras e áudio, que não são o Whisper)."""
        return f"{self.NOME_ORACAO}_whisper_{self.IDIOMA_MESTRE}.srt"

    # ── Legenda escolhida para o vídeo de legenda única (Single Subtitle) ────
    # Conceito diferente de "legenda mestre de segmentação/palavras" (que só
    # vai existir quando Language Subtitles for construído). Aqui é só:
    # "qual arquivo SRT, já salvo na pasta deste vídeo, o pipeline pega para
    # queimar como legenda única no vídeo final".
    #
    # Deixe em branco para usar o padrão (transcrição do Whisper sobre a
    # narração: NOME_whisper_IDIOMA.srt — é o que o notebook de geração salva).
    # Preencha manualmente para escolher outro arquivo já salvo na pasta do
    # vídeo — por exemplo, uma cópia renomeada depois de corrigida à mão,
    # ou uma legenda de outra origem (YouTube, roteiro, etc.).
    NOME_LEGENDA_UNICA: str = ""

    @property
    def nome_legenda_unica(self) -> str:
        """Arquivo SRT escolhido para o vídeo de legenda única.

        Se NOME_LEGENDA_UNICA estiver vazio (padrão), usa NOME_SRT_PT_WHISPER
        (a transcrição do Whisper sobre a narração). Se preenchido, usa
        exatamente o que foi digitado na célula de configuração — permite
        apontar para qualquer SRT já salvo em pasta_oracao, inclusive uma
        versão corrigida manualmente com outro nome.
        """
        return self.NOME_LEGENDA_UNICA.strip() or self.NOME_SRT_PT_WHISPER

    # ── Os 3 "mestres" do vídeo (áudio, palavras, segmentação) ────────────────
    # O vídeo tem 3 papéis de "mestre", cada um podendo ser 1 arquivo só ou o
    # resultado de uma mescla feita por VOCÊ fora do pipeline (o pipeline não
    # tenta mesclar transcrições sozinho -- é frágil demais pra automatizar
    # bem). Em todos os 3, o campo de override abaixo é opcional: vazio =
    # usa o arquivo padrão daquele papel; preenchido = aponta pra qualquer
    # arquivo já salvo em pasta_oracao (ex: sua versão corrigida/mesclada).
    # Nenhum dos 3 usa sufixo "_mestre" no NOME do arquivo -- o papel de
    # "mestre" é indicado pelo CAMPO de config que aponta pra ele, não por
    # uma marca no nome do arquivo (mesmo padrão de nome_legenda_unica).
    #
    #  1. ÁUDIO mestre (nome_audio_mestre) — normalmente 1 arquivo só, sem
    #     mescla: a narração (NOME_AUDIO), venha do Edge TTS, de upload
    #     manual, ou de uma dublagem baixada usada como mestre.
    #  2. PALAVRAS mestre (nome_palavras_mestre) — o roteiro (com ou sem
    #     versículo). Pode ser mesclado por você com a transcrição Whisper
    #     da dublagem do YouTube desse idioma, pra pegar palavra que a
    #     dublagem falou ligeiramente diferente do roteiro escrito -- se
    #     mesclar, salve o resultado por cima do mesmo arquivo no Drive.
    #  3. SEGMENTAÇÃO mestre (nome_legenda_mestre) — quem decide os
    #     blocos/tempos que os idiomas-alvo devem seguir. Essa é a mescla
    #     que o próprio pipeline já faz bem (ver alinhar_versiculos() em
    #     srt_utils.py): Whisper (nome_srt_whisper) + roteiro-versículo,
    #     com fusão automática de versículo curto demais pro vizinho
    #     (elimina gap/flicker -- ver calcular_segmentos_versiculo() em
    #     match_pipeline.py).

    NOME_AUDIO_MESTRE: str = ""

    @property
    def nome_audio_mestre(self) -> str:
        """Arquivo de áudio da narração do idioma mestre.

        Se NOME_AUDIO_MESTRE estiver vazio (padrão), usa NOME_AUDIO.
        Preencha só se quiser apontar pra um áudio com outro nome já salvo
        em pasta_oracao (ex: uma tomada alternativa)."""
        return self.NOME_AUDIO_MESTRE.strip() or self.NOME_AUDIO

    @property
    def nome_roteiro(self) -> str:
        """Roteiro do idioma mestre SEM números de versículo soltos no meio
        do texto -- modo padrão (video-base-*-padrao.ipynb). Pra modo
        versículo, ver nome_roteiro_versiculos."""
        return f"{self.NOME_ORACAO}_roteiro.txt"

    NOME_PALAVRAS_MESTRE: str = ""

    @property
    def nome_palavras_mestre(self) -> str:
        """Arquivo de texto com as palavras corretas do idioma mestre --
        o roteiro (nome_roteiro_versiculos ou nome_roteiro, conforme
        MODO_ROTEIRO). Pode já vir corrigido/mesclado manualmente por você
        com a transcrição Whisper da dublagem do YouTube (ver comentário
        "Os 3 mestres do vídeo" acima) -- nesse caso salve por cima do
        mesmo nome no Drive, não precisa preencher NOME_PALAVRAS_MESTRE.

        Se NOME_PALAVRAS_MESTRE estiver vazio (padrão), usa
        nome_roteiro_versiculos (MODO_ROTEIRO="versiculo", o caso mais
        comum) ou nome_roteiro (MODO_ROTEIRO="padrao"). Preencha só pra
        apontar pra um arquivo com outro nome."""
        if self.NOME_PALAVRAS_MESTRE.strip():
            return self.NOME_PALAVRAS_MESTRE.strip()
        return self.nome_roteiro_versiculos if self.MODO_ROTEIRO == "versiculo" else self.nome_roteiro

    # ── Legenda mestre (Language Subtitles — molde de segmentação/palavras) ──
    # Conceito diferente de nome_legenda_unica. Esta é a legenda que define
    # a SEGMENTAÇÃO e os TEMPOS que os outros idiomas devem seguir — os
    # idiomas-alvo têm seu texto redistribuído nos MESMOS blocos/tempos
    # desta legenda (não usam os tempos do próprio Whisper/YouTube deles).
    # É o papel de "mestre de segmentação" descrito acima (item 3).
    #
    # Por padrão, reaproveita nome_legenda_unica (o SRT já corrigido do
    # Single Subtitle) — na prática, o mesmo arquivo serve aos dois
    # propósitos, a menos que você queira um molde diferente.
    NOME_LEGENDA_MESTRE: str = ""

    @property
    def nome_legenda_mestre(self) -> str:
        """Arquivo SRT que define segmentação/tempos para os outros idiomas
        (mestre de SEGMENTAÇÃO -- ver bloco "Os 3 mestres do vídeo" acima).

        UM ARQUIVO, UM PAPEL. `<nome>_mestre.srt` não é gerado por nenhuma
        etapa: ele nasce de um ato explícito ("promover a mestre", no fim do
        caption-single-revisar.ipynb), porque é o momento em que um arquivo
        corrigido à mão vira contrato pra todos os idiomas.

        Antes disto a mestre era um arquivo emprestado -- na prática o
        `_whisper_<mestre>.srt`, cujo nome quer dizer o OPOSTO ("saída crua do
        Whisper"), e que a célula de transcrição reescreve. Daí ter sido
        preciso inventar o PROTEGER_LEGENDA_MESTRE, que recusa gravar quando o
        destino tem o nome da mestre. Sem idioma no nome de propósito: existe
        exatamente UMA mestre por vídeo, seja qual for o idioma dela, e um
        `_mestre_pt.srt` convidaria a acreditar no contrário.

        NOME_LEGENDA_MESTRE preenchido continua vencendo -- serve pra apontar
        um molde diferente sem renomear nada.
        """
        return self.NOME_LEGENDA_MESTRE.strip() or f"{self.NOME_ORACAO}_mestre.srt"

    @property
    def nomes_legenda_mestre_legado(self) -> tuple[str, ...]:
        """Onde a mestre morava antes de ter nome próprio, na ordem em que
        procurar. Serve pros vídeos que já existem: sem `_mestre.srt`, o
        pipeline cai num destes AVISANDO qual escolheu -- o modo de falhar
        que não se aceita aqui é um arquivo virar mestre em silêncio.

        Sem repetição: com NOME_LEGENDA_UNICA vazio (o padrão),
        nome_legenda_unica JÁ é o NOME_SRT_PT_WHISPER, e listar o mesmo nome
        duas vezes faria a mensagem de aviso repetir o arquivo."""
        vistos: list[str] = []
        for nome in (self.nome_legenda_unica, self.NOME_SRT_PT_WHISPER):
            if nome not in vistos:
                vistos.append(nome)
        return tuple(vistos)

    # ── Proteção da legenda mestre contra sobrescrita acidental ───────────────
    # Se True (padrão), qualquer função que geraria/sobrescreveria um SRT cujo
    # nome bate com nome_legenda_mestre recusa a operação em vez de sobrescrever
    # silenciosamente.
    #
    # Desde que a mestre ganhou nome próprio (`<nome>_mestre.srt`, que nenhuma
    # etapa gera), esta trava não dispara no caminho normal -- ela existia
    # porque a mestre era um arquivo emprestado, que a célula de transcrição
    # reescrevia. Fica como rede pra quem preenche NOME_LEGENDA_MESTRE
    # apontando pra um arquivo que o pipeline gera.
    # Coloque False só quando quiser mesmo re-gerar a mestre do zero.
    PROTEGER_LEGENDA_MESTRE: bool = True

    # ── Indicador de livro:versículo (overlay pequeno no canto) ───────────────
    # Referência fixa no canto superior esquerdo (ex: "Matt/Mt/마 2:4"), que
    # muda só o número do versículo conforme a narração avança — separado das
    # legendas de idioma empilhadas no meio da tela.
    CAPITULO: int = 1
    # Abreviações por idioma, na ordem em que devem aparecer combinadas
    # (duplicatas — ex: pt/es/fr usando a mesma abreviação — são removidas
    # automaticamente, mantendo a primeira ocorrência).
    # Só um OVERRIDE: a fonte normal é a tabela versionada
    # dados_lexico/siglas-livros.json, alimentada pelo \toc3 do USFM de cada
    # tradução (ver biblia_livros.abreviacoes). Preencha aqui pra corrigir um
    # livro sem esperar o USFM inteiro.
    ABREVIACOES_LIVRO: dict[str, str] = field(default_factory=dict)

    # Quais idiomas aparecem no indicador de livro:versículo do canto. NÃO são
    # todos os da tela de propósito: pt/es/fr abreviam Mateus igual ("Mt"), e
    # "Matt/Mt/Mt/Mt/마/太 2:4" é comprido sem informar mais que
    # "Matt/마/太 2:4" -- um por sistema de escrita.
    IDIOMAS_INDICADOR_VERSICULO: tuple[str, ...] = ("en", "ko", "zh")
    TAMANHO_FONTE_VERSICULO: int = 26
    CONTORNO_VERSICULO:      int = 2

    # ── Fontes de texto bruto por idioma (Language Subtitles) ────────────────
    # Por idioma-alvo, qual arquivo bruto usar como fonte de texto para a
    # redistribuição: "yt" (legenda do YouTube, nome_srt_yt) ou "whisper"
    # (transcrição do Whisper sobre o áudio dublado, nome_srt_whisper).
    # Idiomas não listados aqui usam o padrão "yt".
    FONTE_TEXTO_IDIOMA: dict[str, str] = field(default_factory=dict)

    def fonte_texto(self, lang: str) -> str:
        """Retorna 'yt' ou 'whisper' — qual fonte bruta usar para este idioma."""
        return self.FONTE_TEXTO_IDIOMA.get(lang, "yt")

    # ── Código de idioma específico do YouTube (legendas) ─────────────────────
    # O YouTube às vezes usa um código diferente do código "canônico" que o
    # resto do projeto usa (posição na tela, cor, fonte CJK, Whisper) — o caso
    # mais comum é chinês ("zh" internamente vs "zh-Hans"/"zh-Hant" no
    # YouTube). Coreano não precisa disso (YouTube já usa "ko" puro), mas o
    # mecanismo fica disponível caso outro idioma precise no futuro — é só
    # preencher o dict, ex: CODIGO_LEGENDA_YOUTUBE={"zh": "zh-Hans"}.
    CODIGO_LEGENDA_YOUTUBE: dict[str, str] = field(default_factory=dict)

    def codigo_legenda_youtube(self, lang: str) -> str:
        """Código a usar no --sub-langs do yt-dlp para este idioma (pode
        diferir do código canônico usado no resto do projeto — ver acima)."""
        return self.CODIGO_LEGENDA_YOUTUBE.get(lang, lang)

    # ── Override manual de formato de áudio por idioma ─────────────────────────
    # As faixas de dublagem automática do YouTube às vezes ficam temporariamente
    # indisponíveis para o filtro automático (ba[language^=...]) mesmo existindo
    # — se acontecer, rode "yt-dlp -F URL", pegue o ID exato da faixa (ex:
    # "251-11") e coloque aqui para aquele idioma específico.
    FORMATO_MANUAL_AUDIO: dict[str, str] = field(default_factory=dict)

    def formato_manual_audio(self, lang: str) -> Optional[str]:
        """Retorna o ID de formato manual para este idioma, ou None (usa o
        filtro automático por idioma)."""
        return self.FORMATO_MANUAL_AUDIO.get(lang) or None

    def nome_srt_whisper(self, lang: str) -> str:
        """Transcrição do Whisper sobre o áudio dublado deste idioma (bruta)."""
        return f"{self.NOME_ORACAO}_whisper_{lang}.srt"

    def nome_audio_idioma(self, lang: str) -> str:
        """Áudio dublado automático baixado do YouTube para este idioma."""
        return f"{self.NOME_ORACAO}_audio_{lang}.wav"

    @property
    def NOME_SRT_PT(self) -> str:
        """Legenda do idioma mestre, já distribuída/corrigida.
        Usa IDIOMA_MESTRE (não é mais fixo em 'pt')."""
        return f"{self.NOME_ORACAO}_{self.IDIOMA_MESTRE}.srt"

    def nome_srt(self, lang: str) -> str:
        return f"{self.NOME_ORACAO}_{lang}.srt"

    @property
    def nome_roteiro_versiculos(self) -> str:
        """Roteiro do capítulo com números de versículo soltos no meio do
        texto (ex: "1 Now when Jesus... 2 Where is he..."), já limpo de
        navegação/notas de rodapé (ver limpar_roteiro_biblia.html). Fica em
        videos/<nome>/ -- match-scene-verse.ipynb e os notebooks
        video-base-*-versiculo.ipynb baixam esse arquivo sozinhos, sem
        precisar colar o texto na célula de Configuração toda vez."""
        return f"{self.NOME_ORACAO}_roteiro_versiculos.txt"

    @property
    def nome_srt_versiculo(self) -> str:
        """SRT do indicador de livro:versículo NUM SÓ IDIOMA (o mestre --
        ex: "Matt 2:4") -- usado pelo vídeo de legenda única
        (caption_pipeline.py/queimar_legenda_unica), que só tem 1 idioma na
        tela. Pra várias legendas empilhadas ao mesmo tempo, ver
        nome_srt_versiculo_multilingue abaixo."""
        return f"{self.NOME_ORACAO}_versiculo.srt"

    @property
    def nome_srt_versiculo_multilingue(self) -> str:
        """SRT do indicador de livro:versículo combinando as abreviações de
        TODOS os idiomas configurados (ABREVIACOES_LIVRO) num só bloco --
        ex: "Matt/Mt/마 2:4". Usado pelo vídeo de legendas multi-idioma
        (language_captions_pipeline.py/queimar_idiomas), onde já tem
        vários idiomas empilhados na tela ao mesmo tempo."""
        return f"{self.NOME_ORACAO}_versiculo_multilingue.srt"

    def nome_classificacao_multicolor(self, lang: str) -> str:
        """JSON com o resultado da classificação gramatical (Stanza pra
        pt/en/es/fr, Kiwi pro ko) usada na legenda multicolor
        (caption-multicolor-generate.ipynb) -- palavra/peça + classe, por
        bloco de tempo. Disponível pra correção manual: se esse arquivo já
        existir no Drive quando o notebook rodar, ele é usado no lugar de
        rodar o Stanza/Kiwi de novo pra esse idioma."""
        return f"{self.NOME_ORACAO}_classificacao_multicolor_{lang}.json"

    @property
    def nome_imagem_mestre(self) -> str:
        """Imagem de fundo da versão em MINIATURA, específica DESTE vídeo.

        Fica na pasta do vídeo. Quando não existe, a queima cai na imagem
        mestre compartilhada do canal (NOME_IMAGEM_MESTRE_PADRAO, em
        assets/marca) e, se nem essa existir, num fundo de cor lisa gerado na
        hora -- pra dar pra rodar a variante antes de a imagem definitiva
        estar escolhida."""
        return f"{self.NOME_ORACAO}_imagem_mestre.png"

    @property
    def nome_camadas(self) -> str:
        """Declaração das camadas opcionais deste vídeo (siglas, indicador de
        versículo, título) — ver camadas.py.

        Mora junto do vídeo e não na configuração de cada notebook porque a
        decisão é do VÍDEO, não de quem está rodando: declarar num notebook e
        esquecer no outro dava vídeo sem a camada, ou notebook gerando arquivo
        que ninguém ia usar."""
        return f"{self.NOME_ORACAO}_camadas.json"

    @property
    def nome_srt_titulo(self) -> str:
        """SRT do TÍTULO do trecho — a legenda fixa dinâmica do canto superior
        direito, em inglês ("The Massacre of the Innocents"), que muda a cada
        faixa de versículos.

        Sai do match-scene-verse.ipynb, que é quem tem a planilha (onde os
        títulos traduzidos moram e são gravados) e a legenda mestre (de onde
        vêm os tempos). Os notebooks de queima só consomem."""
        return f"{self.NOME_ORACAO}_titulo.srt"

    def nome_analise_bruta(self, lang: str) -> str:
        """A análise CRUA do Stanza/Kiwi desse idioma — token com as palavras
        sintáticas dentro, com lema, upos e traços (ver analise.py).

        É a origem: com ela, mudar uma regra de cor vira remapear em segundos,
        em vez de rodar o analisador inteiro de novo. É cache de uma versão
        específica do analisador, e o arquivo carimba qual."""
        return f"{self.NOME_ORACAO}_analise_bruta_{lang}.json"

    @property
    def nome_revisao_classes(self) -> str:
        """CSV com TODAS as peças de TODOS os idiomas da legenda multicor --
        uma linha por peça, pra abrir no Sheets, corrigir a coluna `classe` e
        subir de volta antes de gerar o .ass (ver revisao_classes.py)."""
        return f"{self.NOME_ORACAO}_classes_revisar.csv"

    @property
    def nome_pagina_revisao_classes(self) -> str:
        """Página HTML com a legenda multicor pintada com as cores de verdade,
        pra achar o erro de classe sem precisar assistir o vídeo."""
        return f"{self.NOME_ORACAO}_classes_revisar.html"

    def nome_match_json(self, capitulo: int) -> str:
        """JSON com o resultado do match versículo↔vídeo/imagem (match-scene-verse.ipynb)."""
        return f"match_{self.NOME_ORACAO}_cap{capitulo}.json"

    def nome_lacunas_match(self, capitulo: int) -> str:
        """Relatório dos versículos SEM match (nenhuma mídia bateu tag) --
        lista as palavras-chave sugeridas pra você buscar manualmente no
        pixabay_downloader antes de rodar a montagem automática."""
        return f"lacunas_match_{self.NOME_ORACAO}_cap{capitulo}.txt"

    def nome_srt_yt(self, lang: str) -> str:
        """Legenda original do YouTube (mestre de texto/proporção)."""
        return f"{self.NOME_ORACAO}_yt_{lang}.srt"

    def nome_classificacao(self, lang: str) -> str:
        """JSON de classificação morfológica completa."""
        return f"{self.NOME_ORACAO}_classificacao_{lang}.json"

    def nome_classificacao_basico(self, lang: str) -> str:
        """JSON de classificação morfológica básica."""
        return f"{self.NOME_ORACAO}_classificacao_basico_{lang}.json"

    # ─────────────────────────────────────────────────────────────────────────
    # PASTAS DO DRIVE
    # Estrutura: narrated_video/
    #   ├── assets/clipes|logo|musica    ← compartilhados entre vídeos
    #   └── videos/{nome}/               ← tudo do vídeo específico
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def pasta_base_drive(self) -> Path:
        """Pasta raiz do projeto no Drive."""
        return Path(f"/content/drive/MyDrive/{self.PASTA_DRIVE_RAIZ}")

    # ── Assets compartilhados (não mudam entre orações) ───────────────────────
    @property
    def pasta_assets(self) -> Path:
        return self.pasta_base_drive / "assets"

    @property
    def pasta_assets_clipes(self) -> Path:
        """Clipes Pixabay reutilizáveis entre todas as orações."""
        return self.pasta_assets / "clipes"

    @property
    def pasta_assets_logo(self) -> Path:
        # Pasta real no Drive é "marca" (não "logo")
        return self.pasta_assets / "marca"

    @property
    def pasta_assets_musica(self) -> Path:
        # Pasta real no Drive é "trilha" (não "musica")
        return self.pasta_assets / "trilha"

    @property
    def pasta_dados_lexico(self) -> Path:
        """Dados de referência do projeto: eventos/títulos bíblicos e o texto
        completo da Bíblia (web-biblia.json). Imutáveis, versionados no git,
        compartilhados por todos os vídeos."""
        return self.pasta_base_drive / "pipeline" / "dados_lexico"

    @property
    def caminho_web_biblia(self) -> Path:
        """O texto completo da WEB, baixado uma vez pelo biblia-texto-baixar."""
        return self.pasta_dados_lexico / "web-biblia.json"

    # ── Pasta do vídeo específico (tudo identificado pelo prefixo) ────────────
    @property
    def pasta_oracao(self) -> Path:
        """Pasta raiz do vídeo: videos/{nome}/"""
        return self.pasta_base_drive / "videos" / self.NOME_ORACAO

    @property
    def pasta_correcoes(self) -> Path:
        """JSONs revisados pelo usuário (pacote revisão)."""
        return self.pasta_oracao / f"{self.NOME_ORACAO}_correcoes"

    # ── Aliases para compatibilidade com módulos existentes ───────────────────
    @property
    def pasta_drive_correcoes(self) -> Path:
        return self.pasta_correcoes

    @property
    def pasta_drive_brutos(self) -> Path:
        """JSONs brutos gerados pelo Groq (backup automático)."""
        return self.pasta_oracao / f"{self.NOME_ORACAO}_brutos"

    @property
    def pasta_revisao(self) -> Path:
        """Prompts genéricos de revisão — compartilhados entre todas as orações."""
        return self.pasta_base_drive / "pipeline" / "revisao"

    # ── Nomes de arquivo do pacote de revisão ─────────────────────────────────

    @property
    def nome_relatorio(self) -> str:
        """Relatório CSV específico da oração."""
        return f"{self.NOME_ORACAO}_relatorio.csv"

    @property
    def nome_prompt_revisao(self) -> str:
        """Prompt de revisão completa — genérico."""
        return "prompt_revisao.md"

    @property
    def nome_prompt_revisao_basico(self) -> str:
        """Prompt de revisão básica — genérico."""
        return "prompt_revisao_basico.md"

    @property
    def pasta_assets_videos(self) -> Path:
        """Alias legado → pasta da oração."""
        return self.pasta_oracao

    @property
    def pasta_assets_audio(self) -> Path:
        """Alias legado → pasta da oração."""
        return self.pasta_oracao

    @property
    def pasta_assets_legendas(self) -> Path:
        """Alias legado → pasta da oração."""
        return self.pasta_oracao

    @property
    def pasta_assets_cache(self) -> Path:
        return self.pasta_oracao / f"{self.NOME_ORACAO}_cache"

    @property
    def pasta_assets_marca(self) -> Path:
        """Alias legado → pasta logo compartilhada."""
        return self.pasta_assets_logo

    @property
    def pasta_assets_trilha(self) -> Path:
        """Alias legado → pasta musica compartilhada."""
        return self.pasta_assets_musica

    # ─────────────────────────────────────────────────────────────────────────
    # VALIDAÇÃO E RESUMO
    # ─────────────────────────────────────────────────────────────────────────

    def validate(self) -> None:
        erros: list[str] = []
        if not self.NOME_ORACAO:
            erros.append("NOME_ORACAO não pode ser vazio")
        if not self.TEXTO_ORACAO:
            erros.append("TEXTO_ORACAO não pode ser vazio")
        if not self.ID_PLANILHA_DRIVE:
            erros.append("ID_PLANILHA_DRIVE não configurado")
        if erros:
            raise ValueError("PipelineConfig inválido:\n" + "\n".join(f"  - {e}" for e in erros))
        logger.info("PipelineConfig OK: '%s'", self.NOME_ORACAO)

    def resumo(self) -> str:
        return "\n".join([
            f"Vídeo:         {self.NOME_ORACAO}",
            f"Drive raiz:    {self.PASTA_DRIVE_RAIZ}",
            f"Pasta vídeo:   {self.pasta_oracao}",
            f"Áudio:         {self.NOME_AUDIO}",
            f"Vídeo base:    {self.NOME_VIDEO_BASE}",
            f"Legenda escolhida: {self.nome_legenda_unica}",
            f"Voz Edge TTS:  {self.VOZ_EDGE}",
            f"Velocidade:    {self.VELOCIDADE_AUDIO}x",
            f"Volume narração/trilha: {self.VOLUME_NARRACAO} / {self.VOLUME_MUSICA}",
            f"Clipes:        {self.pasta_assets_clipes}",
            f"Padrão clipe:  {self.LARGURA_CLIPE}x{self.ALTURA_CLIPE} @ {self.FPS_CLIPE}fps",
        ])


# ─────────────────────────────────────────────────────────────────────────────
# Detecção do modo de fundo
# ─────────────────────────────────────────────────────────────────────────────

def detectar_modo_clipe(
    pasta_oracao: Path | str,
    nome_oracao: str,
    sufixo_imagem: str = "_img",
) -> str:
    """Descobre pelo Drive se o vídeo base daquele projeto é de imagem ou de clipe.

    Os notebooks de QUEIMA (`*-burn`) não montam vídeo nenhum: eles pegam o
    `<nome>_video_base*.mp4` que já existe e escrevem legenda por cima. Só que
    o nome desse arquivo depende de `MODO_CLIPE`, e nenhum deles pedia esse
    campo -- então caíam no padrão `"video"` e procuravam
    `<nome>_video_base.mp4` enquanto o modo imagem tinha gravado
    `<nome>_video_base_img.mp4`. E o sufixo não some no meio do caminho: o
    resultado também sairia sem `_img`, colidindo com a versão de clipe.

    A saída vem do arquivo que EXISTE, não de uma opção que dá pra esquecer de
    marcar -- mesma ideia do sufixo `_zh` que o `caption-multicolor-burn` lê do
    nome do `.ass`. Com os dois presentes não há palpite razoável: aí sim é
    você quem escolhe, passando `MODO_CLIPE` à mão.

    Returns:
        `"imagem"` ou `"video"`, pronto pra `PipelineConfig(MODO_CLIPE=...)`.

    Raises:
        FileNotFoundError: nenhum vídeo base na pasta — não há o que queimar.
        ValueError: os dois existem; escolha qual quer queimar.
    """
    pasta = Path(pasta_oracao)
    de_imagem = pasta / f"{nome_oracao}_video_base{sufixo_imagem}.mp4"
    de_clipe  = pasta / f"{nome_oracao}_video_base.mp4"

    achou_imagem, achou_clipe = de_imagem.exists(), de_clipe.exists()

    if achou_imagem and achou_clipe:
        raise ValueError(
            f"Os dois vídeos base existem em {pasta}:\n"
            f"  - {de_imagem.name}  (modo imagem)\n"
            f"  - {de_clipe.name}  (modo vídeo)\n"
            "Não dá pra adivinhar qual você quer queimar. Passe à mão na "
            "célula de configuração: MODO_CLIPE = \"imagem\" ou \"video\"."
        )
    if achou_imagem:
        return "imagem"
    if achou_clipe:
        return "video"
    raise FileNotFoundError(
        f"Nenhum vídeo base em {pasta}. Procurei:\n"
        f"  - {de_imagem.name}\n"
        f"  - {de_clipe.name}\n"
        "Rode um notebook `video-base-*` antes de queimar legenda."
    )
