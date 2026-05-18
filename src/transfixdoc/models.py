"""Shared pipeline models."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


Task = Literal["translate", "correct"]


class Page(BaseModel):
    """One PDF page at any pipeline stage."""

    page_number: int
    text: str = ""
    image_path: Path | None = None
    error: str | None = None


class Document(BaseModel):
    """A PDF document represented as pages."""

    source_path: Path
    pages: list[Page]


class PipelineConfig(BaseModel):
    """Runtime settings for the document pipeline."""

    task: Task
    source_language: str
    target_language: str | None = None
    report_path: Path
    ocr_backend: str = "docling"
    image_scale: float = Field(default=2.0, gt=0)
    detection_model: str = "gpt-4.1-mini"
    task_model: str = "gpt-4.1-mini"
    workdir: Path | None = None
