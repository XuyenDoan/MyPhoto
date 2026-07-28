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

    The output filename is always the source's stem plus
    :data:`~myphoto.export_engine.naming.EXPORT_SUFFIX` plus the extension
    derived from ``format`` — e.g. ``IMG_0001.jpg`` exports as
    ``IMG_0001_myphoto.jpg`` — so an edited photo is never mistaken for its
    untouched source sitting in the same folder.
    """

    format: ExportFormat
    output_dir: Path
    quality: int = 95

    def __post_init__(self) -> None:
        if self.format not in _VALID_FORMATS:
            raise ValueError(f"Unsupported export format: {self.format!r}")
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be in [1, 100], got {self.quality}")
