"""Shared domain types (image buffers, color spaces, pipeline contracts)."""

from myphoto.core.errors import ImageDecodeError, MyPhotoError, UnsupportedFormatError
from myphoto.core.image import ImageBuffer

__all__ = [
    "ImageBuffer",
    "ImageDecodeError",
    "MyPhotoError",
    "UnsupportedFormatError",
]
