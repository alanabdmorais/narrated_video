# Configuração do pipeline — referência central

Este documento é o **catálogo único** de tudo que é configurável no pipeline:
convenções de nome de arquivo (`config.py`), pastas do Drive, e todas as
planilhas Google Sheets (ID, aba, para que serve, quem lê/escreve). Serve pra
responder "onde eu mudo X?" sem precisar abrir 19 notebooks + `config.py` toda
vez.

Não duplica os comentários que já existem em `modulos/config.py` — só organiza
tudo num lugar só e cruza com o que cada notebook realmente expõe na célula de
Configuração hoje.

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

**Os nomes do AudioTreasure são irregulares**, por isso cada livro carrega seu
próprio `modelo_audio` em vez de o código deduzir um padrão que não existe:

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

> ⚠️ **Zacarias 14 não existe no índice da fonte** — o site lista só 13
> capítulos, e o livro tem 14. A conferência reporta como faltando. Se você
> precisar desse capítulo, vai ter que arrumar o áudio por fora.

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

