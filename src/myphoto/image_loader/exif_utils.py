"""Best-effort EXIF extraction so the Export Engine can preserve it later."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import piexif


def extract_exif(path: Path) -> dict[str, Any]:
    """Read EXIF metadata from ``path`` as a flat ``{tag_name: value}`` dict.

    Only JPEG and TIFF files carry EXIF that :mod:`piexif` can parse. Any
    other format, or a file with no EXIF block, yields an empty dict rather
    than raising — EXIF is best-effort metadata, not something a load should
    fail over.
    """
    try:
        raw_exif = piexif.load(str(path))
    except Exception:  # noqa: BLE001 - piexif raises undocumented types for non-EXIF files.
        return {}

    result: dict[str, Any] = {}
    for ifd_name in ("0th", "Exif", "GPS", "1st"):
        ifd = raw_exif.get(ifd_name)
        if not ifd:
            continue
        tag_table = piexif.TAGS.get(ifd_name, {})
        for tag_id, value in ifd.items():
            tag_name = tag_table.get(tag_id, {}).get("name", str(tag_id))
            result[tag_name] = _decode_value(value)
    return result


def _decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("ascii").rstrip("\x00")
        except UnicodeDecodeError:
            return value
    return value
