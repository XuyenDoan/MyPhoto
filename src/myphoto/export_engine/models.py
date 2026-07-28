"""Export configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

ExportFormat = Literal["jpeg", "png", "tiff"]

_VALID_FORMATS: tuple[ExportFormat, ...] = get_args(ExportFormat)


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """How and where :class:`~myphoto.export_engine.writer.ExportEngine` writes a file.

    ``rename_pattern`` is formatted with ``stem`` (source filename without
    extension), ``name`` (source filename with extension), and ``index``
    (the image's position in the current batch, 0-based) — e.g.
    ``"{stem}_myphoto"`` or ``"IMG_{index:04d}"``. The output extension is
    always derived from ``format`` and appended automatically.
    """

    format: ExportFormat
    output_dir: Path
    quality: int = 95
    rename_pattern: str = "{stem}"

    def __post_init__(self) -> None:
        if self.format not in _VALID_FORMATS:
            raise ValueError(f"Unsupported export format: {self.format!r}")
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be in [1, 100], got {self.quality}")
