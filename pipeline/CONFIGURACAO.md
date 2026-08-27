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

## 9. Lacunas conhecidas / pontos de atenção

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
