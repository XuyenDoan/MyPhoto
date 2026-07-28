"""Builds output file paths for exported images."""

from __future__ import annotations

from pathlib import Path

from myphoto.export_engine.models import ExportFormat

_EXTENSION_FOR_FORMAT: dict[ExportFormat, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "tiff": ".tif",
}

#: Appended to every exported file's stem so an edited photo is visibly
#: distinguishable from its untouched source in the same folder.
EXPORT_SUFFIX = "_myphoto"


def extension_for_format(export_format: ExportFormat) -> str:
    return _EXTENSION_FOR_FORMAT[export_format]


def build_output_path(source_path: Path, output_dir: Path, export_format: ExportFormat) -> Path:
    """Resolve the destination path for one exported image."""
    stem = f"{source_path.stem}{EXPORT_SUFFIX}"
    return output_dir / f"{stem}{extension_for_format(export_format)}"
