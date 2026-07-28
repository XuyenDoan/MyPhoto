"""Exceptions shared across MyPhoto's engines."""

from __future__ import annotations

from pathlib import Path


class MyPhotoError(Exception):
    """Base class for all MyPhoto-specific exceptions."""


class UnsupportedFormatError(MyPhotoError):
    """Raised when a file extension is not a format MyPhoto can read."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Unsupported image format: {path.suffix!r} ({path})")


class ImageDecodeError(MyPhotoError):
    """Raised when a supported file fails to decode (corrupt or unreadable)."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to decode image {path}: {reason}")
