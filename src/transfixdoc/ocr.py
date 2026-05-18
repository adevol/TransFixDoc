"""OCR backends."""

import os
from pathlib import Path
from typing import Protocol

from transfixdoc.models import Document, Page


class OcrBackend(Protocol):
    """Backend that extracts text and optional page images from a PDF."""

    def extract_text(self, pdf_path: Path, output_dir: Path) -> Document:
        """Extract page text and optional page images from a PDF.

        Args:
            pdf_path: PDF to process.
            output_dir: Directory for backend intermediates.

        Returns:
            Extracted document.
        """


class DoclingOcrBackend:
    """Docling-backed OCR implementation."""

    def __init__(self, image_scale: float = 2.0) -> None:
        self.image_scale = image_scale

    def extract_text(self, pdf_path: Path, output_dir: Path) -> Document:
        """Extract text and page images with Docling.

        Args:
            pdf_path: PDF to process.
            output_dir: Directory for generated page images.

        Returns:
            Extracted document.
        """
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        output_dir.mkdir(parents=True, exist_ok=True)
        options = PdfPipelineOptions()
        options.generate_page_images = True
        options.images_scale = self.image_scale
        options.ocr_options = RapidOcrOptions(
            backend="torch", force_full_page_ocr=True, lang=["english"]
        )
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        doc = converter.convert(pdf_path).document
        pages = []

        for page_no in sorted(doc.pages):
            try:
                page = doc.pages[page_no]
                image_path = _save_page_image(page, output_dir, page_no)
                text = doc.export_to_markdown(page_no=page_no).strip()
                pages.append(Page(page_number=page_no, text=text, image_path=image_path))
            except Exception as exc:
                pages.append(Page(page_number=page_no, error=str(exc)))

        if not pages:
            pages.append(Page(page_number=1, error="No pages found."))

        return Document(source_path=pdf_path, pages=pages)


class MistralOcrBackend:
    """Mistral-backed OCR implementation."""

    def __init__(self, image_scale: float = 2.0) -> None:
        self.image_scale = image_scale

    def extract_text(self, pdf_path: Path, output_dir: Path) -> Document:
        """Extract text with Mistral OCR and render page images locally.

        Args:
            pdf_path: PDF to process.
            output_dir: Directory for generated page images.

        Returns:
            Extracted document.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        client = _mistral_client()
        uploaded = client.files.upload(
            file={"file_name": pdf_path.name, "content": pdf_path.read_bytes()},
            purpose="ocr",
        )
        try:
            signed = client.files.get_signed_url(file_id=uploaded.id)
            response = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": signed.url},
            )
        finally:
            client.files.delete(file_id=uploaded.id)
        images = _render_page_images(pdf_path, output_dir, self.image_scale)
        pages = [
            Page(
                page_number=_page_index(page) + 1,
                text=_page_markdown(page).strip(),
                image_path=images.get(_page_index(page) + 1),
            )
            for page in response.pages
        ]
        return Document(source_path=pdf_path, pages=pages)


def get_ocr_backend(name: str, image_scale: float = 2.0) -> OcrBackend:
    """Create an OCR backend by name.

    Args:
        name: Backend identifier.

    Returns:
        OCR backend.
    """
    if name == "docling":
        return DoclingOcrBackend(image_scale=image_scale)
    if name == "mistral":
        return MistralOcrBackend(image_scale=image_scale)
    raise ValueError(f"Unsupported OCR backend: {name}")


def _save_page_image(page: object, output_dir: Path, page_no: int) -> Path | None:
    image = getattr(getattr(page, "image", None), "pil_image", None)
    if image is None:
        return None
    path = output_dir / f"page-{page_no:03}.png"
    image.save(path, format="PNG")
    return path


def _mistral_client() -> object:
    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral

    return Mistral(api_key=os.environ["MISTRAL_API_KEY"])


def _render_page_images(pdf_path: Path, output_dir: Path, image_scale: float) -> dict[int, Path]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_path)
    paths: dict[int, Path] = {}
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                path = output_dir / f"page-{index + 1:03}.png"
                page.render(scale=image_scale).to_pil().save(path)
                paths[index + 1] = path
            finally:
                page.close()
    finally:
        pdf.close()
    return paths


def _page_index(page: object) -> int:
    if isinstance(page, dict):
        return int(page.get("index", 0))
    return int(getattr(page, "index", 0))


def _page_markdown(page: object) -> str:
    if isinstance(page, dict):
        return str(page.get("markdown", ""))
    return str(getattr(page, "markdown", ""))
