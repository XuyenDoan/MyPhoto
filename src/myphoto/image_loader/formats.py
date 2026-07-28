"""Recognized file extensions for raster and RAW image formats."""

from __future__ import annotations

from pathlib import Path

#: Formats decoded directly via Pillow.
RASTER_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
)

#: RAW formats decoded via rawpy/LibRaw.
RAW_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".raw", ".dng", ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
        ".raf", ".orf", ".rw2", ".pef", ".srw", ".rwl", ".x3f", ".3fr", ".erf",
        ".mef", ".mrw", ".iiq",
    }
)

SUPPORTED_EXTENSIONS: frozenset[str] = RASTER_EXTENSIONS | RAW_EXTENSIONS


def is_raw(path: Path | str) -> bool:
    """Return True if ``path``'s extension is a supported RAW format."""
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def is_raster(path: Path | str) -> bool:
    """Return True if ``path``'s extension is a supported non-RAW raster format."""
    return Path(path).suffix.lower() in RASTER_EXTENSIONS


def is_supported(path: Path | str) -> bool:
    """Return True if ``path``'s extension is any format MyPhoto can load."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS
