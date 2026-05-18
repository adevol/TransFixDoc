# TransFixDoc

This repo analyses image-based PDFs and writes a correction or translation report based on the original input.

Mistral OCR gives by far the best results on the sample scanned manual. Docling is kept
as a local fallback backend.

## Setup

```powershell
uv sync
```

Create `.env`:

```env
OPENAI_API_KEY=...
MISTRAL_API_KEY=...
```

## Correct The Sample PDF

```powershell
uv run transfixdoc "data\血压仪德文说明书 英文部分-260509.pdf" `
  --task correct `
  --source-language en `
  --ocr-backend mistral `
  --report output2\blood-pressure-correction-report.pdf `
  --workdir output2\work `
  --image-scale 2.0
```

Output:

```text
output2/blood-pressure-correction-report.pdf
```

## Docling Fallback

```powershell
uv run transfixdoc "data\血压仪德文说明书 英文部分-260509.pdf" --task correct --source-language en --ocr-backend docling --report output\blood-pressure-correction-report.pdf --workdir output\work --image-scale 2.0
```

## Translate

```powershell
uv run transfixdoc input.pdf --task translate --source-language de --target-language en --ocr-backend mistral --report output\translation-report.pdf
```

## Options

- `--ocr-backend mistral`: recommended for scanned PDFs.
- `--ocr-backend docling`: local fallback.
- `--task correct`: correct spelling/OCR/grammar.
- `--task translate`: translate each page.
- `--image-scale 2.0`: sharper report images.
- `--check-language`: verify `--source-language` with an LLM detection pass before processing. Off by default.
