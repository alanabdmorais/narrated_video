# Configuração do pipeline — referência central

Este documento é o **catálogo único** de tudo que é configurável no pipeline:
convenções de nome de arquivo (`config.py`), pastas do Drive, e todas as
planilhas Google Sheets (ID, aba, para que serve, quem lê/escreve). Serve pra
responder "onde eu mudo X?" sem precisar abrir 19 notebooks + `config.py` toda
vez.

Não duplica os comentários que já existem em `modulos/config.py` — só organiza
tudo num lugar só e cruza com o que cada notebook realmente expõe na célula de
Configuração hoje.

> **Este documento é referência, não roteiro.** Ele responde "como se chama
> isto?" e "o que este parâmetro faz?". Pra responder **"eu quero um resultado
> assim, o que eu rodo?"**, veja [`JORNADAS.md`](JORNADAS.md) — o mapa das 13
> jornadas de notebook, gerado de `modulos/jornadas.py` e conferido contra a
> pasta de notebooks.

## 1. Identidade do vídeo (por vídeo, muda toda vez)

Definido na célula "⚙️ Configuration" de cada notebook `video-base-*.ipynb`,
passado pro `PipelineConfig(...)`:

| Variável | Exemplo | Descrição |
|---|---|---|
| `NOME_ORACAO` | `"40_Matt_02"` | Identificador curto do vídeo — prefixo de TODOS os arquivos gerados (ver seção 3) e nome da pasta em `videos/`. |
| `TEXTO_ORACAO` | texto em inglês | Texto pro Edge TTS — ignorado se já existir `<nome>_roteiro.txt` no Drive. |
| `VOZ_EDGE` | `"en-US-GuyNeural"` | Voz do Edge TTS — precisa bater com o idioma de `TEXTO_ORACAO`. |
| `IDIOMA_MESTRE` | `"en"` | Idioma mestre de timestamps (Whisper) e texto (roteiro/legenda do YouTube nesse idioma). |
| `VOLUME_NARRACAO` / `VOLUME_MUSICA` | `1.0` / `0.25` | Volume relativo narração × trilha de fundo. |
| `VELOCIDADE_AUDIO` | `1.0` | Velocidade da narração (0.9 = 10% mais devagar). |
| `CAPITULO` | `1` | Capítulo bíblico (usado nos nomes `match_*`/`lacunas_match_*` e na busca de contexto). |
| `PASTA_DRIVE_RAIZ` | `"narrated_video"` | Fixo pro projeto inteiro — não mexer. |

## 2. Planilhas de origem dos clipes (Pixabay)

Duas planilhas alimentam o pipeline com mídia bruta — vídeo e imagem — cada
uma com sua própria coluna de status que marca linha já usada
(`NOME_COLUNA_STATUS_PLANILHA`, padrão `"Downloading Ok"`, compartilhada pelas
duas):

| | ID | Aba | Coluna Tags | Default em `config.py` |
|---|---|---|---|---|
| **Vídeos** (`pixabay_stock`) | `1bF7hnGSY7AALm4ZAS5owWNpiSTdgArW4ahAuVZaHPL0` | `pixabay_stock` | `Tags_Biblia_PT` | `ID_PLANILHA_DRIVE` (tem default) |
| **Imagens** (`image-stock`) | `1P2LydKeeoU5MsAPNl1qhno5qsD1q5BbMOeTbblOVU1E` | `image-stock` | `Tags_Semelhantes_PT` (ou `Tags_Biblia_PT`) | `ID_PLANILHA_IMAGENS_DRIVE` (default `""` — obrigatório preencher quando `MODO_CLIPE="imagem"`) |

Notebooks que expõem `ID_PLANILHA_VIDEOS`/`NOME_ABA_VIDEOS` e/ou
`ID_PLANILHA_IMAGENS`/`NOME_ABA_IMAGENS` como variável editável na célula de
Configuração: `pixabay-video-descriptions.ipynb`, `pixabay-image-descriptions.ipynb`,
`pixabay-image-seed.ipynb`, `pixabay-image-seed-biblia-completa.ipynb`,
`match-scene-verse.ipynb`, `video-base-imagem-padrao.ipynb` (só imagens),
`video-base-imagem-versiculo.ipynb` (só imagens),
`video-base-imagem-versiculo-trilhas.ipynb`,
`video-base-imagem-versiculo-trilhas-efeitos.ipynb`, e agora também
`video-base-video-padrao.ipynb`/`video-base-video-versiculo.ipynb` (planilha de
vídeos — antes só vinham do default de `config.py`, sem aparecer na célula).

## 3. Biblioteca de Match (match cena↔versículo + tags de clima/efeito)

**Planilha "Biblioteca de Match"** — ID `1i67VxksAkWYx1cZ_QeoesGXsW28hcA0p5IIfhjx8VHE`
(variável `ID_PLANILHA_BIBLIOTECA_MATCH` nos notebooks).

| Aba | Nome padrão | Criada/gerida por | Conteúdo |
|---|---|---|---|
| Cache de match | `biblioteca_match` | `abrir_ou_criar_biblioteca_match()` | Resultado de match já calculado (evita gastar IA de novo). |
| Texto bíblico completo | `biblia_texto` | **manual/externa** — não gerida por código | Texto de referência, populada fora do pipeline. |
| Tags por evento | `evento_tags` | `garantir_aba_evento_tags()` | Tags de clima/efeito por evento bíblico (capítulo_ini/fim). |
| Tags por título | `titulo_tags` | `garantir_aba_titulo_tags()` | Igual acima, granularidade de versículo (versiculo_ini/fim). |
| Tags por versículo | `versiculo_tags` | `garantir_aba_versiculo_tags()` | Palavras-chave extraídas por versículo. |
| Eventos já semeados | `eventos_semeados` | `garantir_aba_eventos_semeados()` | Marca quais itens já tiveram busca em lote feita (seed). |

Usada por: `match-scene-verse.ipynb`, `pixabay-image-seed.ipynb`,
`pixabay-image-seed-biblia-completa.ipynb`,
`video-base-imagem-versiculo-trilhas.ipynb`/`-trilhas-efeitos.ipynb` (só a aba
`versiculo_tags`, pra registrar tags de clima/efeito do match),
`sincronizar-evento-titulo-tags.ipynb`.

## 4. Estoque de som (trilha + efeito sonoro)

**Planilha `Biblioteca_Match_Audio`** — ID
`1VkYaApN1F7X4-52CD0_I-TpKwc2v3XuhUJrIRnZ0Q94` (variável
`ID_PLANILHA_BIBLIOTECA_MATCH_AUDIO` / `ID_BIBLIOTECA_MATCH_AUDIO` conforme o
notebook).

- Aba única `trilha_stock` (nome mantido de propósito — é o que o painel de
  revisão externo, Apps Script fora do repo, lê). Guarda TANTO trilha quanto
  efeito sonoro, diferenciados pela coluna `categoria` (`"trilha"`, `"efeito"`
  ou `"ambos"`). Gerida por `garantir_aba_estoque_som()` /
  `sincronizar_estoque_som()` em `trilha_pipeline.py`.
- Alimentada por `organizar-trilha-audio.ipynb` (clima) e
  `organizar-efeitos-audio.ipynb` (efeito pontual) — os dois escrevem na MESMA
  aba.
- Lida por `video-base-imagem-versiculo-trilhas.ipynb` (categoria `"trilha"`) e
  `video-base-imagem-versiculo-trilhas-efeitos.ipynb` (categorias `"trilha"` e
  `"efeito"`).

### Fontes intermediárias (só usadas por `organizar-trilha-audio.ipynb`)

| Planilha | ID | Papel |
|---|---|---|
| `Freesound_Audio_Manager` | `1ieROA_Yy_1fM_qZ_uweLycEJ81l6LwZVJzbYj-sAUA4` (aba `Página1`) | **Externa, não faz parte do repo.** Busca automática de URLs via API do Freesound — fonte de leitura, nunca escrita pelo pipeline. Colunas fixas (formato do Freesound), por isso `COLUNAS_TRILHA_STOCK` preserva as 10 colunas originais em ordem. |
| `Freesound_Audio_Stock` | `1uJj5-Qxs6okWQBi82Xu5Ybjdy8z9kcyFHvmzVukRaBs` | Normalização intermediária do Freesound Manager (só clima de verdade). Criada automaticamente na 1ª execução se o ID vier em branco. |
| `Pixabay_YT_Audio_Stock` | `15knVuLxpZaSXb3ariKPojnNL14eS7AuOuLvKXPh8uEU` | Varredura das pastas `audio/<clima>/` no Drive (Pixabay + YouTube Audio Library). Idem — criada automaticamente se vazio. |

`organizar-trilha-audio.ipynb` também usa `CAMINHO_PASTA_AUDIO_DRIVE` (pasta no
Drive com subpastas por clima) e `URL_PROXY_APPS_SCRIPT` (Web App do
Apps Script que serve os arquivos de áudio via proxy, contornando o bloqueio do
Google pra embutir Drive em `<audio>`). `organizar-efeitos-audio.ipynb` usa
`CAMINHO_PASTA_EFEITOS_DRIVE` (subpastas por objeto/ação, ex: `Efeitos/porta/`).

## 5. Resumo de todas as planilhas (IDs)

| Planilha | ID |
|---|---|
| Pixabay vídeos (`pixabay_stock`) | `1bF7hnGSY7AALm4ZAS5owWNpiSTdgArW4ahAuVZaHPL0` |
| Pixabay imagens (`image-stock`) | `1P2LydKeeoU5MsAPNl1qhno5qsD1q5BbMOeTbblOVU1E` |
| Biblioteca de Match | `1i67VxksAkWYx1cZ_QeoesGXsW28hcA0p5IIfhjx8VHE` |
| Biblioteca_Match_Audio (estoque único de som) | `1VkYaApN1F7X4-52CD0_I-TpKwc2v3XuhUJrIRnZ0Q94` |
| Freesound_Audio_Manager (externa) | `1ieROA_Yy_1fM_qZ_uweLycEJ81l6LwZVJzbYj-sAUA4` |
| Freesound_Audio_Stock (intermediária) | `1uJj5-Qxs6okWQBi82Xu5Ybjdy8z9kcyFHvmzVukRaBs` |
| Pixabay_YT_Audio_Stock (intermediária) | `15knVuLxpZaSXb3ariKPojnNL14eS7AuOuLvKXPh8uEU` |

## 5b. Convenção de nomes — `modulos/nomenclatura.py`

Nome de arquivo é **contrato**: um notebook procura `40_Matt_02_roteiro.txt`, e
se alguém salvar `40_matt_02_roteiro.txt` o pipeline não acha e ninguém entende
por quê. A regra mora em código, executável, e não só aqui — `.md` não é lido
na hora do aperto.

```bash
python3 pipeline/modulos/nomenclatura.py     # varre e reporta
```

### As sete famílias

| Família | Exemplo | Regra |
|---|---|---|
| notebook | `biblia-audio-baixar.ipynb` | kebab-case |
| módulo | `tempos_cache.py` | snake_case (PEP 8) |
| arquivo do vídeo | `40_Matt_02_roteiro.txt` | `{projeto}_{papel}[_{idioma}]` |
| capítulo | `40_Matt_02` | `{NN}_{SiglaOSIS}_{CC}` |
| compilação | `comp_salmos_esperanca` | `comp_{tema}`, tudo minúsculo |
| aba de planilha | `biblioteca_match` | snake_case |
| pasta do Drive | `assets/biblia_audio` | snake_case |

**Quem constrói cada nome tem dono, e não é este módulo** — ele guarda a regra
e a conferência, não a fábrica:

| Nome | Dono |
|---|---|
| arquivo do vídeo | `config.py`, as propriedades `nome_*` |
| capítulo | `biblia_livros.Livro.nome_projeto()` |
| compilação | `compilacao_pipeline.nome_compilacao()` |

### A ação vai por último

`biblia-audio-baixar`, não `baixar-biblia-audio`. Vale pra notebook, e a
conferência é separada da grafia — um nome pode estar em kebab-case impecável
e ainda assim com o verbo na frente.

Não é preciosismo: **verbo no fim faz a ordenação alfabética agrupar por
assunto**. Com o verbo na frente, `organizar-trilha-audio` aparece longe de
`trilha-*`, que é justamente o que ele manipula — e você procura pelo assunto,
não pela ação.

Quatro nomes atuais violam e ficam registrados: `organizar-efeitos-audio`,
`organizar-trilha-audio`, `sincronizar-evento-titulo-tags` e
`pixabay-image-seed-biblia-completa` (a ação no meio). A mensagem do
verificador já sugere o conserto: *"a ação 'organizar' não está no fim — tente
trilha-audio-organizar"*.

### O idioma é sempre sufixo

`40_Matt_02_whisper_en.srt`, nunca `40_Matt_02_en_whisper.srt`. Assim
`nome.rsplit("_", 1)` devolve o idioma sem adivinhação — e adivinhação erra
calada. É o que `idioma_do_arquivo()` faz.

### As exceções são registradas, não consertadas

`EXCECOES` lista os 16 nomes fora do padrão que **ficam como estão**, cada um
com o motivo:

- **`image-stock`** (aba, com hífen) — aba viva da planilha de imagens, com
  dados dentro. Renomear quebraria a planilha e todos os notebooks que a leem,
  pra ganhar só consistência cosmética.
- **A cadeia `caption-*`, `match-scene-verse`, `pixabay-*-descriptions`** (14
  notebooks em inglês) — nomeados antes de o projeto assentar em português.
  Renomear quebra o link salvo de cada um no Colab: custo real, ganho nenhum.
- **`compilar-versiculos-teste`** — anterior ao `compilacao-montar`; sai quando
  a compilação rodar em produção.

Sem esse registro, o verificador acusaria os mesmos 16 nomes pra sempre — e
verificador que sempre reclama é verificador que ninguém lê. É a mesma lição da
checagem de fonte no portão de qualidade: **a gravidade tem que vir do
resultado, não do formato**.

> Exceção registrada é decisão. Exceção esquecida é bagunça. Nome novo fora do
> padrão sem entrada em `EXCECOES` aparece no relatório.

### Renomear quebra referência, não arquivo

`nomenclatura.referencias_fantasma()` varre módulos, notebooks e documentação
atrás de qualquer nome citado com a extensão de notebook que não exista na
pasta `pipeline/notebooks/`.

Existe porque a onda de rename anterior deste projeto deixou **14 referências
podres** — e três delas em mensagem de erro que você vê justamente na hora do
aperto:

```
"Vídeo base não encontrado: {…}. Rode o video-base.ipynb primeiro."
                                        ↑ não existe desde o rename anterior
```

A pasta `pipeline/notebooks.backup/` guardava os arquivos antigos e não
protegeu nenhuma dessas: **não era o arquivo que estava em risco.** Renomear
não quebra arquivo, quebra quem fala dele — e quebra calado, porque o notebook
continua rodando.

O checador ignora **padrão** de propósito: `video-base-*.ipynb` é a forma
honesta de falar dos seis notebooks de vídeo base de uma vez, então o
lookbehind descarta o que vem depois de curinga ou hífen. E texto que fala da
AUSÊNCIA de um notebook (a decisão adiada 9.1 propondo um `video-base.ipynb`
futuro, por exemplo) vai pro `MENCOES_DE_AUSENCIA`, registrado por
**(arquivo, nome)** — o mesmo nome pode ser proposta legítima num documento e
referência podre num módulo.

## 6. Nomes de arquivo — todos derivados de `NOME_ORACAO`

Tudo isso vem de propriedades/métodos de `PipelineConfig` em `modulos/config.py`
— nunca digite esses nomes à mão, sempre use `config.<nome>`.

### Áudio / vídeo base

| Propriedade | Padrão gerado | Observação |
|---|---|---|
| `NOME_AUDIO` | `<nome>_audio.wav` | Narração. |
| `nome_audio_idioma(lang)` | `<nome>_audio_<lang>.wav` | Dublagem automática baixada do YouTube. |
| `NOME_VIDEO_BASE` | `<nome>_video_base[_img].mp4` | Sufixo `_img` só quando `MODO_CLIPE="imagem"`. **Nome canônico** — todos os notebooks de legenda/burn leem exatamente este arquivo, inclusive as variantes trilhas/efeitos (que sobrescrevem o mesmo nome). Nível 0 dos vídeos finais (ver tabela de níveis abaixo). |
| `NOME_VIDEO_FINAL` | `<nome>_final[_img].mp4` | Nível 1 — legenda única (Single Subtitle). |
| `NOME_VIDEO_FINAL_IDIOMAS` | `<nome>_final_idiomas[_img].mp4` | Nível 2 — legendas multi-idioma empilhadas (1 cor por idioma). |
| `NOME_VIDEO_FINAL_MULTICOLOR` | `<nome>_final_multicolor[_img].mp4` | Nível 3 — mesmo nível 2, com classificação gramatical (Stanza/Kiwi, cor por classe). Nome renomeado de `_com_legenda_colorida` pra alinhar com o padrão `_final`/`_final_idiomas` — ver aviso de migração abaixo. |
| `NOME_VIDEO_FINAL_CLASSIFICACAO(_BASICO)` | `<nome>_final_classificacao[_basico].mp4` | ⚠️ Obsoleto — ramo antigo (IA), não é um nível — só compatibilidade com vídeos antigos. |

**Os 4 níveis de vídeo final** (cada um soma um recurso em cima do anterior, todos coexistem na mesma pasta):

```
NOME_VIDEO_BASE  →  NOME_VIDEO_FINAL  →  NOME_VIDEO_FINAL_IDIOMAS  →  NOME_VIDEO_FINAL_MULTICOLOR
 (sem legenda)      (legenda única)       (multi-idioma, cor única)    (multi-idioma, cor gramatical)
```

> **Migração do rename `_com_legenda_colorida`→`_final_multicolor`:** vídeos já
> gerados antes dessa mudança (ex: `40_Matt_02`) têm o arquivo real no Drive
> com o nome antigo (`40_Matt_02_com_legenda_colorida.mp4`) — renomeie
> manualmente pra `_final_multicolor` antes de rodar `caption-multicolor-burn.ipynb`
> de novo pra esse vídeo.

### Legendas (SRT/ASS)

| Propriedade | Padrão gerado | Observação |
|---|---|---|
| `NOME_SRT_PT_WHISPER` | `<nome>_whisper_<IDIOMA_MESTRE>.srt` | Transcrição Whisper sobre a narração — mestre de SEGMENTAÇÃO. Nome usa "whisper" (renomeado de "edge") porque é sempre o Whisper que gera esse SRT, venha a narração do Edge TTS ou não. |
| `nome_srt_whisper(lang)` | `<nome>_whisper_<lang>.srt` | Transcrição Whisper sobre áudio dublado desse idioma. |
| `nome_srt_yt(lang)` | `<nome>_yt_<lang>.srt` | Legenda original do YouTube (mestre de texto). |
| `NOME_SRT_PT` / `nome_srt(lang)` | `<nome>_<IDIOMA_MESTRE ou lang>.srt` | Legenda já distribuída/corrigida por idioma. |
| `nome_legenda_unica` | = `NOME_LEGENDA_UNICA` (se preenchido) senão `NOME_SRT_PT_WHISPER` | SRT escolhido pro vídeo de legenda única. |
| `nome_legenda_mestre` | = `NOME_LEGENDA_MESTRE` (se preenchido) senão `nome_legenda_unica` | Molde de segmentação/tempos pros outros idiomas (Language Subtitles) — é o mestre de SEGMENTAÇÃO, ver seção 6b. |
| `nome_srt_versiculo` | `<nome>_versiculo.srt` | Indicador de livro:versículo (overlay) NUM SÓ IDIOMA (o mestre, ex: "Matt 2:4") — usado pelo vídeo de legenda única (`caption_pipeline.py`). |
| `nome_srt_versiculo_multilingue` | `<nome>_versiculo_multilingue.srt` | Mesmo indicador, mas combinando as abreviações de TODOS os idiomas configurados (ex: "Matt/Mt/마 2:4") — usado pelo vídeo de legendas multi-idioma (`language_captions_pipeline.py`), que já empilha vários idiomas na tela. |

`PROTEGER_LEGENDA_MESTRE` (bool, padrão `True`) — impede sobrescrever a legenda
mestre sem querer.

### Arquivos `.ass` (legenda já queimável, gerados por `renderizacao.py`/`ffmpeg_utils.py`)

Não vêm de propriedade de `config.py` — cada função de geração usa seu próprio
nome fixo (`caminho_saida`, default se não for passado outro):

| Função | Nome padrão | Usada por |
|---|---|---|
| `gerar_ass_simples()` | `legenda_unica_<nome>.ass` | Legenda única (1 idioma) — `caption_pipeline.py` |
| `gerar_ass()` | `legendas_idiomas_<nome>.ass` (passado explícito) | Multi-idioma **cor única** (1 cor por idioma) — `language_captions_pipeline.py` |
| `gerar_ass()` (mesma função, default) | `legendas_<nome>.ass` | Multi-idioma **multicolor** (1 cor por função gramatical, Stanza/Kiwi) — `caption-multicolor-generate.ipynb` |
| `gerar_ass_versiculo()` | `versiculo_<nome>.ass` | Indicador de livro:versículo (ASS, camada separada) |

Sempre 1 arquivo `.ass` por vídeo (nunca por idioma — mesmo no multi-idioma,
todos os idiomas já vêm empilhados dentro do mesmo arquivo).

### Classificação gramatical intermediária (multicolor)

| Propriedade | Padrão gerado | Observação |
|---|---|---|
| `nome_classificacao_multicolor(lang)` | `<nome>_classificacao_multicolor_<lang>.json` | Resultado bruto do Stanza/Kiwi já filtrado (palavra/peça + classe, por bloco), 1 arquivo por idioma. Salvo automaticamente por `caption-multicolor-generate.ipynb` — se esse arquivo já existir no Drive na próxima execução, é usado no lugar de rodar o Stanza/Kiwi de novo, então dá pra baixar, corrigir a `classe` de alguma peça errada à mão, e resubir com o mesmo nome antes de gerar o `.ass`. |

Serialização em `renderizacao.py`: `salvar_classificacao_multicolor()`/
`carregar_classificacao_multicolor()`.

> **Migração do rename edge→whisper:** vídeos já gerados antes dessa mudança
> (ex: `40_Matt_02`) têm arquivos reais no Drive com o nome antigo
> (`40_Matt_02_edge_en.srt` etc.) — renomeie-os manualmente pra `_whisper_`
> antes de rodar os notebooks de novo para esse vídeo, ou aponte
> `NOME_LEGENDA_UNICA`/`NOME_LEGENDA_MESTRE` pro nome antigo enquanto não
> renomear.

### Match cena↔versículo / roteiro

| Propriedade | Padrão gerado |
|---|---|
| `nome_roteiro` | `<nome>_roteiro.txt` (`MODO_ROTEIRO="padrao"`, sem versículo) |
| `nome_roteiro_versiculos` | `<nome>_roteiro_versiculos.txt` (`MODO_ROTEIRO="versiculo"`, padrão) |
| `nome_match_json(capitulo)` | `match_<nome>_cap<capitulo>.json` |
| `nome_lacunas_match(capitulo)` | `lacunas_match_<nome>_cap<capitulo>.txt` |

## 6b. Os 3 "mestres" do vídeo (áudio, palavras, segmentação)

O vídeo tem 3 papéis de "mestre" — cada um é normalmente 1 arquivo só, mas às
vezes é o resultado de uma mescla que **você faz manualmente fora do
pipeline** (o pipeline não tenta automatizar essas mesclas — é frágil demais
pra fazer bem; só a mescla de segmentação, abaixo, é feita pelo próprio
código). Nos 3, o nome do arquivo NÃO carrega sufixo `_mestre` — o papel de
"mestre" vem do CAMPO de config que aponta pra ele, não de uma marca no nome
do arquivo (mesmo padrão de `nome_legenda_unica`). Também não carregam sufixo
de idioma — só há 1 áudio/roteiro mestre por vídeo, então não há o que
desambiguar (diferente de `nome_audio_idioma(lang)`/`nome_srt_yt(lang)`, que
têm um arquivo por idioma-alvo e por isso precisam do sufixo).

| Papel | Config | Default | Mescla feita por |
|---|---|---|---|
| **Áudio** | `nome_audio_mestre` (override: `NOME_AUDIO_MESTRE`) | `NOME_AUDIO` (`<nome>_audio.wav`) | N/A — normalmente 1 arquivo só, sem mescla. |
| **Palavras** | `nome_palavras_mestre` (override: `NOME_PALAVRAS_MESTRE`) | `nome_roteiro_versiculos` (`MODO_ROTEIRO="versiculo"`, padrão) ou `nome_roteiro` (`MODO_ROTEIRO="padrao"`) | **Você, manualmente** — roteiro mesclado com a transcrição Whisper da dublagem do YouTube (pra pegar palavra que a dublagem falou diferente do escrito). Salve o resultado por cima do mesmo arquivo no Drive. |
| **Segmentação** | `nome_legenda_mestre` | `nome_legenda_unica` (Whisper) | **O próprio pipeline**, bem — `alinhar_versiculos()` em `srt_utils.py` mescla o Whisper com o roteiro-versículo (empresta tempo início/fim pra cada versículo), com fusão automática de versículo curto demais pro vizinho (elimina gap/flicker — `calcular_segmentos_versiculo()` em `match_pipeline.py`). Alimenta as decisões de trilha, efeitos e cenas. |

Pros idiomas-alvo (não-mestre): não têm roteiro próprio. O texto vem de
`nome_srt_yt(lang)` e/ou `nome_srt_whisper(lang)` (mesclados manualmente por
você, mesma lógica de "palavras mestre" acima) — a segmentação, esses idiomas
simplesmente herdam os mesmos blocos/tempos do mestre (`redistribuir_idiomas()`
não calcula segmentação própria por idioma).

`NOME_AUDIO_MESTRE`/`NOME_PALAVRAS_MESTRE` — vazio por padrão, mesmo padrão de
override de `NOME_LEGENDA_UNICA`/`NOME_LEGENDA_MESTRE`: preencha só se quiser
apontar pra um arquivo com outro nome já salvo em `pasta_oracao`.

> `<nome>_edge_audio.wav`/`<nome>_edge_audio_<lang>.wav` — nome reservado pra
> quando o áudio for **especificamente gerado pelo Edge TTS** (não em uso
> agora, não implementado). Ordem confirmada: "edge" vem ANTES de "audio" —
> já existe um arquivo real nesse padrão no Drive (`40_Matt_02_edge_audio.wav`).

### Modo versículo: a campeã é sua, o aviso é meu

No modo **padrão** é o sistema que sorteia a foto, então descartar retrato é
barato: pula pra próxima linha. No modo **versículo** quem escolhe a campeã é
você, e descartar significaria desfazer sua escolha. Por isso
`DESCARTAR_IMAGEM_RETRATO` **não age aqui** — a campeã escolhida é sempre
usada.

Mas usada calada seria pior: uma campeã em pé perde ~2/3 da altura no corte
pra 16:9, e o vídeo sai pronto com a imagem decapitada. `baixar_clipes_imagem_por_versiculo()`
avisa antes, nomeando versículo, título e medidas:

```
⚠️ 2 campeã(s) em formato retrato — o corte pra 16:9 vai comer cerca de 2/3
   da altura. Considere escolher outra no match:
     v7 — sunrise (1080x1920)
     v14 — prayer (1200x1800)
```

Quem troca a campeã é você; o código só para de deixar isso passar em branco.

**E o buraco que isso revelou.** O modo versículo montava o `Clipe` só com
`url` — sem `urls_alternativas`. Ou seja, a reserva contra link vencido
protegia o modo padrão e **não** o modo versículo, que é justamente onde ela
pesa mais: um match salvo há meses guarda o link assinado, já vencido, e o
capítulo inteiro morreria com 400 sem nada pra recuperar. Agora
`carregar_biblioteca()` carrega `URL Thumbnail`, `Largura` e `Altura` junto do
candidato e esses campos viajam pelo match até o vídeo.

Planilha de vídeo não tem essas colunas, e match salvo na
`Biblioteca_Match_Audio` também não guarda thumbnail — nos dois casos os
campos ficam vazios e quem consome trata a ausência. **Inventar valor seria
pior que não ter.**

### Tarja preta na foto: o enquadramento e a orientação

Duas causas independentes, e as duas precisavam de conserto.

**1. O enquadramento acolchoava.** `imagem_para_clipe()` usava
`force_original_aspect_ratio=decrease` + `pad` — encolhe até a foto INTEIRA
caber e completa o resto com preto. Poucas fotos do Pixabay são exatamente
16:9, então quase toda uma ganhava tarja; numa foto em pé, a tarja comia a
maior parte da tela. Pra um **fundo** isso é o avesso do que se quer: a foto
está ali pra ocupar a tela, não pra ser exibida inteira.

`ENQUADRAMENTO_IMAGEM` (padrão `"preencher"`) escolhe:

| Valor | Filtro | O que faz |
|---|---|---|
| `"preencher"` | `increase` + `crop` | amplia até cobrir e corta o que sobra |
| `"caber"` | `decrease` + `pad` | encolhe até caber, completa com preto |

**2. A semeadura não filtrava orientação.** O Apps Script que semeia os
**vídeos** sempre pediu `&orientation=horizontal` à API; o que semeia as
**imagens** não pedia. Por isso a planilha de fotos veio cheia de retrato.
`buscar_imagens_pixabay()` agora pede também.

Isso conserta a semeadura nova, não as linhas já gravadas — por isso
`DESCARTAR_IMAGEM_RETRATO` (padrão ligado) descarta na hora de usar as linhas
cuja `Altura > Largura`, pelas colunas que a própria planilha já tem, sem
baixar nada. Linha sem essas colunas passa: descartar pelo que não se sabe
erraria pro lado caro. Se sobrar pouca linha, o erro diz que o descarte
aconteceu e como desligá-lo.

> Foto em pé num vídeo deitado não tem saída boa — ou vira tarja dos dois
> lados, ou o corte come 2/3 da imagem e sobra o meio de uma pessoa sem a
> cabeça. **Barrar na origem é o único conserto que não perde nada;** os
> outros dois só escolhem qual perda.

**Sobre medir isto.** A primeira versão do teste lia o brilho das bordas com
`signalstats`, que não imprime nada sem `metadata=print`: vinha `-1` em tudo,
e `-1 < 20` passava tanto no teste de "sem tarja" quanto no de "com tarja".
Um teste que concorda com qualquer resultado é pior que nenhum. A versão que
vale reduz cada faixa de borda a um pixel (`crop,scale=1:1`) e lê os três
bytes crus.

### `modulos/pixabay_urls.py` — a regra de link num lugar só

Existem **três** caminhos que gravam URL de imagem do Pixabay, e os três
podiam cair na mesma armadilha do link assinado:

| Caminho | Onde grava | Triagem manual? |
|---|---|---|
| Apps Script "Pixabay Images" | planilha de busca (outra conta) | sim — você escolhe e cola no stock |
| `pixabay-image-seed` | **direto na `image-stock`** | não |
| `pixabay-image-seed-biblia-completa` | **direto na `image-stock`** | não |

Os dois notebooks são o caso mais perigoso: gravam na planilha que o sistema
lê, sem ninguém no meio pra notar. `_gravar_hits_pixabay()` guardava
`largeImageURL` — o link que vence.

A regra virou `pixabay_urls.py`, importado pelo `video_pipeline` e pelo
`pixabay_seed_pipeline`:

| Função | Serve pra |
|---|---|
| `url_estavel(hit)` | o que o semeador GRAVA na planilha |
| `urls_alternativas(thumb)` | a reserva que o vídeo TENTA quando o link falha |
| `e_link_assinado(url)` | reconhecer o link que vence, pra explicar o 400 |

O Apps Script continua fora do repo, copiado à mão — e é justamente por
existir esse terceiro lugar que os dois de cá não podem ser um quarto e um
quinto. **Regra repetida é regra que vai divergir**; foi assim que o filtro de
orientação ficou só no semeador de vídeos por meses.

### O link do Pixabay expira — a planilha morre inteira de uma vez

A API do Pixabay entrega dois links por imagem, e só um deles dura:

| Campo da API | Forma | Dura? |
|---|---|---|
| `largeImageURL` | `https://pixabay.com/get/g<assinatura>_1280.jpg` | **não** — assinado, expira |
| `previewURL` | `https://cdn.pixabay.com/photo/…/nome_150.jpg` | sim — arquivo direto |

O `estoque-imagem` guardou o primeiro na coluna `Imagem` e o segundo em
`URL Thumbnail`. Meses depois a assinatura não vale mais e o Pixabay responde
**400 Bad Request** — a planilha inteira para de funcionar de uma vez, sem
nada ter mudado nela. Foi o que travou o primeiro teste do Matt 02: 45 de 45.

O segundo link continua servindo, e a mesma pasta do CDN tem as outras
resoluções. `urls_alternativas_pixabay()` troca o `_150` do fim por `_1280`,
`_960`, `_640`, `_340`, `_150`, e `_processar_clipe_imagem` tenta a URL da
planilha primeiro e essas depois, avisando no log quando usa a reserva. A
planilha semeada há meses volta a funcionar sem re-semear.

Quando nem a reserva serve, a mensagem diz que a assinatura venceu e manda
refazer o estoque — 400 num link `/get/` é assinatura vencida, não imagem
removida, e sem essa frase o caminho natural é procurar defeito na rede ou na
imagem, os dois lugares errados. O reconhecimento é pela **forma** do link
(`/get/g<hex>_<largura>.<ext>`), não pelo domínio: o Pixabay já serviu esses
links de mais de um host.

**E o agrupamento das falhas passou a ser por forma, não por texto.** Agrupar
pelo texto inteiro não agrupava nada — cada imagem traz uma URL diferente, e
as 45 falhas idênticas saíam como "45 motivos distintos", despejando seis URLs
gigantes sem dizer o que houve. `_forma_da_falha()` troca a URL por `<url>`
antes de agrupar, e cada grupo imprime um exemplo:

```
  · download falhou (HTTPError: 400 Bad Request for url: <url>)  (×45)
      ex.: https://pixabay.com/get/g87a3c…_1280.jpg
```

> O mesmo erro de sempre, agora do meu lado: **a forma do problema é a
> informação; a contagem de variações do texto é ruído.**

### Falha de clipe/imagem diz o motivo

`_processar_clipe` e `_processar_clipe_imagem` faziam `return None` em **todo**
caminho de falha, com o motivo num `logger.debug` — que ninguém vê, porque os
notebooks ligam o log em INFO. O laço só sabia "veio vazio", e o erro final
dizia `Nenhuma imagem processada com sucesso` e mandava "veja os avisos ❌
acima" — avisos que **nunca tinham sido emitidos**, já que o `except` só
dispara em exceção e não havia nenhuma.

Agora os dois levantam `ClipeError` com o motivo real (status HTTP, tamanho
baixado, erro do FFmpeg, a URL culpada), o laço acumula em `falhas`, e
`_resumo_das_falhas()` põe tudo dentro da mensagem de erro, agrupando o que se
repete — 40 imagens no mesmo 404 são uma informação, não quarenta.

O caso mais comum que isso revela: a coluna `Imagem` da planilha com o link da
**página** do Pixabay em vez do link **direto** do arquivo. Baixa "com
sucesso", vem HTML de poucas centenas de bytes, e o FFmpeg recusa. Antes: erro
mudo. Agora:

```
Nenhuma das 46 imagens da planilha pôde ser usada. Motivos:
  · baixou só 312 bytes — não parece uma imagem. A coluna 'Imagem' tem que
    ser o link DIRETO do arquivo, não o da página do Pixabay — https://... (×46)
```

> A regra: **erro que não cabe numa mensagem vira uma sessão de tentativa e
> erro.** O motivo já estava na mão do código — só faltava carregá-lo até
> quem lê.

### Modo do fundo: detectado, não marcado

Os notebooks `*-burn` não montam vídeo — pegam o `<nome>_video_base*.mp4` que
já existe e escrevem legenda por cima. Só que esse nome depende de
`MODO_CLIPE`, e **nenhum dos quatro pedia esse campo**: caíam no padrão
`"video"` e procuravam `<nome>_video_base.mp4` enquanto o modo imagem tinha
gravado `<nome>_video_base_img.mp4`. E o sufixo não some no meio do caminho —
o resultado também sairia sem `_img`, colidindo com a versão de clipe.

Agora `MODO_CLIPE = None` na configuração e `config.detectar_modo_clipe()`
decide pelo arquivo que **existe** no Drive — mesma ideia do sufixo `_zh` que
o `caption-multicolor-burn` lê do nome do `.ass`. Com os dois presentes não há
palpite razoável: aí para e pede que você escolha à mão. Sem nenhum, para
dizendo o que procurou.

> A regra por trás das duas: **a variante do resultado vem do arquivo que você
> escolheu, não de uma opção que dá pra esquecer de marcar.** Opção esquecida
> não dá erro — dá o vídeo errado com o nome certo.

### De onde vem o TEXTO (a célula é o último recurso)

Nos notebooks `video-base-*`, `TEXTO_ORACAO` era a **primeira** fonte e o
roteiro do Drive a segunda. Agora é o contrário:

| # | Fonte | Quando ganha |
|---|---|---|
| 1 | `videos/<nome>/<nome>_roteiro.txt` | edição sua **para este vídeo** |
| 2 | `dados_lexico/web-biblia.json` | nome de capítulo bíblico |
| 3 | `TEXTO_ORACAO` da Configuração | quando nenhum dos dois responde |

O motivo é o mesmo do áudio: **o texto da célula fica parado de um vídeo pro
outro.** Um texto colado à mão há meses vencendo a Bíblia conferida (1,0000
contra três fontes independentes) é erro que não dá aviso nenhum — sai um
vídeo com o texto de outra pessoa e nada aponta pra isso.

Caindo na fonte 2, **os dois roteiros** são gravados na pasta do vídeo — e os
formatos são diferentes de propósito:

| Arquivo | Conteúdo | Quem usa |
|---|---|---|
| `<nome>_roteiro_versiculos.txt` | `1 Now when Jesus… 2 Where is he…` | match cena↔versículo, referência na legenda |
| `<nome>_roteiro.txt` | `Now when Jesus… Where is he…` | vira `TEXTO_ORACAO`, é o que o Edge TTS lê |

Da próxima vez sai pela fonte 1, e ficam dois arquivos pra você corrigir se
algo estiver torto.

> ⚠️ **Gravar um no lugar do outro não dá erro** — dá uma narração contando
> números em voz alta ("um. Agora quando Jesus… dois."), ou um match que não
> acha versículo nenhum. Foi o que a primeira versão desta célula fazia:
> gravava o texto marcado no arquivo da narração. `gerar_narracao()` existe
> pra que os dois saiam da mesma consulta, cada um no seu formato.

**A mensagem separa os dois motivos de falha.** Nome que não é capítulo
(`oracao_bom_dia`) e capítulo ausente do JSON pedem conferências em lugares
diferentes; a primeira versão culpava o nome pelos dois, o que mandaria você
olhar onde não está o problema.

### A célula do YouTube deixou de despejar 150 linhas

`yt-dlp -F` num vídeo com dublagem automática lista cada idioma em sete
formatos — ~150 linhas de uma vez, o suficiente pra travar o navegador (e
travou). Agora imprime só os idiomas disponíveis, numa linha;
`LISTAR_TUDO = True` traz a lista inteira quando você precisar do ID exato.

E a célula **se pula sozinha** quando já existe áudio na pasta do vídeo ou no
estoque. Ela é de quando o áudio precisava vir de algum lugar; com os 1.189
capítulos no Drive, baixar do YouTube por cima trocaria a gravação da fonte
por uma faixa recomprimida — e ainda dependeria do vídeo continuar no ar.

### A guarda da legenda mestre distingue o que ela mesma gerou

`PROTEGER_LEGENDA_MESTRE` recusa sobrescrever o SRT mestre pra não apagar uma
correção manual. Mas ela testava só **"o arquivo existe"** — e isso não é o
mesmo que **"foi corrigido"**.

Consequência: trocar `MODELO_WHISPER` de `base` pra `small` e rodar de novo
esbarrava na guarda, que protegia uma transcrição ruim que ninguém tinha
revisado. E a saída oferecida era desligar a proteção — que depois fica
desligada, e aí a correção seguinte é que se perde.

Agora o checkpoint guarda o `sha1` do SRT gerado. Na execução seguinte:

| Arquivo no Drive | Decisão |
|---|---|
| bate com o `sha1` registrado | é nosso, pode refazer |
| não bate | alguém editou — protege |
| sem `sha1` (sessão nova, checkpoint antigo) | protege, na dúvida |

> **Na dúvida, protege.** Perder uma correção é caro; refazer uma transcrição
> custa um minuto.

E a mensagem diz o modelo da transcrição anterior, que é o que faz você
entender por que ela apareceu.

### Aspa de citação não é divergência

`palavras_comparaveis()` preservava apóstrofo pra não quebrar `child's` e
`wouldn't` — certo. Só que a WEB usa **aspa simples** pra abrir e fechar fala
de profeta, e o mesmo caractere nas bordas do token virava parte da palavra:

```
'you    ≠  you
israel' ≠  israel
```

Três das 16 divergências do Mateus 2 eram isso — pontuação, no meio de uma
lista que existe justamente pra mostrar divergência de texto.

Agora o apóstrofo é tirado só das **bordas**: no meio continua sendo parte da
palavra.

> Ruído numa lista de conferência gasta a atenção que a lista pede. Quem lê
> 16 itens sabendo que 3 são falsos passa a ler os 16 com menos cuidado.

### A regra: faz sentido em inglês?

Quando não dá pra ouvir divergência por divergência, vale:

> **Faz sentido em inglês?** Sim → fica o Whisper. Não → vai pro roteiro.

Ela acerta o caso comum sem exigir o áudio: o Whisper erra grafia de nome
próprio, e grafia errada não é palavra. `Arkeleus` não existe; `Archelaus`
existe. `troubled in all Jerusalem` não é inglês; `troubled, and all Jerusalem`
é.

**A preferência é do Whisper, não do roteiro** — e isso é deliberado. A legenda
tem que dizer o que se ouve. Onde o David Williams lê diferente do escrito, o
Whisper está certo: `Herod the king` fica, mesmo o roteiro trazendo
`King Herod`, porque as duas formas são inglês e só o áudio decidiria.

> ⚠️ **A regra é julgamento, não automação.** `Seeing their treasures` é
> gramatical e mesmo assim está errado — os tesouros são deles, não algo que
> viram. Nenhum código decide isso; quem decide é quem lê. Por isso o
> `caption-single-revisar` mostra e não escreve.

Aplicada ao Mateus 2 (16 divergências, `small`), a regra trocou **4**:

| Bloco | Whisper | Vira | Por quê |
|---|---|---|---|
| 4 | `troubled in all Jerusalem` | `troubled, and all Jerusalem` | não é inglês |
| 19 | `Seeing their treasures` | `Opening their treasures` | não fecha o sentido |
| 33 | `weeping in great mourning` | `weeping and great mourning` | a frase é lista de três |
| 39 | `Arkeleus` | `Archelaus` | não é grafia de nada |

E manteve o Whisper em `Herod the king`, `for thus it is written`,
`shall come forth`, `that they shouldn't return`, `through the prophets`,
`in Rama` — todas inglês válido.

### `caption-single-revisar` — ouvir cada divergência

Toca o trecho do áudio de cada divergência (com folga de contexto), com as duas
versões do texto ao lado. Só o áudio separa "o Whisper errou" de "o Dave leu
diferente".

O trecho é achado pelo tempo do bloco, e o bloco vem de `cmp.posicoes_a` — não
de procurar o texto. Buscar pela primeira palavra do contexto casaria a
primeira ocorrência dela no capítulo, e **o áudio tocado seria o do lugar
errado**: uma revisão que confirma a coisa errada com o ouvido é pior que
nenhuma.

Não escreve no SRT. O contexto impresso é o trecho **normalizado** — sem
pontuação, minúsculo — que serve pra achar o lugar, não pra colar. Trocar
automático colaria texto sem pontuação no meio da legenda, e isso sairia no
vídeo.

### Conferir o Whisper contra o roteiro (sem substituir)

O SRT do `caption-single-generate` traz duas coisas, e só uma pode estar
errada:

| | Vem de | Confiável? |
|---|---|---|
| tempos | Whisper ouvindo o áudio | sim |
| texto | Whisper adivinhando grafia | erra nome próprio |

O roteiro tem o texto certo e nenhum tempo. Uma célula depois do preview
alinha os dois (`biblia_texto.comparar`, o mesmo `difflib` do
`alinhar_versiculos`) e lista **só onde divergem**, com o bloco aproximado.

> ⚠️ **Não substitua tudo pelo roteiro.** O David Williams lê ligeiramente
> diferente do escrito em alguns trechos — 0,9625 medido no
> `biblia-audio-conferir`. Substituir cego trocaria um erro visível (o nome
> errado) por um invisível: legenda dizendo o que o áudio não fala. Onde o
> Dave leu diferente, **o Whisper está certo** — a legenda tem que dizer o
> que se ouve.

Por isso a célula não escreve nada: ela mostra, e quem decide é você.

**O bloco vem do alinhamento, não de uma busca.** `comparar()` devolve
`posicoes_a` — o índice da palavra em A onde cada diferença começa — e o bloco
sai daí. A primeira versão procurava o trecho de contexto com `find()`: o
contexto começa numa palavra comum ("when", "was"), a busca casava a PRIMEIRA
ocorrência no texto todo, e uma diferença do bloco 39 saía anunciada como
bloco ~1.

> **Erro de localização é pior que nenhuma localização** — manda procurar no
> lugar errado, com confiança.

E a célula avisa quando `MODELO_WHISPER` é `tiny`/`base`: boa parte da lista
some trocando pra `small`. Numa execução com `base`, `chief priests` virou
`cheap priests`, `myrrh` virou `mirror`, `sent out` virou `sinned out` e
`reigning` virou `raining` — ruído que parece divergência de texto e não é.

### O sincronizador que se atualiza roda a versão velha

O Colab carrega o código do notebook na memória quando você **abre** o
arquivo. Se a cópia troca o `.ipynb` no Drive no meio da execução, as células
que continuam rodando são as **antigas** — e o que a versão nova faria (gravar
o `_manifesto.txt`, por exemplo) simplesmente não acontece, sem erro nenhum.

Foi o que houve: o sync rodou, disse "Drive idêntico byte a byte", e o
`caption-single-generate` seguinte reclamou `⚠️ sem _manifesto.txt`. Os dois
estavam certos — o manifesto era código que ainda não tinha rodado.

Agora o `repositorio-sincronizar` avisa quando se atualiza:

```
⚠️  ESTE NOTEBOOK SE ATUALIZOU NESTA RODADA.
    O que acabou de rodar é a versão ANTIGA...
    Feche a aba, abra de novo e rode outra vez.
```

> Um notebook que se reescreve precisa de **duas passadas**, e a primeira não
> tem como saber o que a segunda vai fazer. O melhor que ela pode fazer é
> dizer isso.

### `MODELO_WHISPER = "small"` é o padrão, e o motivo é medido

O padrão era `"base"`, com um comentário dizendo que era "bom pra narração
clara de um só locutor". Medido no Mateus 2, mesma narração:

| Modelo | Divergências contra o roteiro | Similaridade |
|---|---|---|
| `base` | 24 | 0,9521 |
| `small` | ~5 | — |

O `base` ouviu `cheap priests`, `and mirror`, `sinned out`, `was raining`,
`in a hold a surrounding`. Texto bíblico é cheio de nome próprio, e é neles
que ele tropeça.

**E esse SRT é o mestre de segmentação de todos os idiomas** — erro aqui se
propaga pro vídeo inteiro.

> Havia um motivo escondido pra insistir no padrão errado: a configuração vive
> **dentro do arquivo que o sync sobrescreve.** Trocar pra `small` à mão e
> sincronizar depois desfaz a troca, silenciosamente. Enquanto o padrão do
> repositório estiver errado, ele volta toda vez.

O padrão foi propagado depois pro resto do caminho: os dois
`caption-multilang-*-sources-gather` (que transcrevem as faixas dubladas) e os
próprios `def ...(modelo="small")` de `caption_pipeline` e
`language_captions_pipeline`. Duas razões pra não deixar só nos notebooks: as
faixas dubladas **não são em inglês**, onde o `base` erra mais, não menos; e um
`default=` de função é o valor que vale quando alguém chama sem passar nada —
deixar um `"base"` esquecido lá é o mesmo padrão errado, só escondido um nível
abaixo.

`compilacao-montar` ficou em `"base"` de propósito: lá o Whisper só serve pra
**alinhar por sequência de palavras**, que tolera erro de transcrição, e trocar
o modelo invalida o cache de tempos de todos os capítulos já processados.
Padrão certo não é padrão único — é o padrão que cabe no uso.

### `IDIOMA_MESTRE` já valia `"en"` na documentação e `"pt"` no código

A tabela de configuração deste arquivo dizia `"en"`. O `PipelineConfig` dizia
`"pt"`. Todo notebook passava `IDIOMA_MESTRE = "en"` explicitamente, então a
divergência nunca apareceu — até o dia em que um notebook novo esquecesse de
passar.

E o modo de falhar é traiçoeiro, porque o idioma mestre é o que as três funções
de coleta **pulam de propósito** (ele já foi resolvido no
`caption-single-generate`). Um `"pt"` esquecido não dá erro: ele pula o
português e processa o inglês, sobrescrevendo exatamente a legenda que foi
corrigida à mão. O padrão agora é `"en"`, que é o uso corrente — a Bíblia
poliglota, narrada pelo David Williams em inglês. Continua variável.

> Documentação e código discordando é uma das duas estar errada, e não dá pra
> saber qual sem olhar. Aqui a documentação estava certa — o que só se descobriu
> conferindo.

### Guarda que depende de um arquivo opcional é guarda que falta na hora

A conferência do setup fazia duas perguntas e amarrava as duas ao
`_manifesto.txt`:

| pergunta | precisa do manifesto? |
|---|---|
| a cópia Drive → VM trouxe tudo? | **não** — é comparar duas pastas |
| o Drive está atrás do repositório? | sim, só ele sabe |

Sem o manifesto ela imprimia `⚠️ sem _manifesto.txt` e seguia **sem conferir
nada**. Foi exatamente assim que um `✅ 13 modules copied` passou com visto
verde num Drive que tinha 31 — no dia em que o manifesto ainda não existia,
porque o sincronizador que o grava não tinha chegado a rodar de verdade.

Comparar 13 com 31 nunca dependeu de manifesto. As duas perguntas agora são
independentes: a primeira sempre roda (e se recopia sozinha, que é o conserto
do mount preguiçoso); a segunda avisa que não pode responder.

> Guarda opcional falta justamente no cenário ruim, porque o que a desliga
> costuma ser a mesma bagunça que ela existia pra pegar.

### `sys.modules` não sabe que o arquivo mudou

Copiar um `.py` novo por cima não desfaz um `import` já feito: o Python guarda
o módulo em `sys.modules` e reaproveita. Numa sessão longa do Colab, o notebook
roda com o `config.py` de ontem mesmo depois de um sync perfeito.

O sintoma aparece longe da causa. Aqui foi um `nome_srt_whisper()` devolvendo
`40_Matt_02_edge_pt.srt` — o nome antigo, aposentado há tempos — enquanto o
arquivo no Drive já dizia `_whisper_`. Nada falha; só sai errado.

O setup agora descarrega de `sys.modules` tudo que veio de `/content/pipeline`
depois de copiar, o que equivale a reiniciar o runtime sem perder o resto da
sessão.

### A aba do Colab é uma cópia, e cópia envelhece

O sincronizador atualizou a si mesmo numa rodada. Nas rodadas seguintes ele
disse `♻️ 0 · ✅ Drive idêntico ao repositório, byte a byte` -- e estava certo,
o Drive estava mesmo em dia. Só que o que rodou continuou sendo o código de
ontem: o Colab lê o `.ipynb` quando você **abre a aba** e guarda as células na
memória; ele não relê o arquivo a cada execução.

Resultado: o `_manifesto.txt` não era escrito, e nada avisava. O aviso de
auto-atualização que existia só dispara **na rodada em que a cópia acontece** —
quem roda depois não recebe aviso nenhum. Alarme que toca uma vez e cala é
quase pior que alarme nenhum, porque o problema continua e você já acha que
passou.

Pior ainda, o silêncio tem um lado destrutivo: se o Colab autossalvar a aba
velha, ele grava o notebook antigo por cima do novo no Drive, desfazendo o
sync sem uma linha de log.

A checagem agora roda na Configuração, toda vez: o texto da célula que está
executando tem que ser **igual a alguma célula** do `.ipynb` que está no Drive.
Não precisa de sentinela nem de número de versão pra manter.

> A primeira versão dessa checagem procurava o texto *dentro* do arquivo
> inteiro, e passava exatamente no caso que ela existe pra pegar: quando a
> versão nova só **acrescenta** linhas no fim de uma célula, a versão velha é
> um prefixo dela — e prefixo continua sendo substring. Só apareceu porque o
> teste simulou a aba velha em vez de conferir a atual. Teste que só exercita
> o caso bom não é teste, é confirmação.

### `_manifesto.txt` — contar sem ter contra o que comparar não é conferir

O setup de todo notebook imprimia `✅ 13 modules copied` — **com visto
verde**, faltando 18 dos 31. O notebook seguia e quebrava depois num `import`,
longe da causa.

E o diagnóstico óbvio estava errado: o Drive tinha os 31, conferidos byte a
byte pelo `repositorio-sincronizar`. Quem trouxe 13 foi o `copytree` do setup
— **o Drive montado do Colab popula a listagem da pasta com atraso**, e uma
cópia logo depois do `mount` às vezes enxerga só parte dos arquivos.

Por isso a conferência é de três pontas, e não de duas:

| Ponta | O que é |
|---|---|
| manifesto | o que o repositório tem (gravado pelo sincronizador) |
| Drive | o que chegou lá |
| VM | o que a cópia desta sessão trouxe |

A causa muda o conserto, então a mensagem muda junto:

- **falta no Drive** → rode o `repositorio-sincronizar`
- **está no Drive, não copiou** → o mount estava acordando: recopia sozinho os
  que faltaram, e só para se ainda assim não vier

> Uma mensagem certa sobre a causa errada custa o mesmo que nenhuma mensagem.
> A primeira versão desta conferência mandava sincronizar um Drive que já
> estava sincronizado.

**E o validador de sintaxe tinha um buraco no lugar exato do risco.** A edição
em lote pôs o bloco sem indentação dentro de um `if`, em 20 notebooks — e o
teste que eu rodava **pulava** justamente as células de setup, porque elas têm
`!pip`/`!apt`, que não são Python. Agora `nomenclatura.celulas_que_nao_compilam()`
troca essas linhas por `pass` e compila o resto; entrou no relatório junto com
os outros três defeitos.

> Pular a célula porque uma linha não é Python é trocar uma dificuldade por
> uma cegueira — e a cegueira ficou exatamente onde as edições acontecem.

### `modulos/audio_narracao.py` — onde procurar a narração, num lugar só

A busca pelo áudio existia em **um** lugar (`video_pipeline.gerar_audio`) e os
outros **quatro** consumidores olhavam só a pasta do vídeo. Resultado: o
`caption-single-generate` parou com *"Áudio não encontrado — rode um dos
notebooks video-base-*.ipynb primeiro"* num capítulo cujo áudio estava no
Drive o tempo todo, dois diretórios ao lado. E a mensagem mandava repetir um
passo que já tinha sido feito.

> Regra repetida é regra que vai divergir. **Regra em um lugar e quatro cópias
> antigas é pior** — a versão certa existe, e mesmo assim não é usada.

Os cinco consumidores agora chamam `audio_narracao.trazer(config, destino)`:

| Ordem | Onde | Nomes |
|---|---|---|
| 1 | disco da VM | `<nome>_audio.wav` |
| 2 | `videos/<nome>/` | `<nome>_audio.*`, `<nome>.*` |
| 3 | `assets/biblia_audio/` | idem |

Extensões: `.wav .mp3 .m4a .ogg .flac`; o que não for wav é convertido.
`erro_nao_achei()` lista as pastas de verdade e as três saídas, em vez de
apontar um notebook só.

### De onde vem a narração (e por que ela não é sobrescrita)

`gerar_audio()` procura, **nesta ordem**, antes de cogitar gerar:

| # | Onde | Nomes aceitos | Origem típica |
|---|---|---|---|
| 1 | `videos/<nome>/` | `<nome>_audio.*`, `<nome>.*` | gravação própria, ou o capítulo que você subiu à mão |
| 2 | `assets/biblia_audio/` | `<nome>_audio.*`, `<nome>.*` | o estoque do `biblia-audio-baixar` |
| 3 | — | — | Edge TTS, a partir de `TEXTO_ORACAO` |

Extensões: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`. O que não for `.wav` é
convertido (`ffmpeg_utils.converter_para_wav`) — o pipeline inteiro espera
`<nome>_audio.wav`, e gravar um mp3 com nome de wav é uma dívida que vence
longe de onde foi contraída.

Vindo do **estoque**, o áudio é subido pra `videos/<nome>/` no fim: é lá que
as fases seguintes (clipes, mescla) o procuram. Vindo da **pasta do vídeo**,
nada é subido — subir seria reescrever por cima do original.

> ⚠️ **O defeito que isto conserta.** A checagem antiga olhava só o disco da
> VM do Colab, que numa sessão nova está sempre vazio. Resultado: o Edge TTS
> gerava e subia pra `pasta_assets_audio` — que é alias de `pasta_oracao`,
> com o mesmo nome de arquivo. A narração sintética **sobrescrevia no Drive**
> a gravação humana. E em silêncio: o vídeo saía pronto, só com a voz errada.
> A docstring já prometia "nunca sobrescreve um áudio já presente" — só que
> "presente" significava presente *na VM*, não no Drive.

Duas consequências práticas: o aviso de `texto_hash` divergente agora só vale
pra áudio que o Edge TTS gerou (narração humana não tem hash de texto —
comparar disparava alarme falso no caso normal), e uma falha do Edge TTS
depois de 3 tentativas volta como `PipelineError` de verdade. Antes ela era
levantada dentro de uma `threading.Thread` e morria com ela: o `join()`
voltava como se tivesse dado certo, e o erro reaparecia como um
`FileNotFoundError` três linhas abaixo, apontando pro lugar errado.

### Classificação morfológica / relatório

| Propriedade | Padrão gerado |
|---|---|
| `nome_classificacao(lang)` / `nome_classificacao_basico(lang)` | `<nome>_classificacao_<lang>.json` / `..._basico_<lang>.json` |
| `nome_relatorio` | `<nome>_relatorio.csv` |
| `nome_prompt_revisao` / `nome_prompt_revisao_basico` | `prompt_revisao.md` / `prompt_revisao_basico.md` (genéricos, não prefixados) |

## 7. Pastas do Drive

Raiz fixa: `PASTA_DRIVE_RAIZ` (`"narrated_video"`, nunca muda).

| Propriedade | Caminho | Observação |
|---|---|---|
| `pasta_base_drive` | `/content/drive/MyDrive/<raiz>` | |
| `pasta_assets_clipes` | `.../assets/clipes` | Clipes Pixabay reutilizáveis entre vídeos. |
| `pasta_assets_logo` | `.../assets/marca` | Pasta real chama `marca`, não `logo`. |
| `pasta_assets_musica` | `.../assets/trilha` | Pasta real chama `trilha`, não `musica`. |
| `pasta_oracao` | `.../videos/<NOME_ORACAO>` | Tudo do vídeo específico. |
| `pasta_correcoes` | `.../videos/<nome>/<nome>_correcoes` | JSONs revisados manualmente. |
| `pasta_drive_brutos` | `.../videos/<nome>/<nome>_brutos` | Backup automático dos JSONs brutos do Groq. |
| `pasta_assets_cache` | `.../videos/<nome>/<nome>_cache` | |
| `pasta_revisao` | `.../pipeline/revisao` | Prompts genéricos de revisão, compartilhados. |

`pasta_assets_videos`/`pasta_assets_audio`/`pasta_assets_legendas` são aliases
legados que apontam todos pra `pasta_oracao`.

## 8. Outros parâmetros configuráveis relevantes

| Campo | Padrão | Descrição |
|---|---|---|
| `MODO_CLIPE` | `"video"` | `"video"` ou `"imagem"` — dita `ID_PLANILHA_IMAGENS_DRIVE` obrigatório e sufixo `_img`. |
| `GROQ_MODEL` | `"llama-3.3-70b-versatile"` | Modelo usado pro match/classificação via Groq. |
| `DURACAO_CLIPE` | `5` (s) | Duração de cada clipe no modo padrão (não verse-matched). |
| `DURACAO_MINIMA_SEGMENTO_VERSICULO` | `2.0` (s) | Versículos mais curtos que isso são fundidos com o vizinho. |
| `LARGURA_CLIPE`/`ALTURA_CLIPE`/`FPS_CLIPE` | `1280×720@25` | Padronização de todo clipe antes de concatenar (evita corromper duração). |
| `ABREVIACOES_LIVRO` | dict por idioma | Overlay de referência (livro:versículo). |
| `FONTE_TEXTO_IDIOMA` | `{}` | Por idioma-alvo, `"yt"` ou `"whisper"` como fonte bruta de texto. |
| `CODIGO_LEGENDA_YOUTUBE` | `{}` | Override de código de idioma no YouTube (ex: `zh` → `zh-Hans`). |
| `FORMATO_MANUAL_AUDIO` | `{}` | Override manual do ID de formato yt-dlp por idioma. |
| `IDIOMAS_CJK` | `{"ko", "zh"}` | Idiomas que precisam de fonte CJK explícita (Arial não cobre Hangul/Han). |
| `FONTE_CJK_POR_IDIOMA` | `{"zh": "Noto Sans CJK SC"}` | Variante regional por idioma; quem não estiver aqui cai em `FONTE_CJK`. Ver `config.fonte_cjk(lang)`. |
| `SUFIXO_VARIANTE_IDIOMAS` | `""` | Sufixo nos finais nível 2 e 3, pra variantes do conjunto de idiomas conviverem (ver seção 8b). |

## 8b. Variante de 6 idiomas — chinês (`zh`)

Fluxo paralelo ao de 5 idiomas, em **notebooks próprios**; os de 5 idiomas
continuam intactos e as duas variantes convivem na mesma pasta do vídeo.

### Convenção de código

| Onde | Código | Por quê |
|---|---|---|
| Interno (posição, cor, fonte, arquivos) | `zh` | Código canônico do projeto. |
| YouTube (`--sub-langs`) | `zh-Hans` | Via `CODIGO_LEGENDA_YOUTUBE`. Use `zh-Hant` se quiser tradicional. |
| Stanza (modelo) | `zh-hans` | Nome do modelo. Via `IDIOMAS_STANZA` no notebook. |

**Simplificado (`Hans`), não tradicional** — é o usado na China continental,
Singapura e Malásia (~1,1 bi de falantes) contra Taiwan/HK/Macau (~40 mi).

### Notebooks

| Novo | Copiado de | Mudança |
|---|---|---|
| `caption-multilang-zh-sources-gather.ipynb` | `caption-multilang-sources-gather` | `zh` em `IDIOMAS_ALVO` (o `CODIGO_LEGENDA_YOUTUBE` já vinha pronto) |
| `caption-multilang-zh-generate.ipynb` | `caption-multilang-generate` | `zh` em `IDIOMAS_ALVO` + `FONTE_TEXTO_IDIOMA` |
| `caption-multilang-zh-burn.ipynb` | `caption-multilang-burn` | `zh` em `IDIOMAS_ALVO`, `太` em `ABREVIACOES_LIVRO`, `SUFIXO_VARIANTE_IDIOMAS="_zh"` |
| `caption-multicolor-zh-generate.ipynb` | `caption-multicolor-generate` | `zh: zh-hans` em `IDIOMAS_STANZA`, `.ass` próprio, sufixo `_zh` |
| *(nenhum)* | `caption-multicolor-burn` | **reaproveitado como está** — é agnóstico de idioma (só recebe um `.ass` e queima) |

Saídas: `<nome>_final_idiomas_zh.mp4` e `<nome>_final_multicolor_zh.mp4` — não
sobrescrevem as de 5 idiomas.

### Cores: o chinês não precisou de nenhuma categoria nova

Reutiliza as 14 genéricas + `particula`. As 6 categorias exclusivas do coreano
(terminações/sufixo) não se aplicam: **coreano é aglutinante** (sufixos
transformam a palavra), **chinês é isolante** (palavras são blocos
independentes, modificadas por outras palavras, não por sufixos).

O único mapeamento próprio do chinês é `PART` → `particula` — `PART` é a classe
mais frequente da língua (o 的 sozinho é o caractere mais comum do chinês) e
sem isso cairia no fallback `adverbio`.

| | Cor | Posição Y | Fonte |
|---|---|---|---|
| `zh` | `#800080` 🟣 roxo | 500 (6ª faixa) | Noto Sans CJK **SC** |

## 8c. Bíblia em áudio (WEB / David Williams)

A narração é a **World English Bible** lida por David Williams (domínio
público, [AudioTreasure](https://audiotreasure.com/webindex.htm)) — **não é
King James**, apesar do nome parecido. O texto pareado é o
[`eng-web-c`](https://ebible.org/eng-web-c/) (WEB Classic); a própria página da
narração distribui o `WEBTEXT.pdf` como "read along".

Isso importa: o `alinhar_versiculos()` (`srt_utils.py`) casa o texto de
referência contra a transcrição do Whisper pra derivar o tempo de cada
versículo. Texto de outra tradução degrada o alinhamento em silêncio.

### `modulos/biblia_livros.py` — tabela canônica dos 66 livros

Fonte única do nome de capítulo. `livro.nome_projeto(cap)` devolve o padrão do
projeto (`40_Matt_02`, sigla OSIS — a mesma que já vinha sendo usada à mão) e
`livro.stem_audio(cap)` devolve o nome na fonte.

**Os nomes do AudioTreasure são irregulares** — e, pior, *imprevisíveis*. A
primeira versão montou `modelo_audio` a partir do índice do SITE, e o zip usa
outros nomes. O download saiu com **120 capítulos "faltando" que estavam todos
lá dentro**:

| a tabela esperava | o zip tinha |
|---|---|
| `20_proverbs_01` | `20_prov_01` |
| `25_lamentations01` | `25_lam1` |
| `22_song_of_soloman_01` | `22_song_of_solomon_01` |

Mateus, 1-2 Coríntios, Gálatas, 1-2 Tessalonicenses, Filemom, 2-3 João,
Judas e Obadias, todos assim.

> **Prever o nome exato de um arquivo alheio é uma aposta que se perde em
> silêncio.** O que a fonte garante não é o nome — é a numeração canônica, que
> está no começo e no fim de todo arquivo.

`chave_audio(stem)` extrai `(livro, capítulo)` de qualquer forma que a fonte
use, e é por essa chave que arquivo e capítulo se casam.
`indexar_por_chave()` devolve o índice, os arquivos que não viraram chave, e
as **colisões** — dois arquivos disputando o mesmo capítulo não são resolvidos
em silêncio, porque áudio trocado não dá erro: sai um vídeo lendo outro
capítulo.

`modelo_audio` continua na tabela, rebaixado: só alimenta a mensagem
*"esperava algo como X"* quando um capítulo falta de verdade.

Os nomes que a fonte usa, pra referência:

| Livro | Na fonte | Irregularidade |
|---|---|---|
| Gênesis | `01_Genesis_01` | (o formato da maioria) |
| Mateus | `40_Matthew01` | sem underscore antes do número |
| Lamentações | `25_Lamentations03` | sem underscore |
| Salmos | `19_Psalm_001` | número com 3 dígitos |
| Cânticos | `22_Song_of_Soloman_01` | "Soloman" escrito assim na fonte |

O padding do capítulo segue a largura do próprio livro (mínimo 2): Mateus fica
`40_Matt_02` como sempre foi, e Salmos fica `19_Ps_001`..`19_Ps_150`, que
ordena certo numa listagem de pasta.

### `notebooks/biblia-audio-baixar.ipynb`

Baixa os zips do AudioTreasure (NT ~300 MB + AT ~900 MB), descompacta e salva
em `assets/biblia_audio/` um mp3 por capítulo, já renomeado. Roda uma vez;
capítulo que já está no Drive é pulado, então é seguro rodar de novo depois de
uma queda de sessão. O download sai da internet do Colab, não da máquina local.

Fica em `assets/` por ser material compartilhado entre todos os vídeos — mesma
lógica de `assets/trilha` e `assets/marca`.

A conferência final cruza duas listas: **faltando** (capítulo do cânone que o
zip não trouxe) e **sobrando** (mp3 que nenhum capítulo reclamou). Livro que
aparece nas duas = `modelo_audio` errado na tabela, não arquivo ausente.

> ⚠️ **Livro de um capítulo só não tem número no nome** — `65_jude.mp3`,
> `31_obadiah.mp3`, `57_philemon.mp3`, `63_2john.mp3`, `64_3john.mp3`. O
> capítulo vem de saber que o livro tem um só, nunca do nome: fosse do nome,
> `63_2john` viraria "2 João capítulo 2", que não existe. Pra qualquer outro
> livro, nome sem número é recusado — `40_matthew` não diz qual dos 28 é, e
> chutar o 1 daria um vídeo lendo o capítulo errado sem erro nenhum.

> ✅ **Zacarias 14 EXISTE no zip.** A versão anterior deste documento dizia
> que não, com base no índice do SITE, que lista 13. O zip trouxe os 14 — a
> execução completa fechou em 1189 de 1189. Mais um caso do mesmo engano:
> **o índice da página não é o conteúdo do arquivo**, e foi a página que
> também gerou a tabela de nomes errada.

## 8d. Texto da Bíblia (WEB) — `dados_lexico/web-biblia.json`

### `notebooks/biblia-texto-baixar.ipynb`

Baixa o USFM da WEB do ebible.org, converte pra um JSON único em
`dados_lexico/web-biblia.json` e **confere contra o `40_Matt_02` que já
existe** antes de salvar. Depois disso, o `roteiro_versiculos.txt` de qualquer
capítulo sai de uma chamada de função — acabou a consulta capítulo a capítulo
no site.

**Por que USFM e não o PDF.** O `WEBTEXT.pdf` da página da narração é de duas
colunas: extrator de texto lê atravessando e embaralha as palavras (testado —
Gênesis 1:1 sai com as duas colunas intercaladas). O USFM marca parágrafo
(`\p`) e poesia (`\q1`) explicitamente, que é exatamente a estrutura que o
`roteiro_versiculos.txt` já tem. O PDF serve pra ler, não pra virar dado.

### A prova de três pontas (29/ago)

O texto da narração foi confirmado por três fontes independentes que **batem
entre si palavra por palavra**:

| Comparação | Similaridade |
|---|---|
| `web-biblia.json` (baixado do ebible) × roteiro do projeto | **1,0000** |
| **PDF oficial do AudioTreasure** × roteiro do projeto | **1,0000** |
| áudio do David Williams (Whisper `small`) × texto | 0,9625 |

O PDF é o que o próprio site do áudio publica "pra acompanhar a narração" — é
a fonte mais autoritativa possível pra essa pergunta, e não sobrou dúvida.

Então **0,96 no áudio é o piso do bom**, não um defeito: é o custo de
transcrever fala. Está em `biblia-audio-conferir.ipynb` como calibração.

> ⚠️ **Whisper "corrige" texto bíblico pro fraseado da King James.** No Mateus
> 2 ele transcreveu `King Herod` como "Herod the king", `for this is written`
> como "for thus it is written" e `shall come a governor` como "come forth a
> governor". Reordenar palavra e inserir palavra **parecem** divergência real —
> o instinto "ASR não inventaria isso" está errado em texto conhecido. Foi o
> PDF que desfez a suspeita.

### Ester e Daniel vêm na forma grega

A WEB do ebible.org publica os dois com os acréscimos deuterocanônicos, sob os
códigos USFM **`ESG`** e **`DAG`** — e **não** publica `EST`/`DAN` separados.
Sem apelido, os dois livros somem do `web-biblia.json` (aconteceu em 29/ago).
`biblia_livros.ALIASES_USFM` resolve.

| | Traz a mais | Risco |
|---|---|---|
| `DAG` → Daniel | Susana (13) e Bel (14) | **nenhum** — os capítulos 1–12 mantêm a numeração, e os extras nunca são pedidos |
| `ESG` → Ester | adições gregas A–F | **real** — dependendo de como a edição as encaixa, a numeração de **versículo** pode deslocar |

Versículo deslocado desalinha contra o áudio **em silêncio**, que é o defeito
que este notebook inteiro existe pra evitar. Por isso o notebook avisa toda vez
que usa um apelido, com a contagem de capítulos. **Antes de fazer um vídeo de
Ester, confira o capítulo contra a fonte.**

> A célula de parsear lista **quais** arquivos ficaram de fora, com o código
> USFM de cada um. Antes ela só dizia "9 arquivos fora do cânone (normal)" — e
> quando Ester e Daniel sumiram, a informação que resolvia o caso tinha sido
> resumida embora. Contagem sem os nomes não diagnostica nada.

**Onde mora.** `dados_lexico/`, junto de `eventos-biblicos.json` e
`titulos-biblicos.json` — dado de referência **imutável**, versionado, lido por
módulo. Não vai pra planilha: planilha é pra estado que muda e que você edita à
mão, e texto bíblico não é nem uma coisa nem outra. Numa aba editável, um
`ordenar coluna` sem querer corromperia o alinhamento em silêncio.

### O limiar da conferência é calibrado, não chutado

**Duas traduções em inglês diferentes batem ~0,83 de similaridade** — medido,
WEB contra KJV no mesmo trecho de Mateus 2. Elas compartilham muita palavra, e
por isso um limiar frouxo (tipo 0,80) deixaria passar a tradução errada. O
notebook usa **0,97**.

Importa porque o `alinhar_versiculos()` casa este texto contra a transcrição do
Whisper pra derivar o tempo de cada versículo: texto de outra edição degrada o
alinhamento **sem erro nenhum** — aparece só no vídeo montado.

### `modulos/biblia_texto.py`

| Função | O que faz |
|---|---|
| `parsear_usfm(conteudo)` | `(livro, {capítulo: [Versiculo]})`. Tira nota de rodapé, referência cruzada, título e cabeçalho; preserva palavras de Jesus (`\wj`) e `\add`; junta versículo que continua na linha seguinte. |
| `gerar_roteiro(versiculos)` | Monta o texto no formato do `roteiro_versiculos.txt`, com número como token isolado e quebra na poesia. |
| `comparar(a, b)` | Compara palavra a palavra ignorando pontuação, acento, aspas curvas e número de versículo. Devolve similaridade e a lista de divergências com contexto. |
| `carregar_biblia(caminho)` | Lê o `web-biblia.json`. Erro nomeando o notebook quando o arquivo ainda não existe — "KeyError: 'livros'" não diria a ninguém que o que falta é rodar um notebook. |
| `versiculos_de(biblia, sigla, cap)` | Os versículos de um capítulo, de volta ao formato `Versiculo`. |
| `roteiro_do_capitulo(nome, caminho)` | `"40_Matt_02"` → o roteiro pronto. Fecha o ciclo com `biblia_livros.de_nome_projeto()`, e usa o **mesmo** `gerar_roteiro()` do notebook de download — então não existem dois formatos concorrentes. |

### O roteiro deixou de ser algo que você fornece

`caption_pipeline.resolver_texto_versiculos(config, texto_colado)` — usado pelos
**três** notebooks de burn (single, multilang, multilang-zh). Três fontes, da
mais específica pra mais geral:

| # | Fonte | Por que nessa ordem |
|---|---|---|
| 1 | `TEXTO_VERSICULOS` na Configuração | o que você escreveu ganha de tudo |
| 2 | `<nome>_roteiro_versiculos.txt` na pasta do vídeo | pode ter sido **editado** (versículo mesclado, palavra que a dublagem falou diferente do escrito) — e edição tem que ganhar da Bíblia crua |
| 3 | `dados_lexico/web-biblia.json` | a Bíblia inteira: qualquer um dos 1.189 capítulos, sem você colar nada |

Ao cair na fonte 3, grava o resultado como o roteiro do vídeo: da próxima vez
sai pela fonte 2, e fica um arquivo pra você corrigir se algo estiver torto.

Vive num módulo, e não dentro de um notebook, porque os três precisam
exatamente disto — e a versão copiada em três lugares é a que diverge no
primeiro conserto.

> ⚠️ **Só o texto por versículo vem daqui.** A narração continua saindo do
> `TEXTO_ORACAO` do notebook de vídeo base (é ele que o Edge TTS lê), e os
> outros idiomas continuam vindo da dublagem automática do YouTube. Isto
> resolve o overlay "Matt 2:4", não o roteiro falado.

Testado com USFM sintético cobrindo as armadilhas estruturais (nota de rodapé,
`\w` com Strong, dois `\v` na mesma linha, versículo continuando na linha de
baixo, poesia, título no meio do capítulo) e com round-trip pelo
`extrair_marcadores_versiculo()` de `srt_utils.py`, que é quem consome.

> ⚠️ **Limite conhecido, herdado do formato:** `extrair_marcadores_versiculo()`
> lê qualquer token de 1–3 dígitos como número de versículo. Um numeral solto
> dentro do texto poderia confundir — na prática a WEB escreve números por
> extenso, e a função só registra a primeira ocorrência de cada número, então o
> risco é baixo. Fica registrado porque não é óbvio olhando o código.

## 8e. Portão de qualidade — `notebooks/portao-qualidade.ipynb`

Confere o vídeo **antes de publicar**. Existe por causa de uma família de bugs
que o pipeline tem e que **não levanta exceção nenhuma** — aparece só no vídeo
pronto. Dois já aconteceram de verdade neste projeto: idioma novo caindo no
cinza de fallback, e legenda virando quadradinho por fonte sem os glifos.

| Camada | Confere | Custo |
|---|---|---|
| `verificar_ass()` — antes de queimar | cor fora da paleta, fonte sem glifo, área segura, tempo invertido, sobreposição na mesma faixa, bloco vazio | milissegundos |
| `verificar_video()` — antes de publicar | áudio estourado/baixo, faixa de áudio ausente, duração | ~1 min (`volumedetect` lê o arquivo todo) |

### A severidade vem do resultado, não da substituição

O projeto declara `Arial` no estilo padrão, e **Linux/Colab não tem Arial**: o
fontconfig troca por Liberation Sans, metricamente compatível, que cobre latim
inteiro. Isso é **aviso**, não erro.

Se fosse erro, o portão reprovaria todo vídeo do projeto e você aprenderia a
ignorá-lo — o que é pior do que não ter portão. O que é **erro sempre** é
glifo faltando, porque é o que vira quadradinho na tela.

> ⚠️ Declarar `Noto Sans CJK SC` no `.ass` **não basta**: se a fonte não
> estiver instalada na máquina que queima, o fontconfig cai em outra e o
> chinês/coreano sai em quadradinho. O notebook instala `fonts-noto-cjk` no
> Setup, e o portão pega o caso se faltar.

### O portão já achou um bug de verdade

Na primeira varredura ele encontrou algo que estava no código desde antes:
`gerar_ass_simples()` (a legenda única, usada pelo `caption-single-burn`)
**nunca aplicava a tag de fonte CJK**. Ela não recebia o idioma, e o estilo
padrão desse `.ass` é Arial — sem Hangul e sem Han. Um vídeo com
`IDIOMA_MESTRE` coreano ou chinês sairia com a legenda inteira em
quadradinhos, sem erro nenhum no console.

Eram dois problemas independentes, os dois corrigidos:

| | Era | Ficou |
|---|---|---|
| `gerar_ass_simples()` | sem parâmetro `lang`, sem `\fn` | `lang=""` opcional; emite `\fn` só nos CJK |
| `caption-single-burn` | `apt-get install ffmpeg` | `... ffmpeg fonts-noto-cjk` |

O `_adicionar_linha_simples()`, no mesmo arquivo, já fazia certo — o
`gerar_ass_simples()` é que tinha uma cópia simplificada sem a tag.

Verificado que idioma latino sai **byte a byte idêntico** ao de antes do
parâmetro existir (sha256 igual sem `lang`, e com `pt`, `en` e `fr`), e que
`ko`/`zh` passam a receber `\fnNoto Sans CJK KR`/`SC`. Com a fonte instalada,
o próprio portão vira o juiz: o `.ass` de antes reprova apontando os
codepoints, o de depois aprova.

### Testes

- Paleta: rodado contra o `legendas_40_Matt_02_v2.ass` real, anterior à
  repadronização — detectou **37 cores fora das 21**, como esperado.
- Fonte: latim com Arial passa (1 aviso); chinês e coreano com fonte sem
  cobertura reprovam apontando os codepoints exatos.
- Tempo invertido, área segura, bloco vazio: cada um em `.ass` sintético.
- Vídeo: mp4 sintéticos com áudio normal, estourado (+0,0 dB), sem faixa de
  áudio e com duração divergente — os cinco casos se comportam certo.

## 8f. Cache de tempos por capítulo — `modulos/tempos_cache.py`

O áudio de um capítulo nunca muda, então o tempo dos versículos dele também
não. Transcrever com Whisper e alinhar custa minutos; reaproveitar custa
milissegundos. **Uma compilação que usa Mateus 2 paga uma vez** — a próxima
que repetir o capítulo não paga nada.

Um arquivo por capítulo em `assets/biblia_tempos/`, espelhando o
`assets/biblia_audio/`. Não é um JSON só porque o cache **cresce aos poucos**:
arquivo por capítulo grava só o que mudou, dá pra abrir e conferir um capítulo
isolado, e duas execuções em paralelo não brigam pelo mesmo arquivo.

### A invalidação é o ponto todo

Tempo de versículo é dado **derivado** de duas entradas: o áudio e o texto de
referência. Se qualquer uma mudar, o tempo guardado está errado — e errado em
silêncio, porque um número continua parecendo um número válido.

Por isso o cache guarda a impressão digital das entradas e **erra pro lado do
miss**: entrada diferente = não achou, recalcula. Nunca devolve tempo velho
achando que serve.

| Mudou | Resultado |
|---|---|
| O arquivo de áudio | miss — *"o áudio do capítulo é outro arquivo"* |
| O texto de referência | miss — *"o texto de referência mudou"* |
| O modelo do Whisper | miss — *"transcrito com 'base', agora pediram 'small'"* |
| Só a quebra de linha do texto | **hit** — o hash normaliza espaço em branco, e o `alinhar_versiculos()` colapsa quebra de linha de qualquer jeito |

O miss vem com motivo em texto, pra ser diagnosticável em vez de misterioso.

### `intervalo(versiculo)`

Devolve `(início_ms, fim_ms)`, onde o fim é o **início do próximo versículo** —
é assim que o corte fica sem buraco nem sobreposição entre versículos
consecutivos. O último termina no fim do áudio.

### `faltando(pasta, capitulos)`

Diz de uma vez quais capítulos de uma seleção ainda precisam de transcrição —
em vez de você descobrir um por um no meio do processo. É o que responde
"quais áudios vou precisar" no fluxo da compilação.

## 8g. Nome de uma compilação

O tema é **editorial e livre** — muda a cada vídeo, o código não tem como
adivinhar. Vem da célula de Configuração, como qualquer outra escolha sua:

```python
TEMA = "Salmos Esperança"     # -> comp_salmos_esperanca
```

`compilacao_pipeline.nome_compilacao()` só deixa o texto utilizável como nome
de pasta e de arquivo. Acento, cedilha, espaço e pontuação atravessam Drive,
shell e linha de comando do ffmpeg, e cada um quebra de um jeito diferente e
chato de diagnosticar.

Ele é **estável**: `"Salmos Esperança"`, `"salmos  esperanca"`,
`"SALMOS-ESPERANÇA"` e `"Salmos, Esperança!"` dão todos o mesmo
`comp_salmos_esperanca` — reescrever o tema com outra pontuação não cria uma
pasta nova por engano.

### Por que o prefixo `comp_`

Separa compilação de capítulo. Sem ele, `salmos_esperanca` e `19_Ps_023` moram
juntos em `videos/` sem nada dizendo o que é o quê — e uma compilação batizada
por acaso com o nome de um capítulo **sobrescreveria a pasta dele**.

`conflita_com_capitulo()` confere contra os 1189 capítulos, **sem diferenciar
maiúscula**: `40_matt_02` e `40_Matt_02` são a mesma pasta pra qualquer efeito
prático (Drive e macOS nem distinguem). Comparar sensível deixaria passar
exatamente a colisão que a função existe pra pegar.

## 8h. Compilação — `notebooks/compilacao-montar.ipynb`

Versículos sortidos da Bíblia inteira, atravessando livros. Você escreve o
tema e a seleção; o notebook faz o resto.

```python
TEMA = "Salmos Esperança"
SELECAO = [
    ("Ps",  23, "1-6"),
    ("Ps",  42, "5,11"),
    ("Isa", 40, "28-31"),
    ("Rom",  8, "38-39"),
]
```

**A ordem da seleção é a ordem do vídeo** — pode pular entre livros, repetir
capítulo e sair de ordem.

| Passo | O quê |
|---|---|
| 1 | extrai o texto dos versículos do `web-biblia.json` |
| 2 | diz **quais capítulos ainda precisam de tempo** |
| 3 | transcreve e alinha **só os que faltam**, gravando no cache |
| 4 | corta, concatena, gera `.wav` + `.srt` + manifesto |

O passo 3 é o caro, e é o que o cache existe pra pagar uma vez por capítulo.

### Validação vem antes do trabalho

`parsear_selecao()` confere livro e capítulo contra a tabela canônica, e
`compilar_selecao()` carrega o cache de **todos** os capítulos antes de cortar
o primeiro segmento. Livro inexistente, versículo fora do capítulo ou tempo
faltando quebram na leitura da config — não vinte minutos depois, no meio do
corte, com arquivos temporários soltos.

### Por que o corte decodifica em vez de copiar

A fonte é **mp3**, e corte por cópia gruda na fronteira do frame (~26 ms): a
emenda entre versículos sai torta. Além disso, o concat por cópia exige mesmo
codec, taxa e canais em todos os segmentos — e a seleção atravessa arquivos
diferentes. `_cortar_segmento()` normaliza (44,1 kHz, mono, PCM), que é o que
faz a junção funcionar entre capítulos.

O `-ss`/`-t` vem **depois** do `-i`: seek exato, à custa de ler até o ponto.
Capítulo tem poucos minutos, então o custo é baixo e a precisão é o que mantém
o versículo inteiro dentro do corte.

### O manifesto

Pra cada trecho do compilado: de qual capítulo e versículo veio, em que
milissegundo do original começava, e onde caiu no compilado. É por ele que a
montagem de vídeo acha a mídia certa de cada pedaço.

### Testes

Ensaio completo com áudio e `web-biblia.json` sintéticos, atravessando dois
livros com seleção não sequencial: nome, parse, relatório do cache,
alinhamento (simulando saída do Whisper com pontuação e caixa diferentes do
texto de referência — 4/4 versículos alinhados), corte, concat, duração exata,
ordem preservada e SRT com o texto certo. E a segunda compilação da mesma
seleção não recalcula nada.

Também testado: falha limpa quando falta tempo no cache (apontando qual
capítulo), e os três erros de config (capítulo fora do livro, sigla
inexistente, intervalo invertido).

## 9. Decisões adiadas

Coisas que a gente **decidiu não fazer agora**, com o gatilho anotado. Não são
pendências soltas: são escolhas, e o que muda é o momento.

### 9.1 Consolidar os seis `video-base-*` num só, com perfil

**Situação.** O nome `video-base-imagem-versiculo-trilhas-efeitos` codifica o
conjunto de funcionalidades no nome do arquivo. Isso não escala por aritmética:
cada feature nova dobra as combinações possíveis. Hoje são 6 notebooks pra 4
features; a próxima feature pede mais 6.

E os seis são cumulativos — o `-trilhas-efeitos` **já é superconjunto dos
outros cinco**, inclusive cobrindo imagem e vídeo sozinho, via `TIPO_FONTE`.

**O projeto já resolveu isso do lado certo.** As *saídas* nomeiam nível sem
explosão nenhuma:

```
_video_base.mp4 → _final.mp4 → _final_idiomas.mp4 → _final_multicolor.mp4
```

Níveis cumulativos e nomeados, não lista de features ligadas. Foram os
*notebooks* que não seguiram a disciplina que as *saídas* já seguem.

**Decisão quando chegar a hora.** Um `video-base.ipynb`, com o nível em
configuração:

```python
PERFIL = "completo"    # padrao | versiculo | trilhas | completo
TIPO_FONTE = "imagem"  # imagem | video
```

O perfil nomeado é o que impede a troca de ruim por pior: dez flags soltas
obrigariam a ler a configuração inteira pra saber o que vai sair. Com perfil,
você continua pensando em "quero o completo" — que é como já pensa hoje ao
escolher o arquivo.

**O ganho maior não é o nome curto, é a deriva.** Hoje uma correção no
`-trilhas-efeitos` não chega nos outros cinco. É o mesmo problema que fez o
chinês virar flag em vez de módulo duplicado, e as duas centrais saírem de um
gerador só.

**Por que não agora.** É refatoração de verdade, em seis notebooks que
funcionam, e há trabalho não rodado na fila — os notebooks de áudio, texto,
compilação e portão nunca viram Colab. Consolidar código testado com código não
testado é como se perde os dois.

**Gatilho.** Quando você for mexer nos `video-base` por outro motivo, ou quando
a sétima variante pedir pra nascer. Aí a consolidação se paga; antes disso é
arrumação.

**Custo aceito.** Você perde os seis links salvos no Colab e ganha um. Pra quem
navega por arquivo, é mudança de hábito.

### 9.2 `NOME_ORACAO` não guarda mais uma oração

O campo diz "oração", mas hoje guarda `40_Matt_02` (um capítulo) e em breve
`comp_salmos_esperanca` (uma compilação). É fóssil do escopo original. Quem
chegar novo lê e entende errado.

**Por que não agora.** Aparece na célula de configuração de quase todos os
notebooks — é refatoração, não renomeação. **Gatilho:** junto de alguma mudança
que já toque essas células.

### 9.3 Apagar o `compilar-versiculos-teste`

Não renomear: **apagar**. Ter dois notebooks de compilação confunde porque um
está obsoleto, não porque os nomes divergem. **Gatilho:** quando o
`compilacao-montar` rodar em produção.

### 9.4 Quando padronizar os 19 nomes: renomear no lugar, não fazer um V2

**Pergunta que apareceu:** vale deixar o pipeline atual como backup e produzir
uma versão V2 com todos os nomes já padronizados?

**Não** — e a evidência é do próprio projeto, não teórica.

`pipeline/notebooks.backup/` é o resultado de já terem feito exatamente isso
uma vez. Sobrou:

| | |
|---|---|
| 10 arquivos mortos | ninguém roda, e o `verificar_repo()` nem olha pra essa pasta |
| 14 referências quebradas no código vivo | módulos e notebooks apontando pros nomes que só existem no backup |

A cópia de segurança protegeu os arquivos antigos e não impediu nenhuma das
14, porque **renomear não quebra arquivo — quebra referência**. Um V2 não
resolve isso; dobra a superfície onde o nome pode divergir.

Dois custos que também não caem com um V2:

- **Os links do Colab salvos** (~19). Um V2 não salva um link; duplica quantos
  existem.
- **Nada no Drive muda** de qualquer jeito: os arquivos do Drive são nomeados
  a partir de `NOME_ORACAO`, nunca do nome do notebook. Renomear notebook não
  toca em vídeo, áudio nem legenda — o custo é bem menor do que parece.

**Como fazer, quando for a hora:**

1. `git tag nomes-v1` antes. É o backup de verdade: exato, grátis, e não vira
   pasta morta. (O `notebooks.backup/` já está no histórico desde o commit
   `26107aa` — é redundante hoje e pode ser apagado.)
2. Renomear com `git mv`, **num commit que só renomeia**. Preserva o blame, e
   é revisável de relance — o que um commit que renomeia *e* muda
   comportamento nunca é.
3. Rodar `python3 pipeline/modulos/nomenclatura.py` depois. É o
   `referencias_fantasma()` que fecha o buraco de 2024: ele lista arquivo e
   linha de cada citação ao nome velho.
4. Atualizar o `jornadas.py` junto — o `verificar_repo()` dele acusa
   `[fantasma]` pra jornada que cita notebook renomeado.

**Separado da 9.1.** Renomear é mecânico e verificável; consolidar os seis
`video-base-*` é design. Num commit só, uma coisa segura vira uma coisa que
ninguém consegue revisar.

## 9b. Lacunas conhecidas / pontos de atenção

- Os notebooks `video-base-video-padrao.ipynb` e `video-base-video-versiculo.ipynb`
  agora expõem `ID_PLANILHA_VIDEOS`/`NOME_COLUNA_STATUS_PLANILHA` na célula de
  Configuração (antes vinham só do default de `config.py`, sem aparecer editável
  — corrigido).
- Os nomes de aba de `evento_tags`/`titulo_tags`/`versiculo_tags`/`eventos_semeados`
  não são expostos como variáveis de notebook (só `NOME_ABA_VERSICULO_TAGS`
  aparece nos notebooks de trilhas) — os demais usam o default hardcoded nas
  funções `garantir_aba_*` de `match_pipeline.py`/`pixabay_seed_pipeline.py`.
  Só precisa mexer se um dia quiser renomear essas abas.
- `biblia_texto` é uma aba populada manualmente/externamente — não existe
  função no pipeline que a crie ou sincronize.
- Rename `edge`→`whisper` nos nomes de SRT (config.py, `caption_pipeline.py`,
  `language_captions_pipeline.py`, e os notebooks que usam
  `nome_srt_whisper(lang)`/`NOME_SRT_PT_WHISPER`) — feito. Vídeos já gerados
  antes disso (ex: `40_Matt_02`) mantêm os arquivos antigos no Drive com nome
  `_edge_` — ver aviso na seção 6.
- `nome_audio_mestre`/`nome_palavras_mestre`/`nome_legenda_mestre` formalizam
  os 3 "mestres" do vídeo (seção 6b) — só `nome_legenda_mestre` (segmentação)
  é de fato consumido/mesclado pelo pipeline; os outros 2 são "documentação
  configurável" — apontam pro arquivo certo, mas a mescla em si (quando
  existe) é sempre feita por você fora do pipeline.
- `nome_srt_versiculo` virou NUM SÓ IDIOMA (mestre) e `nome_srt_versiculo_multilingue`
  (novo) ficou com a combinação de todos os idiomas — antes as duas legendas
  de idioma único e multi-idioma geravam/liam o MESMO nome (`_versiculo.srt`)
  com conteúdo sempre multilíngue, o que não batia com o arquivo real do
  `40_Matt_02` (`40_Matt_02_versiculo_multilingue.srt`, já com o sufixo). Com
  a mudança, o nome real do Drive passou a corresponder ao novo
  `nome_srt_versiculo_multilingue` (usado por `language_captions_pipeline.py`)
  automaticamente — nenhuma ação manual no Drive foi necessária pra esse caso.
- `classificacao.py` (filtro Stanza→20 classes, contraparte do `classificacao_ko.py`)
  faltava no repositório — nunca tinha sido migrado do Drive pro GitHub, e
  `caption-multicolor-generate.ipynb` quebrava no import. Recuperado do Drive
  e adicionado em `pipeline/modulos/classificacao.py`.
- **`nome_ass(lang)` REMOVIDO** de `config.py` — não era usado em lugar
  nenhum do pipeline (nem legenda única, nem multi-idioma cor única, nem
  multicolor — as 3 variantes geram só 1 `.ass` por vídeo, cada uma com seu
  próprio nome fixo, nunca 1 arquivo por idioma). Ver tabela de `.ass` na
  seção 6 pros nomes reais.
- **Bug real corrigido: coreano caía em cinza na legenda multicolor.**
  `classificacao_ko.py` devolve classes finas (`particula_sujeito`,
  `verbo_passado`, `honorifico`, etc.) que nunca bateram com nenhuma chave
  de `cores.py` (só 20 chaves oficiais existem) — `cor_html()` caía no
  fallback cinza (`#808080`) pra tudo que não fosse `numeral`/`adverbio`/
  `interjeicao`/`conjuncao`/`pontuacao`. Ou seja, substantivo, pronome,
  verbo e partícula coreanos (a maior parte do texto) saíam cinza, não na
  cor pretendida. Corrigido com `cores.MAPA_CLASSES_FINAS` (traduz classe
  fina → 1 das 20 oficiais, usado por `cor_html()`/`cor_texto()`/
  `nome_cor_oficial()`) — a maioria das traduções já estava documentada
  como subclasse em `central-decisao-cores.html` (ex: "particula": sujeito/
  tópico/objeto/possessiva/locativa/direcional; "terminacao_final": neutra/
  imperativo — por isso `EF` agora separa `terminacao_final_neutra`/
  `terminacao_final_imperativa` em vez de cair em `verbo_imperativo`/`outro`
  como antes). As duas exceções sem subclasse documentada na central
  (`terminacao_passado`/`terminacao_futuro`, do `EP`) foram decididas indo
  pra `verbo` — mesma família de cor do radical que já carrega essa marca
  de tempo. Testado ponta a ponta (37 combinações de tag/forma): 0 caem em
  cinza sem ser o fallback `outro` intencional (tag genuinamente
  desconhecida).
- **Chinês caía em cinza e sem fonte (corrigido junto com a variante zh).**
  Dois conjuntos fixos ignoravam qualquer idioma fora dos 5 originais:
  `ffmpeg_utils._IDIOMAS = {"pt","en","es","fr","ko"}` fazia o `zh` cair no
  modo morfológico e sair no cinza `#666666` em vez da cor do idioma; e
  `if lang == "ko"` (em `ffmpeg_utils` e `renderizacao`) só aplicava a fonte
  CJK ao coreano, então o chinês renderizava em Arial — quadradinhos (□).
  Mesma família do bug das classes finas do coreano. Agora `_IDIOMAS` deriva
  de `CORES_IDIOMAS` (extensível sozinho) e a fonte vem de
  `config.fonte_cjk(lang)`. Verificado com snapshot antes/depois: os 5
  idiomas saem **byte a byte idênticos** (hash do `.ass` igual nos dois
  fluxos, mais classificação e cores).

## 10. Paleta de cores — emoji-first (legenda multicor)

As cores das 20 classes gramaticais foram repadronizadas pra uma paleta de
**21 cores que têm emoji equivalente** — o critério deixou de ser "nome oficial
CSS" e passou a ser "dá pra sinalizar na descrição do YouTube?".

`cores.legenda_youtube()` monta o bloco pronto pra colar na descrição
(uma linha por classe: emoji + nome). Aceita uma lista pra filtrar/ordenar,
ex: `legenda_youtube(["substantivo", "verbo", ...])` num vídeo sem coreano —
e `cores.classes_para_idiomas(["pt", "en", "es", "fr"])` já devolve essa lista
pronta, a partir dos idiomas do vídeo. O 2º parâmetro (`idiomas`) ajusta os
rótulos: `particula` é a única classe de mais de um idioma, então sai como
"Partícula (coreano)" num vídeo sem chinês e "Partícula (coreano/chinês)" num
com. Na prática você não chama nada disso à mão — é a colinha (abaixo).

| Classe | Emoji | Cor | Hex | Origem |
|---|---|---|---|---|
| substantivo | 🖤 | preto | `#000000` | Montessori |
| verbo | 🔴 | vermelho | `#FF0000` | Montessori |
| pronome | 🟣 | roxo | `#800080` | Montessori |
| adverbio | 🟠 | laranja | `#FFA500` | Montessori |
| conjuncao | 🩷 | rosa | `#FF69B4` | Montessori |
| interjeicao | 🏆 | dourado | `#FFD700` | Montessori |
| artigo | 🩵 | azul claro | `#87CEEB` | Montessori — **passou a bater** (era `#0000FF`) |
| adjetivo | 🔵 | azul | `#0000FF` | Montessori (azul escuro) |
| preposicao | 💚 | verde claro | `#66BB6A` | Montessori (verde) |
| nome_proprio | 🟡 | amarelo | `#FFFF00` | mantido |
| pontuacao | 🩶 | cinza | `#808080` | mantido |
| auxiliar | 🤍 | branco | `#FFFFFF` | mantido |
| numeral | 🏻 | pele muito clara | `#FFDFC4` | novo |
| modal | 🏿 | pele escura | `#8D5524` | novo (mantém a família marrom) |
| particula | 🪻 | lilás | `#C8A2C8` | novo |
| terminacao_honorifica | 🪖 | verde escuro | `#556B2F` | renomeada — ver 10b |
| terminacao_nominal | 🪸 | salmão | `#FA8072` | novo — ver 10b |
| terminacao_adjetival | 🏾 | pele morena | `#C68642` | novo |
| terminacao_final | 🍷 | vinho | `#722F37` | era crimson — mesma família |
| sufixo | 🏼 | pele clara | `#F1C27D` | novo |
| *(reserva)* | 🏽 | pele média | `#E0AC69` | sem classe — ver abaixo |

### 10b. Emoji de objeto é aposta — três trocas que a realidade forçou

O emoji existe pra o espectador ligar a linha da descrição com a cor na tela.
Emoji de **objeto** não serve pra isso de forma confiável: quem desenha é cada
fabricante, e a cor muda.

| Era | Virou | Por quê |
|---|---|---|
| 🧶 novelo = verde escuro | — | O novelo é desenhado **vermelho ou rosa** em quase toda plataforma. Nunca foi verde. |
| 📗 livro = verde claro | 💚 coração verde | Coração é cor sólida e única, a família mais confiável depois das formas geométricas. |
| verde escuro `#2E7D32` | 🪸 salmão `#FA8072` | Três verdes juntos não se distinguem na descrição. Um deles tinha que sair. |

**Quem ficou com o quê, e por quê:** `preposicao` é uma das nove categorias
Montessori, e a cor dela lá é **verde** — então ela ficou com o verde claro. O
salmão foi pra `terminacao_nominal`, que não é Montessori. Sobraram dois
verdes, agora bem afastados.

Descartados no caminho, com os motivos: **🇲🇴** (o Windows não desenha bandeira
— mostra as letras `MO`; a bandeira tem três cores; e é bandeira de território
num canal que mira o Bilibili), **🍣** (multicolorido: arroz branco + alga) e
**🍑** (conotação sexual consolidada na internet).

**Sobraram dois verdes, e o `#556B2F` foi renomeado de "verde oliva" pra
"verde escuro"** (`dark green` em inglês). O nome estava livre — o antigo
verde escuro `#2E7D32` saiu da paleta — e "escuro/claro" descreve o par muito
melhor pro espectador do que "oliva/claro", que não diz qual é mais escuro.
A cor e o emoji não mudaram, só o nome.

**A rede de segurança é o nome da cor na legenda básica.** Foi decisão
consciente aceitar o risco dos emoji de objeto e dos emoji novos: mesmo que
🪖 ou 🪸 apareçam com a cor errada — ou como quadradinho num aparelho antigo —
a linha `🪖 dark green — honorific ending` continua legível e resolve.

**Ainda são apostas na paleta:** 🪖 capacete, 🪻 flor, 🍷 taça, 🏆 troféu e o
próprio 🪸 coral. Todos são objeto. Se algum aparecer com a cor errada no seu
aparelho, é o mesmo bug do novelo.

> A cor do texto da preposição virou preto sozinha (era branco sobre verde
> escuro): `CORES_TEXTO` é derivado da luminância, não escrito à mão.

**Os 5 tons de pele são muito parecidos entre si**, então foram distribuídos
pra ficar o mais longe possível uns dos outros nas classes que podem aparecer
lado a lado:

- `numeral` 🏻 (o mais claro) e `modal` 🏿 (o mais escuro) ficam nos extremos —
  são os dois que podem dividir a mesma linha (numeral existe em todos os
  idiomas, modal só no inglês).
- `terminacao_adjetival` 🏾 e `sufixo` 🏼 são **exclusivos do coreano**, então
  nunca caem na mesma linha que `modal` (só inglês) — dá pra usar tons
  vizinhos ali sem risco.
- 🏽 pele média fica **de reserva, sem classe**, de propósito: deixa um degrau
  vazio no meio da escala, afastando os tons que estão em uso.

`CORES_TEXTO` (preto ou branco por cima do fundo) agora é **derivado** da mesma
regra de luminância que `ffmpeg_utils`/`renderizacao` aplicam ao desenhar
(`> 128 → preto`), em vez de uma tabela escrita à mão — as duas não têm mais
como discordar.

> ⚠️ Vídeos já queimados mantêm as cores antigas — a legenda da descrição
> precisa bater com a paleta usada naquele `.ass`. Pra atualizar um vídeo
> antigo, é regerar o `.ass` (`caption-multicolor-*-generate`) e requeimar.

### Cores por idioma (vídeo multi-idioma cor única)

Paleta diferente da de cima em **uso** — aqui é 1 cor por IDIOMA, não por classe
gramatical — mas sai das mesmas 21 cores com emoji. Fica em
`config.CORES_IDIOMAS`; a legenda vem de
`cores.legenda_youtube_idiomas(config.CORES_IDIOMAS, ordem)`.

| Ordem na tela | Idioma | Emoji | Cor | Hex |
|---|---|---|---|---|
| y=100 | **Inglês** | 💚 | verde claro | `#66BB6A` |
| y=180 | Português | 🟡 | amarelo | `#FFFF00` |
| y=260 | Espanhol | 🟠 | laranja | `#FFA500` |
| y=340 | Francês | 🩵 | azul claro | `#87CEEB` |
| y=420 | Coreano | 🩷 | rosa | `#FF69B4` |
| y=500 | Chinês | 🟣 | roxo | `#800080` |

**O inglês é o idioma anfitrião, então é a primeira linha.** É a língua da
narração, é a origem que o tradutor automático do YouTube usa, e é o que a
maior parte do público lê. A ordem mora em `constants.POSICOES_Y` /
`POS_SIGLA_Y`, e é dali que os outros lugares a copiam
(`sorted(idiomas, key=POSICOES_Y.get)`): a pilha da tela, a legenda da
descrição e o card do vídeo saem todos na mesma sequência — a mesma ideia da
ordem por frequência das classes, uma ordem só, aprendida uma vez.

Vizinho não pode se parecer com vizinho. Ao subir o inglês pro topo, o
amarelo (pt) passou a ficar encostado no laranja (es) — medido, **ΔE\*ab 52,9**,
mais folgado que o par rosa/roxo (ko/zh, **44,4**) que já estava valendo. O pior
vizinho da pilha não mudou, então **nenhuma cor precisou mudar** junto com a
ordem.

Cada idioma manteve a cor que já tinha, só migrada pro tom equivalente da
paleta — **com uma exceção**: o chinês. O tom mais próximo do `#B388FF` antigo
seria o lilás 🪻, mas as legendas ficam **empilhadas** e o chinês cai logo
abaixo do coreano — lilás encostado em rosa é o par mais parecido da paleta
inteira. Virou roxo 🟣, que mantém a família e contrasta com o vizinho.

Como as cores por idioma e as por classe gramatical nunca aparecem no mesmo
vídeo (são níveis diferentes — `_final_idiomas` vs `_final_multicolor`), elas
podem reusar os mesmos tons sem conflito.

### As duas centrais de cores

| Arquivo | Idiomas |
|---|---|
| `assets/central-decisao-cores.html` | 5 (pt/en/es/fr/ko) |
| `assets/central-decisao-cores-zh.html` | 6 (+ chinês) |

**As 20 classes e as 21 cores são idênticas nas duas** — o chinês não trouxe
categoria nova. O que difere: exemplos por idioma, a lista de cores por idioma,
o nome/definição de `particula` (que no chinês também se aplica) e os textos de
cabeçalho.

As duas saem de `assets/gerar-central-cores.py`, que lê o `cores.py` como fonte
única e usa o próprio `central-decisao-cores.html` como template de
estrutura/CSS/JS:

```bash
python3 assets/gerar-central-cores.py
```

É idempotente (rodar duas vezes dá o mesmo arquivo). **Depois de mexer em
`cores.py`, rode-o** — senão as centrais ficam mostrando a paleta antiga.
Editar as duas à mão é o que se quer evitar: uma correção entraria numa e não
na outra.

### Legenda poliglota — o público é poliglota, a legenda também

Três sabores por vídeo multicolor, e para um vídeo você cola **os dois
primeiros**:

| Sabor | O que é | Por quê |
|---|---|---|
| **básica (inglês)** | `🔴 verb` | É o que o tradutor automático do YouTube tem chance de converter pra língua de quem assiste |
| **poliglota** | `🔴 verbo · verb · verbo · verbe · 동사 · 动词 → andar · walk · andar · marcher · 걷다 · 走` | A garantia: não depende de tradutor, e o exemplo ensina a cor melhor que o nome da classe sozinho |
| **só português** | `🔴 Verbo` | Pra você conferir |

A primeira linha do bloco poliglota é `PT · EN · ES · FR · KO · ZH` — **sigla,
não nome por extenso**: "Português · Inglês · …" só serve pra quem já lê
português, e a legenda é justamente pra quem não lê. A sigla é a mesma que
aparece ao lado da faixa no vídeo, então o espectador liga a linha da descrição
com o que está vendo na tela.

#### Duas decisões de formato que a realidade forçou

**O separador é `·`, não `/`.** Vários exemplos já têm barra por dentro
(`will / can / must`, `가/는/를`): com `/` entre idiomas, `modal` sairia como
`— / will / can / must / — / —` e não dá pra saber onde termina um idioma e
começa o outro. Nenhum texto das tabelas contém `·` — há um teste que garante.

**Idioma sem exemplo entra como `—`, não some.** A posição é o que identifica
o idioma: o 3º item é sempre espanhol. Se o vazio sumisse, o leitor contaria
errado e atribuiria a palavra ao idioma errado. E o `—` é informação: mostra
que aquela classe não existe naquele idioma.

#### `NOMES_CLASSE_IDIOMA` e `EXEMPLOS_CLASSE` (`cores.py`)

Nome da classe e palavra de exemplo, nos 6 idiomas. Os exemplos **viviam
soltos dentro do HTML da central**, sem quem os validasse e fora do alcance da
colinha; agora são fonte única em `cores.py` e a central os recebe injetados,
como já acontecia com cores, emoji e paleta. Verificado que as duas centrais
saem **byte a byte idênticas** depois da mudança de casa.

### Onde as páginas moram: Artifact, não Drive

As três páginas — as duas centrais e a colinha — são publicadas como
**Artifact**, cada uma com URL fixa. Republicar o mesmo caminho de arquivo
atualiza a página no lugar.

O motivo é evitar versão conflitante. Enquanto elas viviam como cópias no
Drive, toda mudança de cor exigia subir três arquivos de novo, e esquecer um
deixava você olhando uma legenda que não existe mais. As cópias do Drive foram
pra lixeira; a fonte continua sendo o `cores.py`, e o Artifact é a vista
renderizada dela.

O gerador emite **duas formas** de cada página, da mesma fonte:

| Arquivo | Pra quê |
|---|---|
| `<nome>.html` | página autônoma — abre local, tem `<!doctype>`/`<head>`/`<body>` |
| `<nome>-artifact.html` | mesma página sem o invólucro, que o Artifact monta na publicação |

Deixar as tags de invólucro no arquivo publicado aninha html dentro de html, e
o navegador conserta do jeito dele, que não é o nosso.

> ⚠️ **O botão de proposta copia, não baixa.** O visualizador de Artifact
> bloqueia download — o link de arquivo sairia mudo, sem erro. Como a proposta
> ia ser colada numa conversa de qualquer jeito, copiar resolve nos dois
> contextos: página publicada e arquivo local.

### A colinha da descrição do YouTube

`assets/colinha-emojis-youtube.html` — abre no navegador, clica em **Copiar** no
bloco do tipo de vídeo e cola na descrição. Seis blocos prontos:

Doze blocos prontos — dois de vídeo multi-idioma e, para cada conjunto de
idiomas do vídeo multicolor, três sabores:

| Bloco | Sabor | Linhas |
|---|---|---|
| Multi-idioma cor única — 6 idiomas (com chinês) | — | 6 idiomas |
| Multi-idioma cor única — 5 idiomas | — | 5 idiomas |
| Multicolor 6 idiomas | básica (inglês) · poliglota com exemplos · só português | 20 classes |
| Multicolor 5 idiomas | básica · poliglota · português | 20 classes |
| Multicolor sem coreano (pt/en/es/fr) | básica · poliglota | 14 classes |
| Multicolor só latinos (pt/es/fr) | básica · poliglota | 12 classes |

Para um vídeo multicolor, cole **as duas**: a **básica em inglês**, que é o que
o tradutor automático do YouTube tem chance de converter, e a **poliglota**,
que é a garantia — não depende de tradutor nenhum e ainda traz uma palavra de
exemplo por idioma, que ensina a cor melhor que o nome da classe sozinho.

**Escolha o bloco pelos idiomas que o vídeo realmente tem.** Um vídeo sem
coreano não deve listar as terminações coreanas, e um só com idiomas latinos
não tem `modal`/`auxiliar` (inglês) — a colinha já corta essas linhas.

Ela sai do **mesmo** `gerar-central-cores.py`, do mesmo `cores.py`, junto com as
duas centrais. É esse o ponto de gerar em vez de escrever à mão: mudou uma cor
ou um emoji, roda o script e a colinha muda junto — não tem como a descrição do
YouTube ficar anunciando uma cor que o vídeo não usa mais.

### A ordem é uma só: por frequência

`cores.ORDEM_FREQUENCIA` — as 20 classes da mais frequente para a mais rara,
**medida**, não chutada: contagem das 3.127 palavras já classificadas do
Mateus 2 nos 5 idiomas, com `AUX` somado a `verbo` e `CCONJ`+`SCONJ` a
`conjuncao`, como o projeto mapeia.

```
verbo 18,3% · substantivo 14,4% · pontuacao 11,6% · preposicao 11,4%
pronome 10,5% · artigo 10,4% · conjuncao 9,3% · nome_proprio 5,8%
adverbio 5,2% · adjetivo 2,5%                     -> estas dez dão 99,4%
```

Vale nos **três** lugares em que a legenda aparece: o "Resumo rápido" da
central, os blocos da colinha (via `classes_para_idiomas()`) e o card do vídeo.

Duas decisões dentro dessa:

- **É constante, não recalculada por vídeo.** Se cada capítulo reordenasse a
  legenda pela sua própria contagem, o espectador teria que reaprender a
  ordem a cada vídeo. Uma ordem, aprendida uma vez.
- **A primeira metade é o corte natural.** Como as dez primeiras cobrem 99,4%
  das palavras, dividir 10/10 não é só cortar no meio: a tela 1 do card
  sozinha já basta pra ler o vídeo inteiro.

### Abreviar os nomes longos: tentado, medido, descartado

As quatro terminações coreanas são as linhas mais longas de qualquer legenda —
`terminação honorífica · honorific ending · terminación honorífica ·
terminaison honorifique`. Abreviar a palavra que se repete
(`terminação/terminación/terminaison` → `term.`) economiza 32 caracteres, e
produz isto:

```
term. honor. · honorific end. · term. honor. · term. honor.
```

Português, espanhol e francês viram a **mesma string**. A medição foi feita nas
quatro classes de terminação e nenhuma escapava (4→2, 4→3, 4→2, 4→3 nomes
latinos distintos). Economizar largura apagando a distinção entre três idiomas
é destruir exatamente o que a legenda poliglota existe pra mostrar.

O comprimento se resolve no **layout** — coluna latina mais larga e quebra de
linha —, não no texto. O mecanismo foi removido e o comentário no `cores.py`
guarda a medição, pra ninguém tentar de novo.

## 11. O card de legenda que abre e fecha o vídeo

`assets/gerar-card-legenda.py` → dois PNG 1920x1080 por variante de idioma,
prontos pra entrar na planilha de imagens e o pipeline colocar no começo e/ou
no fim do vídeo.

```
python3 assets/gerar-card-legenda.py --png
```

| Saída | O que é |
|---|---|
| `card_legenda_cores_1.png` / `_2.png` | 5 idiomas (pt/en/es/fr/ko) |
| `card_legenda_cores_zh_1.png` / `_2.png` | 6 idiomas (com chinês) |
| `card-legenda-cores.html` / `-zh.html` | as duas telas, pra conferir antes |
| `card-legenda-cores*-artifact.html` | as mesmas, no formato do Artifact |

### Duas telas — é regra, não coincidência

São 20 classes. Numa tela só cada linha fica com 45 px de altura num frame
1080p — ilegível no celular, que é onde a maior parte do público assiste. Em
duas, a linha dobra pra 85 px. E o corte 10/10 é o de `ORDEM_FREQUENCIA`: quem
só vir a tela 1 já cobre 99% das palavras.

**`NUM_TELAS = 2` não é o resultado de 20 dividir bonito por 10.** Três telas
custariam mais tempo de vídeo do que a informação vale, e quem precisa procurar
uma cor em três lugares desiste. Se um dia entrar uma classe nova, quem cede é
a altura da linha, nunca o número de telas:

- `_dividir()` reparte em **exatamente duas** fatias, a maior primeiro (21 sai
  11+10). A tela mais cheia é a das classes frequentes de propósito — é a que o
  espectador realmente lê, e é onde os nomes latinos são mais curtos.
- `_metricas()` encolhe fonte, quadradinho e respiro na proporção
  `10 / linhas`. Medido no Chromium: **12 linhas ainda cabem** nos 1080 px sem
  cortar uma célula sequer. Duas telas seguram até 24 classes.
- A tabela usa `grid-auto-rows:1fr`, não `repeat(10,1fr)` — ninguém conta
  linha, e a altura sobrante se divide sozinha.
- As medidas vão como **variável CSS no próprio elemento** da tela, não numa
  folha por tela: assim as duas telas convivem na página de conferência com
  tamanhos diferentes sem ninguém escopar seletor.

O rodapé da tela 1 só promete os "99%" enquanto a primeira metade for
exatamente as dez classes cuja frequência foi medida (`DEZ_MEDIDAS`). Se a
divisão mudar, ele troca sozinho pra uma frase sem número — a alternativa seria
anunciar uma cobertura inventada.

### Quadradinho de cor, não emoji

O emoji é uma muleta da **descrição** do YouTube, que é texto puro e não aceita
cor. O card é imagem: pinta o hexadecimal exato que a legenda usa no vídeo.
Emoji ali mostraria a cor aproximada que a fonte de quem renderiza escolheu —
exatamente o problema que o 🧶 causou (ver 10b).

A borda fininha em cada quadradinho existe pro branco e o cinza-claro não
sumirem no fundo claro.

### Duas variantes, pela mesma razão das duas centrais

Um vídeo de 5 idiomas não pode exibir uma coluna `中文`, nem `颜色图例` no
título: o espectador procuraria no vídeo uma cor que não está lá. Colunas,
título e rodapé saem todos dos idiomas da variante.

### A largura da coluna latina não é um número escolhido à mão

É `max-content`: mede o nome mais longo **daquela tela** e o CJK fica com o que
sobra. Por isso a tela 2, das terminações coreanas, sai naturalmente mais larga
que a tela 1 — sem ninguém reajustar quando um nome muda.

### O print é renderizado, não tirado à mão

Print manual depende do tamanho da janela e do zoom do navegador. O script
renderiza no Chromium headless com o tamanho como argumento, então o PNG sai
sempre exatamente no frame do vídeo.

> ⚠️ **`--window-size` é a janela, não a página.** No headless a página recebe
> ~87 px a menos, e esse desconto muda com a versão do Chromium: pedir
> 1920x1080 direto entrega uma imagem de 1080 px com só 993 px de página
> dentro, e o rodapé some **calado**. Por isso o script renderiza com 320 px de
> folga e corta os 1920x1080 do canto superior esquerdo.

### Só fonte de sistema

Nada de fonte vinda da internet: o PNG é renderizado aqui e o print de
conferência é aberto na sua máquina — uma fonte remota chega numa das duas e
não na outra. `Arial` primeiro (é o que o `.ass` já declara no resto do
pipeline) e o `Noto CJK` entra sozinho quando o glifo é coreano ou chinês, que
é como o navegador resolve fallback.

### O que ainda falta

O card está pronto como **imagem**. Falta a ponta do pipeline: a variável que
liga/desliga o card e diz se ele entra no começo, no fim ou nos dois, e a
montagem em si nos `video-base-*`. Isso encosta na consolidação dos seis
`video-base-*` (decisão adiada 9.1) — se a consolidação vier antes, o card
vira um campo do perfil em vez de seis edições paralelas.

