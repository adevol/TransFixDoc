"""PDF report generation."""

import html
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from transfixdoc.models import Document


def write_report(document: Document, output_path: Path) -> Path:
    """Write a PDF report.

    Args:
        document: Translated or corrected document.
        output_path: Report PDF path.

    Returns:
        Written report path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Report for {html.escape(str(document.source_path))}", styles["Title"])]

    for page in document.pages:
        story.extend([Spacer(1, 12), Paragraph(f"Page {page.page_number}", styles["Heading2"])])
        if page.image_path and page.image_path.exists():
            story.extend([Image(str(page.image_path), width=420, height=594), Spacer(1, 12)])
        text = f"<b>Error:</b> {html.escape(page.error)}" if page.error else _markdown_bold(page.text)
        story.append(Paragraph(text.replace("\n", "<br/>"), styles["BodyText"]))
        story.append(PageBreak())

    SimpleDocTemplate(str(output_path), pagesize=A4).build(story)
    return output_path


def _markdown_bold(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
