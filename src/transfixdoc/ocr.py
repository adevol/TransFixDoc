"""OCR backends."""

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
        pages = []

        for page_no in range(1, _page_count(pdf_path) + 1):
            try:
                result = converter.convert(pdf_path, page_range=(page_no, page_no))
                doc = result.document
                page = doc.pages[page_no]
                image_path = _save_page_image(page, output_dir, page_no)
                text = doc.export_to_markdown(page_no=page_no).strip()
                pages.append(Page(page_number=page_no, text=text, image_path=image_path))
            except Exception as exc:
                pages.append(Page(page_number=page_no, error=str(exc)))

        if not pages:
            pages.append(Page(page_number=1, error="No pages found."))

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
    raise ValueError(f"Unsupported OCR backend: {name}")


def _save_page_image(page: object, output_dir: Path, page_no: int) -> Path | None:
    image = getattr(getattr(page, "image", None), "pil_image", None)
    if image is None:
        return None
    path = output_dir / f"page-{page_no:03}.png"
    image.save(path, format="PNG")
    return path


def _page_count(pdf_path: Path) -> int:
    import pypdfium2 as pdfium

    return len(pdfium.PdfDocument(pdf_path))
