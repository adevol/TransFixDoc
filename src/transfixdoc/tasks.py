"""Translation and correction tasks."""

import base64
from difflib import SequenceMatcher
from typing import Callable

from transfixdoc.models import Document, Page, PipelineConfig


def translate_pages(document: Document, config: PipelineConfig) -> Document:
    """Translate each document page.

    Args:
        document: OCR output.
        config: Pipeline settings.

    Returns:
        Document with translated page text.
    """
    target = config.target_language
    if not target:
        raise ValueError("--target-language is required for translation")
    return _process_pages(
        document,
        config,
        system=(
            "Translate the user's page text completely and faithfully from "
            f"{config.source_language} to {target}. Return only the translation."
        ),
        transform=lambda original, generated: generated.strip(),
    )


def correct_pages(document: Document, config: PipelineConfig) -> Document:
    """Correct each document page.

    Args:
        document: OCR output.
        config: Pipeline settings.

    Returns:
        Document with corrected page text and highlighted edits.
    """
    return _process_pages(
        document,
        config,
        system=(
            "Correct OCR, spelling, grammar, and terminology issues in the page "
            "text. Return only the full corrected text."
        ),
        transform=_highlight_corrections,
    )


def _process_pages(
    document: Document,
    config: PipelineConfig,
    *,
    system: str,
    transform: Callable[[str, str], str],
) -> Document:
    from openai import OpenAI

    client = OpenAI()
    pages = []
    for page in document.pages:
        try:
            response = client.responses.create(
                model=config.task_model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": _page_content(page)},
                ],
            )
            text = transform(page.text, response.output_text)
            pages.append(page.model_copy(update={"text": text, "error": None}))
        except Exception as exc:
            pages.append(
                Page(
                    page_number=page.page_number,
                    text="",
                    image_path=page.image_path,
                    error=str(exc),
                )
            )
    return Document(source_path=document.source_path, pages=pages)


def _page_content(page: Page) -> str | list[dict[str, str]]:
    text = "" if page.text.strip() == "<!-- image -->" else page.text.strip()
    if page.image_path and page.image_path.exists():
        image = base64.b64encode(page.image_path.read_bytes()).decode("ascii")
        prompt = (
            "Correct and verify the English spelling visible on this scanned page. "
            "Use the OCR text as a hint when it is useful.\n\n"
            f"OCR text:\n{text or '[No useful OCR text]'}"
        )
        return [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:image/png;base64,{image}"},
        ]
    return text or "[No OCR text]"


def _highlight_corrections(original: str, corrected: str) -> str:
    original_words = original.split()
    corrected_words = corrected.split()
    matcher = SequenceMatcher(a=original_words, b=corrected_words)
    output = []

    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        words = corrected_words[j1:j2]
        if tag == "equal":
            output.extend(words)
        elif words:
            output.append(f"**{' '.join(words)}**")

    return "Page is correct." if output == original_words else " ".join(output)
