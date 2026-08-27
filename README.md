# narrated_video

Pipeline de geração de vídeos narrados da Bíblia (Colab/Python), migrado do Google
Drive para este repositório. Aqui ficam **apenas código e dados** — os arquivos de
mídia bruta (vídeo, áudio) continuam vivendo só no Google Drive, nunca neste git
(veja `.gitignore`).

## Estrutura

```
narrated_video/
├── pipeline/
│   ├── notebooks/          → notebooks Colab "oficiais" (versão atual do pipeline)
│   ├── notebooks.backup/   → versões anteriores/alternativas dos notebooks
│   ├── modulos/            → código Python (.py) importado pelos notebooks
│   └── dados_lexico/       → JSONs de apoio (títulos e eventos bíblicos)
├── assets/
│   ├── *.html, *.md, *.csv → utilitários soltos (limpeza de roteiro, vocabulário
│   │                          de tags, decisão de cores, biblioteca da Bíblia Almeida)
│   ├── prompts/            → prompts usados manualmente (ex: descrição de cena no Gemini)
│   └── planilhas/          → exports das planilhas Google Sheets usadas pelo pipeline
└── videos/
    └── <nome_do_video>/    → roteiro, legendas (.srt/.ass), classificações (.csv)
                               e afins de cada vídeo — SEM o vídeo/áudio em si
```

## O que NÃO está aqui

Por definição do projeto, mídia bruta (`.mp4`, `.mp3`, `.wav`, `.mov`, `.m4a` etc.)
nunca é versionada neste repositório — ela é grande demais e já vive de forma
confiável no Google Drive (`narrated_video/videos/<nome>/`), que continua sendo a
fonte de verdade para esses arquivos. Os notebooks já sabem baixar/subir mídia do
Drive quando rodam.

Também não entrou: `assets/cookies.txt` (contém sessão ativa de login do YouTube —
nunca deve ser versionado, mesmo em repositório privado) e `assets/marca/` (logo em
imagem, fora do escopo de "código e dados").

## Nota sobre `assets/planilhas/`

Quatro planilhas do Google Sheets alimentam o pipeline (bibliotecas de áudio/match).
A exportação nativa em CSV só trouxe dados completos para `Biblioteca_de_Match.csv`.
Para as outras três (`Biblioteca_Match_Audio`, `Freesound_Audio_Stock`,
`Pixabay_YT_Audio_Stock` — todas com múltiplas abas), a exportação CSV voltou vazia,
então foi salvo em `.md` um snapshot em texto do conteúdo (pode estar truncado para
planilhas grandes). Para os dados completos e atualizados, consulte as planilhas
originais no Google Drive.

## Nota sobre `videos/40_Matt_02/`

Existem dois arquivos `legendas_40_Matt_02_v2.ass` no Drive, com o mesmo nome mas
IDs e conteúdo diferentes (provavelmente um rascunho e uma versão corrigida). Para
não perder nenhum dos dois na migração, ambos foram trazidos com nomes distintos:

- `legendas_40_Matt_02_v2.ass` — versão mais recente (criada por último no Drive).
- `legendas_40_Matt_02_v2-versao-anterior-1702.ass` — versão anterior/rascunho.

Vale conferir manualmente qual das duas é a "boa" antes de usar em produção.
