"""Language detection."""

from pydantic import BaseModel, Field

from transfixdoc.models import Document


class LanguageResult(BaseModel):
    """Detected language result."""

    language: str = Field(description="ISO 639 language code, such as de or en.")


def detect_language(document: Document, model: str) -> str:
    """Detect the source language of a document.

    Args:
        document: OCR output.
        model: OpenAI model name.

    Returns:
        ISO language code.
    """
    from openai import OpenAI

    sample = "\n".join(page.text for page in document.pages)[:500]
    response = OpenAI().responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": "Return only the dominant language as an ISO 639-1 code.",
            },
            {"role": "user", "content": sample or "No text was extracted."},
        ],
        text_format=LanguageResult,
    )
    return response.output_parsed.language.lower()
