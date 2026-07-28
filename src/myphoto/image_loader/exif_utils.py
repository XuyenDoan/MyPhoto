"""Best-effort EXIF extraction, kept in piexif's native IFD structure.

Round-tripping EXIF through the Export Engine requires the tag-id-keyed
structure :func:`piexif.dump`/:func:`piexif.insert` expect, not a
human-readable flattened dict — so :func:`extract_exif` returns that
structure directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import piexif

#: A valid-but-empty EXIF structure, used when a file has no EXIF to read.
EMPTY_EXIF: dict[str, Any] = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}


def extract_exif(path: Path) -> dict[str, Any]:
    """Read EXIF metadata from ``path`` as a piexif-compatible IFD dict.

    Only JPEG and TIFF files carry EXIF that :mod:`piexif` can parse. Any
    other format, or a file with no EXIF block, yields an empty structure
    rather than raising — EXIF is best-effort metadata, not something a
    load should fail over.
    """
    try:
        raw_exif: dict[str, Any] = piexif.load(str(path))
    except Exception:  # noqa: BLE001 - piexif raises undocumented types for non-EXIF files.
        return dict(EMPTY_EXIF)
    return raw_exif


def normalize_orientation(exif: dict[str, Any]) -> None:
    """Reset the Orientation tag to 1 (normal), in place.

    Call this after the pixel data has already been physically rotated to
    match the original Orientation tag (see
    ``image_loader.loader._load_raster``) — otherwise re-exporting this
    EXIF as-is would tell viewers to rotate an image that's already
    right-side up, flipping/rotating it a second time.
    """
    if piexif.ImageIFD.Orientation in exif.get("0th", {}):
        exif["0th"][piexif.ImageIFD.Orientation] = 1
