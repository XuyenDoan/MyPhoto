"""Loads standard and RAW image formats into the internal image representation."""

from myphoto.image_loader.formats import (
    RASTER_EXTENSIONS,
    RAW_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    is_raster,
    is_raw,
    is_supported,
)
from myphoto.image_loader.loader import ImageLoader

__all__ = [
    "RASTER_EXTENSIONS",
    "RAW_EXTENSIONS",
    "SUPPORTED_EXTENSIONS",
    "ImageLoader",
    "is_raster",
    "is_raw",
    "is_supported",
]
