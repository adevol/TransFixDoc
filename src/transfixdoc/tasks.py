"""Translation and correction tasks."""

import base64
from concurrent.futures import ThreadPoolExecutor
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
        system=_with_context(
            config,
            "Translate the user's page text completely and faithfully from "
            f"{config.source_language} to {target}. Return only the translation.",
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
        system=_with_context(
            config,
            "Correct OCR errors, spelling, grammar, terminology, and sentences "
            "that are grammatically valid but logically incoherent, missing "
            "words, or read as literal translations from another language. If a "
            "sentence is already natural and accurate, leave it unchanged "
            "word-for-word — do not rephrase for style.\n"
            "\n"
            "Examples:\n"
            "Input: 'Wait until the green light.'\n"
            "Output: 'Wait until the green light appears.'\n"
            "\n"
            "Input: 'Please do not disassemble it privately.'\n"
            "Output: 'Please do not disassemble it yourself.'\n"
            "\n"
            "Input: 'Lift the case by sliding it through the handle.'\n"
            "Output: 'Lift the case by gripping the handle.'\n"
            "\n"
            "Input: 'Press the START button to begin.'\n"
            "Output: 'Press the START button to begin.'\n"
            "\n"
            "Return only the full corrected text.",
        ),
        transform=_highlight_corrections,
    )


def _with_context(config: PipelineConfig, instruction: str) -> str:
    if config.context:
        return f"Document context: {config.context}\n\n{instruction}"
    return instruction


def _process_pages(
    document: Document,
    config: PipelineConfig,
    *,
    system: str,
    transform: Callable[[str, str], str],
) -> Document:
    from openai import OpenAI

    client = OpenAI()

    def process(page: Page) -> Page:
        try:
            response = client.responses.create(
                model=config.task_model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": _page_input(page)},
                ],
            )
            text = transform(page.text, response.output_text)
            return page.model_copy(update={"text": text, "error": None})
        except Exception as exc:
            return Page(
                page_number=page.page_number,
                text="",
                image_path=page.image_path,
                error=str(exc),
            )

    with ThreadPoolExecutor(max_workers=config.max_workers) as pool:
        pages = list(pool.map(process, document.pages))
    return Document(source_path=document.source_path, pages=pages)


def _page_input(page: Page) -> str | list[dict[str, str]]:
    text = "" if page.text.strip() == "<!-- image -->" else page.text.strip()
    if page.image_path and page.image_path.exists():
        image = base64.b64encode(page.image_path.read_bytes()).decode("ascii")
        prompt = f"OCR text, if available:\n{text or '[No useful OCR text]'}"
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
