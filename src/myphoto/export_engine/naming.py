"""Builds output file paths from an :class:`ExportOptions` rename pattern."""

from __future__ import annotations

from pathlib import Path

from myphoto.export_engine.models import ExportFormat

_EXTENSION_FOR_FORMAT: dict[ExportFormat, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "tiff": ".tif",
}


def extension_for_format(export_format: ExportFormat) -> str:
    return _EXTENSION_FOR_FORMAT[export_format]


def build_output_path(
    source_path: Path,
    output_dir: Path,
    rename_pattern: str,
    index: int,
    export_format: ExportFormat,
) -> Path:
    """Resolve the destination path for one exported image."""
    stem = rename_pattern.format(stem=source_path.stem, name=source_path.name, index=index)
    return output_dir / f"{stem}{extension_for_format(export_format)}"
