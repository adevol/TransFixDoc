"""Language and document-context detection."""

from pydantic import BaseModel, Field

from transfixdoc.models import Document


class DocumentAnalysis(BaseModel):
    """Combined detection result for a document."""

    language: str = Field(
        description="ISO 639-1 code of the dominant language, such as de or en."
    )
    context: str = Field(
        description=(
            "One short sentence describing what kind of document this is and "
            "its subject, e.g. 'User manual for a home blood pressure monitor.'"
        )
    )


def analyze_document(document: Document, model: str) -> DocumentAnalysis:
    """Detect dominant language and a one-sentence document descriptor.

    Args:
        document: OCR output.
        model: OpenAI model name.

    Returns:
        Language code (lowercase) and a short context descriptor.
    """
    from openai import OpenAI

    sample = "\n".join(page.text for page in document.pages)[:1500] or "No text was extracted."
    response = OpenAI().responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "From the page text, return the dominant language as an "
                    "ISO 639-1 code and one short sentence describing what "
                    "kind of document this is and its subject."
                ),
            },
            {"role": "user", "content": sample},
        ],
        text_format=DocumentAnalysis,
    )
    result = response.output_parsed
    return DocumentAnalysis(language=result.language.lower(), context=result.context.strip())
