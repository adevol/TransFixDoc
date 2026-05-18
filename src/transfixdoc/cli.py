"""Command line interface."""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from transfixdoc.language import detect_language
from transfixdoc.models import PipelineConfig, Task
from transfixdoc.ocr import get_ocr_backend
from transfixdoc.report import write_report
from transfixdoc.tasks import correct_pages, translate_pages

app = typer.Typer()


@app.command()
def run(
    input_pdf: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    task: Annotated[Task, typer.Option()],
    source_language: Annotated[str, typer.Option()],
    report: Annotated[Path, typer.Option()],
    target_language: Annotated[str | None, typer.Option()] = None,
    ocr_backend: Annotated[str, typer.Option()] = "docling",
    image_scale: Annotated[
        float, typer.Option(help="Scale factor for saved page images.")
    ] = 2.0,
    detection_model: Annotated[str, typer.Option()] = "gpt-4.1-mini",
    task_model: Annotated[str, typer.Option()] = "gpt-4.1-mini",
    skip_language_check: Annotated[bool, typer.Option()] = False,
    workdir: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Analyze a PDF and write a translation or correction report."""
    load_dotenv()
    config = PipelineConfig(
        task=task,
        source_language=source_language.lower(),
        target_language=target_language,
        report_path=report,
        ocr_backend=ocr_backend,
        image_scale=image_scale,
        detection_model=detection_model,
        task_model=task_model,
        workdir=workdir or report.parent / "work",
    )
    document = get_ocr_backend(config.ocr_backend, config.image_scale).extract_text(
        input_pdf, config.workdir
    )
    detected = config.source_language if skip_language_check else detect_language(document, config.detection_model)

    if detected != config.source_language:
        raise typer.BadParameter(
            f"source language mismatch: expected {config.source_language}, detected {detected}"
        )

    result = (
        translate_pages(document, config)
        if config.task == "translate"
        else correct_pages(document, config)
    )
    write_report(result, config.report_path)
    raise typer.Exit(1 if any(page.error for page in result.pages) else 0)


if __name__ == "__main__":
    app()
