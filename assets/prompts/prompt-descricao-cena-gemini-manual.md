# Prompt — Descrição de Cena (uso manual no chat do Gemini)

Copie o texto abaixo, cole no chat do Gemini (app ou gemini.google.com), e anexe as
imagens do lote (fotos direto, ou os frames de início/meio/fim de cada vídeo — veja
"Como extrair frames de um vídeo" no final deste arquivo).

Funciona igual pra imagem (Pixabay Images) ou vídeo (Pixabay Video) — só muda quantos
frames você anexa por item (1 pra imagem, 3 pra vídeo).

---

## PROMPT (copie a partir daqui)

```
Você vai me ajudar a descrever cenas de fotos/vídeos de banco de imagens (Pixabay) que
uso como fundo em vídeos de conteúdo bíblico/religioso para YouTube.

Vou te enviar um lote de itens. Cada item tem um ID e uma ou mais imagens anexadas
(1 imagem = foto; 3 imagens em sequência = início/meio/fim de um vídeo). Vou te dar
também o Título e as Tags originais (em inglês) de cada item, quando eu tiver.

Para CADA item, gere estes 6 campos:

1. **Tags_PT** — as tags originais (Tags) traduzidas pro português, mesma
   quantidade/ordem, separadas por vírgula.
2. **Tags_EN** — as mesmas tags originais em inglês, só limpas (sem duplicar,
   sem termos genéricos demais tipo "photo" ou "image"), separadas por vírgula.
3. **Tags_Oracao_PT** — 4 a 8 palavras-chave em português que conectem essa cena a
   temas de oração/reflexão bíblica (ex: paz, luz, natureza, contemplação, esperança,
   entrega, silêncio, presença, amanhecer, jornada) — só as que realmente combinam
   com o que aparece na imagem, não force conexão onde não tem.
4. **Tags_Oracao_EN** — a tradução direta das Tags_Oracao_PT.
5. **Descricao_Cena_PT** — 2 a 3 frases objetivas descrevendo o que aparece
   visualmente: cenário, elementos principais, cores, luz, movimento (se for vídeo).
   Sem floreio poético, só o que você realmente vê nas imagens.
6. **Descricao_Cena_EN** — a mesma descrição, em inglês.

Regras importantes:
- NÃO invente elementos que não estão nas imagens.
- Se não tiver certeza de algo, descreva só o que é visualmente claro.
- Mantenha as descrições curtas e diretas — não é pra soar bonito, é pra alimentar
  um sistema de busca por texto depois.

Responda APENAS com um bloco de código JSON, neste formato exato (um objeto por item):

​```json
[
  {
    "id": "1047521",
    "tags_pt": "filhote, cachorro, animal de estimação, fofo, cachorro marrom",
    "tags_en": "puppy, dog, pet, cute, brown dog",
    "tags_oracao_pt": "inocência, novo começo, cuidado, ternura",
    "tags_oracao_en": "innocence, new beginning, care, tenderness",
    "descricao_cena_pt": "Um filhote de cachorro marrom de pelagem curta está deitado, olhando diretamente para a câmera. O fundo é desfocado, em tons neutros, destacando o animal.",
    "descricao_cena_en": "A short-haired brown puppy is lying down, looking directly at the camera. The background is blurred in neutral tones, highlighting the animal."
  }
]
​```

Não escreva nada antes ou depois do bloco JSON. Vou te avisar quando quiser processar
o próximo lote.

Aqui está o primeiro lote:

[COLE AQUI: para cada item, o ID + Título + Tags (se tiver), e anexe as imagens
correspondentes logo depois de cada um]
```

---

## Depois de receber a resposta do Gemini

1. Copie o bloco JSON que ele devolveu.
2. Salve num arquivo `.json` (ex: `lote_01.json`).
3. Repita pro próximo lote (o Gemini não precisa "lembrar" do lote anterior — cada
   lote é independente, então dá pra abrir uma conversa nova se preferir).
4. No fim, você vai ter vários arquivos `lote_01.json`, `lote_02.json`, etc. — o
   notebook de match vai ter uma célula pra juntar todos eles e mesclar na planilha
   automaticamente (não precisa colar campo por campo na mão).

## Quantos itens por lote?

Comece com **5 a 8 itens por lote** (ou seja, até ~24 imagens anexadas de uma vez, se
forem vídeos com 3 frames cada). Se o Gemini gratuito reclamar de limite/tamanho,
diminua para 3-4 itens por lote.

## Como extrair frames de um vídeo (início/meio/fim)

Se for descrever um vídeo (não uma foto), rode isso no terminal ou no Colab pra tirar
3 frames antes de anexar no chat do Gemini:

```bash
# Substitua URL_DO_VIDEO e SAIDA pelo que for usar
ffmpeg -ss 0.5 -i "URL_DO_VIDEO" -vframes 1 -update 1 SAIDA_inicio.jpg
ffmpeg -sseof -2.5 -i "URL_DO_VIDEO" -vframes 1 -update 1 SAIDA_meio.jpg
ffmpeg -sseof -0.5 -i "URL_DO_VIDEO" -vframes 1 -update 1 SAIDA_fim.jpg
```
