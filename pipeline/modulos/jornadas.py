# -*- coding: utf-8 -*-
"""
jornadas.py — Que sequência de notebook leva a que resultado.

São 30 notebooks. A pergunta que se faz na prática nunca é "o que este
notebook faz?" -- é a inversa: **"eu quero um vídeo assim; o que eu rodo?"**
Este módulo responde essa, e o `JORNADAS.md` sai daqui.

## Por que em código e não só num .md

Mesma razão do `nomenclatura.py`: um .md envelhece calado. Notebook novo entra
na pasta e o mapa continua dizendo que são os de antes; notebook renomeado
deixa o mapa apontando pra um arquivo que não existe. Aqui o `verificar_repo()`
acusa os dois casos, e o `EXCECOES` obriga a escrever o motivo de um notebook
ficar fora de qualquer jornada -- exceção registrada é decisão, exceção
esquecida é bagunça.

## O que é uma jornada

Uma sequência de notebooks que entrega **um resultado que você usa**. Não é a
mesma coisa que uma etapa: `caption-single-generate` sozinho não entrega nada
que se publique, entrega um SRT que a jornada seguinte consome.

Três tipos:

    PREPARO   roda uma vez na vida do projeto (ou quando o estoque cresce)
    VIDEO     roda uma vez por vídeo
    APOIO     roda quando você quiser, não produz vídeo

## A descoberta que o mapa tornou óbvia

Os quatro níveis de vídeo final NÃO são uma cadeia de arquivos. Os três
notebooks de burn (`caption-single-burn`, `caption-multilang-burn`,
`caption-multicolor-burn`) leem todos o MESMO `NOME_VIDEO_BASE` -- nenhum
queima em cima do mp4 do nível anterior. Então:

  - dá pra pular direto pro nível 3 sem nunca gerar o nível 1 em vídeo;
  - o que encadeia de verdade são os SRT, não os mp4: o nível 2 precisa do
    SRT mestre que o `caption-single-generate` produz, e o nível 3 precisa dos
    SRT por idioma que o `caption-multilang-generate` produz.

Por isso `depende_de` aponta pra jornada cujo ARQUIVO é necessário, e não pra
"o nível de baixo".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ── Estrutura ────────────────────────────────────────────────────────────────

PREPARO, VIDEO, APOIO = "preparo", "vídeo", "apoio"


@dataclass(frozen=True)
class Passo:
    """Um notebook dentro de uma jornada."""
    notebook: str
    produz: str
    #: Alternativas ao mesmo passo (ex: fundo de imagem OU de vídeo). Quem
    #: aparece aqui conta como coberto pela jornada, igual ao `notebook`.
    ou: tuple[str, ...] = ()
    nota: str = ""

    @property
    def notebooks(self) -> tuple[str, ...]:
        return (self.notebook, *self.ou)


@dataclass(frozen=True)
class Jornada:
    id: str
    tipo: str
    titulo: str
    quando: str            # quando se percorre esta jornada
    entrega: str           # o que existe no fim que não existia antes
    passos: tuple[Passo, ...]
    depende_de: tuple[str, ...] = ()   # ids de jornadas cujos arquivos são pré-requisito
    custo: str = ""
    armadilha: str = ""    # o erro que essa jornada costuma provocar

    @property
    def notebooks(self) -> tuple[str, ...]:
        return tuple(n for p in self.passos for n in p.notebooks)


# ── As jornadas ──────────────────────────────────────────────────────────────

JORNADAS: tuple[Jornada, ...] = (

    # ── PREPARO ──────────────────────────────────────────────────────────
    Jornada(
        id="biblia",
        tipo=PREPARO,
        titulo="A Bíblia inteira, em áudio e em texto",
        quando="Uma vez, antes da primeira compilação.",
        entrega="1.189 mp3 por capítulo em `assets/biblia_audio/` e o texto "
                "completo em `dados_lexico/web-biblia.json`.",
        custo="~1,2 GB e algumas horas de download. Roda e esquece.",
        passos=(
            Passo("biblia-audio-baixar", "`assets/biblia_audio/40_Matt_02.mp3` × 1.189",
                  nota="Renomeia do padrão irregular da fonte pro do projeto."),
            Passo("biblia-texto-baixar", "`dados_lexico/web-biblia.json`",
                  nota="Confere contra o `40_Matt_02` que já existe antes de dar por bom."),
        ),
        armadilha="Depois disso, o passo 'fornecer o áudio' some do fluxo de "
                  "compilação. Antes disso, toda compilação trava esperando você.",
    ),

    Jornada(
        id="som",
        tipo=PREPARO,
        titulo="Estoque de som — trilha e efeito",
        quando="Uma vez pra criar as planilhas; de novo sempre que você "
               "adicionar arquivos novos às pastas do Drive.",
        entrega="Aba `trilha_stock` da `Biblioteca_Match_Audio` — trilha e "
                "efeito no mesmo estoque, separados pela coluna `categoria`.",
        passos=(
            Passo("organizar-trilha-audio", "3 planilhas de trilha + aba `trilha_stock`",
                  nota="Na PRIMEIRA vez ele CRIA as planilhas e imprime os IDs — "
                       "copie pra configuração, senão cria planilha nova toda vez."),
            Passo("organizar-efeitos-audio", "linhas de efeito na mesma `trilha_stock`",
                  nota="Filtra por tag concreta (porta, trovão, cavalo), não por clima."),
        ),
        custo="Grátis, sem IA. Não duplica se rodar de novo.",
    ),

    Jornada(
        id="lexico",
        tipo=PREPARO,
        titulo="Tags de evento e título na planilha",
        quando="Uma vez, e de novo quando o léxico ganhar sinônimos.",
        entrega="Abas `evento_tags` e `titulo_tags` na Biblioteca de Match, "
                "com o intervalo de cada um visível.",
        custo="Grátis — sem IA, sem Pixabay. Roda a Bíblia inteira de uma vez.",
        passos=(
            Passo("sincronizar-evento-titulo-tags", "abas `evento_tags` e `titulo_tags`"),
        ),
    ),

    Jornada(
        id="estoque-imagem",
        tipo=PREPARO,
        titulo="Estoque de imagem, semeado pelo léxico bíblico",
        quando="Quando a biblioteca não cobre os versículos que você quer usar.",
        entrega="Linhas novas na `pixabay-image-stock` e entradas permanentes "
                "na `biblioteca_match`, reaproveitáveis por qualquer vídeo futuro.",
        passos=(
            Passo("pixabay-image-seed", "linhas novas em `image-stock`",
                  ou=("pixabay-image-seed-biblia-completa",),
                  nota="Por livro/capítulo, ou os 66 livros de uma vez (esse "
                       "tem checkpoint: se o Colab cair, continua de onde parou)."),
            Passo("pixabay-image-descriptions", "tags e descrição de cena preenchidas",
                  nota="É `Tags_Semelhantes_*` que o painel de revisão usa pra "
                       "achar candidato — sem esta etapa o match não acha nada."),
        ),
        armadilha="Entre SEMEAR e ALOCAR você tem que abrir a planilha e apagar "
                  "as imagens que não servem. Alocar sem revisar imortaliza o lixo.",
    ),

    Jornada(
        id="estoque-video",
        tipo=PREPARO,
        titulo="Estoque de vídeo descrito por IA",
        quando="Quando entrar clipe novo na `pixabay_stock`.",
        entrega="`Tags_*` e `Descricao_Cena_*` preenchidas na aba `pixabay_stock`.",
        custo="IA de visão (Groq + Mistral em rodízio), 1 a 3 frames por clipe.",
        passos=(
            Passo("pixabay-video-descriptions", "8 campos preenchidos por clipe"),
        ),
    ),

    # ── VÍDEO: nível 0, o vídeo base ─────────────────────────────────────
    Jornada(
        id="base-padrao",
        tipo=VIDEO,
        titulo="Nível 0 · vídeo base, modo padrão",
        quando="Quando a imagem não precisa ter a ver com o versículo — "
               "clipes/fotos sorteados, N segundos cada.",
        entrega="`<nome>_video_base[_img].mp4` — narração + fundo + trilha, sem legenda.",
        passos=(
            Passo("video-base-imagem-padrao", "`<nome>_video_base_img.mp4`",
                  ou=("video-base-video-padrao",),
                  nota="Imagem parada ou clipe de vídeo — mesma jornada, fundo diferente."),
        ),
        custo="Cada etapa pula sozinha o que já está feito (checkpoint).",
    ),

    Jornada(
        id="base-versiculo",
        tipo=VIDEO,
        titulo="Nível 0 · vídeo base, imagem casada com o versículo",
        quando="Quando cada versículo deve aparecer com a imagem que fala dele.",
        entrega="`<nome>_video_base[_img].mp4` — a imagem troca quando o versículo troca.",
        depende_de=("estoque-imagem", "legenda-unica"),
        passos=(
            Passo("match-scene-verse", "`match_<nome>_cap<N>.json` + `lacunas_match_*.txt`",
                  nota="Não escreve nada sozinho — é uma lista pra você revisar. "
                       "Versículo sem candidato sai marcado 'sem opção'."),
            Passo("video-base-imagem-versiculo", "`<nome>_video_base_img.mp4`",
                  ou=("video-base-video-versiculo",)),
        ),
        armadilha="Este notebook PARA no meio: rode só a NARRAÇÃO (etapa 6), saia "
                  "pra rodar o `caption-single-generate` e o `match-scene-verse`, "
                  "e só então volte pra etapa de cortar os clipes. Ele exige "
                  "100% de cobertura do match — para com um relatório dos "
                  "versículos faltando, não gera vídeo pela metade.",
    ),

    Jornada(
        id="base-trilhas",
        tipo=VIDEO,
        titulo="Nível 0 · vídeo base + trilha por clima, e efeito pontual",
        quando="Quando a trilha deve mudar junto com o evento da narrativa, e "
               "(na variante com efeitos) quando um versículo pede um som "
               "pontual — porta, trovão, cavalo.",
        entrega="`<nome>_video_base[_img].mp4` — mesmo nome canônico dos outros, "
                "com trilha por trecho de evento (+ efeitos, na variante).",
        depende_de=("estoque-imagem", "som", "legenda-unica"),
        passos=(
            Passo("video-base-imagem-versiculo-trilhas", "`<nome>_video_base_img.mp4` + trilha",
                  ou=("video-base-imagem-versiculo-trilhas-efeitos",),
                  nota="Autocontidos: fazem o match cena↔versículo por dentro, "
                       "não precisa rodar o `match-scene-verse` antes."),
        ),
        armadilha="Mesma interrupção do `base-versiculo`: narração primeiro, "
                  "`caption-single-generate` fora, volta pro resto. E o pool de "
                  "candidatas (`TRILHAS_CANDIDATAS`, `EFEITOS_CANDIDATOS`) você "
                  "escolhe à mão na Configuração — pool vazio dá vídeo sem "
                  "trilha, sem erro nenhum.",
    ),

    # ── VÍDEO: os níveis de legenda ──────────────────────────────────────
    Jornada(
        id="legenda-unica",
        tipo=VIDEO,
        titulo="Nível 1 · legenda única",
        quando="O vídeo mais simples que dá pra publicar — e o SRT que ele "
               "gera é pré-requisito de quase todo o resto.",
        entrega="`<nome>_final[_img].mp4` + a LEGENDA MESTRE `<nome>_mestre.srt`, "
                "que é o contrato de segmentação dos níveis 2 e 3.",
        # Sem `depende_de` de propósito: o `generate` precisa só da NARRAÇÃO
        # (`<nome>_audio.wav`), que é a etapa 6 de qualquer notebook de vídeo
        # base -- não do vídeo base pronto. Pôr "base-padrao" aqui faria o mapa
        # dizer que pro modo versículo você tem que rodar o modo padrão antes,
        # que é falso.
        passos=(
            Passo("caption-single-generate", "`<nome>_whisper_<mestre>.srt`",
                  nota="Já lista onde o Whisper discorda do roteiro do capítulo. "
                       "Vale baixar, corrigir e resubir com o mesmo nome — "
                       "Whisper sempre pede uma passada."),
            Passo("caption-single-revisar",
                  "as trocas a fazer no SRT + `<nome>_mestre.srt`",
                  nota="Ouvir cada divergência é opcional (só o áudio separa 'o "
                       "Whisper errou' de 'o Dave leu diferente'; sem ouvir, vale a "
                       "regra 'faz sentido em inglês? sim fica o Whisper, não vai pro "
                       "roteiro'). A ÚLTIMA célula não é: é ela que promove o SRT "
                       "corrigido a `<nome>_mestre.srt`, e é esse arquivo que os "
                       "níveis 2 e 3 seguem."),
            Passo("caption-single-burn", "`<nome>_final[_img].mp4`"),
        ),
        armadilha="Os três passos precisam de coisas diferentes: o `generate` "
                  "precisa só da narração (etapa 6 de qualquer notebook de vídeo "
                  "base), o `burn` precisa do vídeo base pronto. Pros níveis 2 e 3 "
                  "o pré-requisito é a PROMOÇÃO a mestre (última célula do "
                  "`revisar`) — o `burn` não é pré-requisito de nada. Sem promover, "
                  "eles caem no `<nome>_whisper_<mestre>.srt` avisando, que é onde a "
                  "mestre morava antes de ter nome próprio.",
    ),

    Jornada(
        id="multi-idioma",
        tipo=VIDEO,
        titulo="Nível 2 · legendas multi-idioma, uma cor por idioma",
        quando="O vídeo poliglota simples: uma linha por idioma, empilhadas, "
               "inglês no topo. Exige um vídeo NO YOUTUBE com dublagem "
               "automática — é de lá que sai o texto de cada idioma.",
        entrega="`<nome>_final_idiomas[_img].mp4` + um `<nome>_<lang>.srt` por idioma.",
        depende_de=("legenda-unica",),
        custo="Nenhum: nem chave de API nem GPU. A repartição era por IA e hoje "
              "é ancorada na GRADE de tempos das legendas do YouTube (as faixas "
              "de um mesmo vídeo compartilham a mesma grade, o que dá uma âncora "
              "exata entre idiomas), com repartição proporcional de reserva.",
        armadilha="O texto dos outros idiomas NÃO é traduzido aqui — é colhido "
                  "da dublagem automática e das legendas de um vídeo que já "
                  "está no YouTube (`URL_YOUTUBE`). Num capítulo inédito, você "
                  "precisa publicar primeiro (pode ser não listado) e esperar o "
                  "YouTube gerar as faixas. Sem essa URL a jornada não começa.",
        passos=(
            Passo("caption-multilang-sources-gather",
                  "`<nome>_yt_<lang>.srt`, `<nome>_audio_<lang>.wav`, `<nome>_whisper_<lang>.srt`",
                  ou=("caption-multilang-zh-sources-gather",),
                  nota="Pede `URL_YOUTUBE` na Configuração. Duas fontes de texto "
                       "por idioma; você escolhe qual confia mais em "
                       "`FONTE_TEXTO_IDIOMA` (o padrão é `yt`, e só ele TEM grade). "
                       "MANTENHA o idioma mestre na lista: a legenda do YouTube "
                       "dele é a grade que alinha todos os outros."),
            Passo("caption-multilang-generate", "`<nome>_<lang>.srt` por idioma",
                  ou=("caption-multilang-zh-generate",)),
            Passo("caption-multilang-burn", "`<nome>_final_idiomas[_img].mp4`",
                  ou=("caption-multilang-zh-burn",),
                  nota="A variante `-zh-` grava com sufixo `_zh`, então as duas "
                       "versões convivem na mesma pasta."),
        ),
    ),

    Jornada(
        id="multicolor",
        tipo=VIDEO,
        titulo="Nível 3 · legenda multicor, uma cor por classe gramatical",
        quando="O carro-chefe do canal: cada palavra pintada pela função que "
               "exerce na frase.",
        entrega="`<nome>_final_multicolor[_img].mp4`, mais o `.ass`, a "
                "classificação por idioma em JSON, a ANÁLISE BRUTA do "
                "Stanza/Kiwi e o par de arquivos da revisão (HTML pra achar o "
                "erro de cor, CSV pra corrigir).",
        depende_de=("multi-idioma",),
        custo="Stanza (latinos) + Kiwi (coreano), CPU. Só na PRIMEIRA vez: o "
              "bruto do analisador fica salvo, e rodar de novo remapeia a partir "
              "dele em segundos — inclusive aplicando regra de cor que mudou "
              "desde então, sem apagar o que você corrigiu à mão.",
        passos=(
            Passo("caption-multicolor-generate",
                  "`legendas_<nome>.ass`, `<nome>_classificacao_multicolor_<lang>.json`, "
                  "`<nome>_analise_bruta_<lang>.json` e `<nome>_classes_revisar.{html,csv}`",
                  ou=("caption-multicolor-zh-generate",),
                  nota="Quatro camadas dentro dele: bruto (a origem), mapeamento, "
                       "central de correções automáticas "
                       "(`dados_lexico/classes-correcoes.json`) e a sua correção "
                       "manual pelo CSV. A célula 5 aponta ONDE olhar em vez de "
                       "pedir que você leia milhares de peças. A variante `-zh-` "
                       "sai como `legendas_<nome>_zh.ass`."),
            Passo("caption-multicolor-burn", "`<nome>_final_multicolor[_img].mp4`",
                  nota="UM notebook serve as duas variantes: ele lê o sufixo `_zh` "
                       "do nome do `.ass` que você enviar e grava a saída "
                       "correspondente. Por isso não existe `-zh-burn`."),
        ),
        armadilha="Precisa dos `<nome>_<lang>.srt` do nível 2 — a classificação "
                  "roda em cima do texto já distribuído por idioma. Se a legenda "
                  "mudar depois, o bruto e a classificação salvos são DESCARTADOS "
                  "sozinhos (eles conferem o texto contra o SRT atual): sem isso o "
                  "vídeo sairia exibindo as palavras da versão anterior, com o SRT "
                  "novo parado ao lado.",
    ),

    # ── APOIO ────────────────────────────────────────────────────────────
    Jornada(
        id="sincronizar",
        tipo=APOIO,
        titulo="Trazer o GitHub pro Drive",
        quando="Sempre que o repositório mudar — e desconfie se fizer semanas "
               "que você não roda.",
        entrega="`pipeline/modulos`, `notebooks` e `dados_lexico` do Drive "
                "idênticos ao repositório, conferido por sha256.",
        custo="Segundos. Copia só o que mudou.",
        passos=(
            Passo("repositorio-sincronizar", "Drive igual ao repositório",
                  nota="Mostra o que vai mudar ANTES de mudar, e confere por "
                       "hash DEPOIS — copiar pra Drive montado falha calado."),
        ),
        armadilha="O código vive no GitHub e o Colab lê do Drive; sem esta "
                  "ponte os dois divergem em silêncio. Em 29/ago o Drive "
                  "estava 56 commits atrás — faltavam 10 notebooks e 7 "
                  "módulos. Teste rodado assim executa código velho e falha "
                  "por motivo que já não existe. A direção é uma só: "
                  "GitHub → Drive; edição feita direto no Colab e não levada "
                  "pro git é sobrescrita.",
    ),

    Jornada(
        id="conferir-audio",
        tipo=APOIO,
        titulo="O áudio fala o mesmo que o texto?",
        quando="Antes de fazer vídeo de um capítulo novo — e uma vez, pra "
               "calibrar o que é normal na sua gravação.",
        entrega="A lista de trechos onde a narração e o texto divergem, "
                "ordenada pelo tamanho.",
        depende_de=("biblia",),
        custo="Whisper 'small' com GPU: ~1 min por capítulo. A transcrição "
              "fica salva num .txt, então recomparar não paga de novo.",
        passos=(
            Passo("biblia-audio-conferir",
                  "`<nome>_whisper_bruto_<modelo>.txt` + o relatório de divergências"),
        ),
        armadilha="Whisper 'corrige' texto bíblico pro fraseado da King James "
                  "-- trocou 'King Herod' por 'Herod the king' no Mateus 2. "
                  "Reordenar palavra PARECE divergência real e não é. O que "
                  "decide é a FORMA: muitas diferenças pequenas é ruído, "
                  "poucas e grandes é divergência. Calibrado em 0,9625 "
                  "(Whisper 'small') num capítulo cujo texto é comprovadamente "
                  "o certo -- o PDF oficial do AudioTreasure bate 1,0000 com o "
                  "web-biblia.json.",
    ),

    Jornada(
        id="portao",
        tipo=APOIO,
        titulo="Portão de qualidade",
        quando="Antes de queimar (`.ass`) e antes de publicar (`.mp4`).",
        entrega="Um veredito — não gera arquivo nenhum.",
        custo="A camada do `.ass` é de milissegundos; a do `.mp4`, ~1 min.",
        passos=(
            Passo("portao-qualidade", "relatório aprovado/reprovado"),
        ),
        armadilha="Existe pra uma família de bugs que NÃO levanta exceção: cor "
                  "fora da paleta, glifo faltando, áudio estourado. Rode a "
                  "camada do `.ass` sempre — ela é de graça.",
    ),

    Jornada(
        id="compilacao",
        tipo=VIDEO,
        titulo="Compilação de versículos sortidos",
        quando="Quando o vídeo não é um capítulo, e sim uma seleção temática "
               "que pula entre livros.",
        entrega="`comp_<tema>.wav` + `.srt` + manifesto `.json`.",
        depende_de=("biblia",),
        custo="A transcrição é o caro, e o cache de tempos faz você pagar UMA "
              "vez por capítulo, pra sempre. A segunda compilação que usar "
              "Salmo 23 pula esse passo.",
        passos=(
            Passo("compilacao-montar", "`comp_<tema>.wav` + `.srt` + manifesto"),
        ),
        armadilha="A ordem é a que VOCÊ escreveu na seleção — pode repetir "
                  "capítulo e sair de ordem de propósito.",
    ),
)


#: Notebook que não pertence a jornada nenhuma, e o motivo. Sem este registro
#: o `verificar_repo()` acusaria o mesmo arquivo pra sempre, e verificador que
#: sempre reclama é verificador que ninguém lê.
EXCECOES: dict[str, str] = {
    "compilar-versiculos-teste":
        "Teste de um capítulo só, anterior ao compilacao-montar. Fica até a "
        "compilação rodar de verdade em produção (ver nomenclatura.EXCECOES).",
}


# ── Conferência ──────────────────────────────────────────────────────────────

def _notebooks_no_disco(raiz: Path) -> set[str]:
    return {p.stem for p in (raiz / "pipeline" / "notebooks").glob("*.ipynb")}


def verificar_repo(raiz: Path | str) -> list[str]:
    """Confere o mapa contra a pasta de notebooks. Lista vazia = bate.

    Três coisas que fariam o mapa mentir:
      1. notebook no disco que nenhuma jornada cita (entrou e ninguém ligou);
      2. jornada citando notebook que não existe (foi renomeado ou apagado);
      3. `depende_de` apontando pra jornada inexistente.
    """
    raiz = Path(raiz)
    problemas: list[str] = []

    no_disco = _notebooks_no_disco(raiz)
    citados = {n for j in JORNADAS for n in j.notebooks}
    ids = {j.id for j in JORNADAS}

    for nb in sorted(no_disco - citados - set(EXCECOES)):
        problemas.append(
            f"[órfão] {nb!r} não aparece em jornada nenhuma — "
            f"encaixe numa jornada ou registre em EXCECOES com o motivo")

    for nb in sorted(citados - no_disco):
        dono = next(j.id for j in JORNADAS if nb in j.notebooks)
        problemas.append(f"[fantasma] a jornada {dono!r} cita {nb!r}, que não existe")

    for nb in sorted(set(EXCECOES) - no_disco):
        problemas.append(f"[exceção morta] {nb!r} está em EXCECOES mas não existe mais")

    for j in JORNADAS:
        for dep in j.depende_de:
            if dep not in ids:
                problemas.append(f"[dependência] {j.id!r} depende de {dep!r}, que não é jornada")

    return problemas


def relatorio(raiz: Path | str) -> str:
    problemas = verificar_repo(raiz)
    n_nb = len({n for j in JORNADAS for n in j.notebooks})
    if not problemas:
        return (f"✅ O mapa bate com a pasta: {len(JORNADAS)} jornadas cobrindo "
                f"{n_nb} notebooks ({len(EXCECOES)} exceção(ões) registrada(s)).")
    linhas = [f"⚠️  {len(problemas)} divergência(s) entre o mapa e a pasta:"]
    linhas += [f"  {p}" for p in problemas]
    return "\n".join(linhas)


# ── Consultas ────────────────────────────────────────────────────────────────

def por_id(jid: str) -> Jornada:
    for j in JORNADAS:
        if j.id == jid:
            return j
    raise KeyError(f"jornada desconhecida: {jid!r} — use {sorted(j.id for j in JORNADAS)}")


def jornadas_de(notebook: str) -> list[Jornada]:
    """Em que jornadas este notebook aparece — a pergunta inversa do mapa."""
    return [j for j in JORNADAS if notebook in j.notebooks]


def caminho_ate(jid: str) -> list[Jornada]:
    """Todas as jornadas que precisam acontecer, em ordem, pra chegar nesta.

    Ordena por dependência (topológica). É a resposta pra "quero o vídeo
    multicor, começo por onde?".
    """
    vistas: list[str] = []

    def visitar(atual: str, pilha: tuple[str, ...] = ()) -> None:
        if atual in vistas:
            return
        if atual in pilha:
            raise ValueError(f"ciclo em depende_de: {' -> '.join((*pilha, atual))}")
        for dep in por_id(atual).depende_de:
            visitar(dep, (*pilha, atual))
        vistas.append(atual)

    visitar(jid)
    return [por_id(i) for i in vistas]


if __name__ == "__main__":
    import sys
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    print(relatorio(raiz))
