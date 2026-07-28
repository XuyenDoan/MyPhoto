"""Decodes JPEG/PNG/TIFF/BMP/RAW files into the internal ImageBuffer format."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

from myphoto.core.errors import ImageDecodeError, UnsupportedFormatError
from myphoto.core.image import ImageBuffer
from myphoto.image_loader.exif_utils import extract_exif
from myphoto.image_loader.formats import is_raster, is_raw

#: 16-bit-per-channel Pillow modes produced by TIFF/PNG decoding.
_SIXTEEN_BIT_MODES = ("I;16", "I;16B", "I;16L", "I")


class ImageLoader:
    """Reads a supported image file from disk into an :class:`ImageBuffer`.

    RAW files are decoded via ``rawpy``/LibRaw using the camera's as-shot
    white balance and a linear (gamma 1.0) response, so later Color Engine
    stages (White Balance, Exposure, Tone Curve, ...) start from a neutral,
    minimally-processed buffer rather than an already tone-mapped JPEG-like
    render. Standard raster formats are decoded via Pillow.
    """

    def load(self, path: Path | str) -> ImageBuffer:
        """Decode ``path`` into an :class:`ImageBuffer`.

        Raises:
            FileNotFoundError: ``path`` does not exist.
            UnsupportedFormatError: the file extension is not recognized.
            ImageDecodeError: the file is recognized but fails to decode.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        if is_raw(path):
            return self._load_raw(path)
        if is_raster(path):
            return self._load_raster(path)
        raise UnsupportedFormatError(path)

    def _load_raster(self, path: Path) -> ImageBuffer:
        try:
            with Image.open(path) as img:
                img.load()
                icc_profile: bytes | None = img.info.get("icc_profile")
                data, bit_depth = _pillow_image_to_array(img)
        except UnsupportedFormatError:
            raise
        except Exception as exc:  # Pillow raises many different exception types.
            raise ImageDecodeError(path, str(exc)) from exc

        return ImageBuffer(
            data=data,
            source_path=path,
            color_space="sRGB",
            bit_depth=bit_depth,
            is_raw=False,
            icc_profile=icc_profile,
            exif=extract_exif(path),
        )

    def _load_raw(self, path: Path) -> ImageBuffer:
        try:
            with rawpy.imread(str(path)) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=True,
                    output_bps=16,
                    gamma=(1.0, 1.0),
                    output_color=rawpy.ColorSpace.sRGB,  # type: ignore[attr-defined]
                )
        except Exception as exc:
            raise ImageDecodeError(path, str(exc)) from exc

        data = rgb.astype(np.float32) / 65535.0
        return ImageBuffer(
            data=data,
            source_path=path,
            color_space="sRGB-linear",
            bit_depth=16,
            is_raw=True,
            icc_profile=None,
            exif=extract_exif(path),
        )


def _pillow_image_to_array(img: Image.Image) -> tuple[np.ndarray, int]:
    """Convert a loaded Pillow image to a normalized ``(H, W, C)`` float32 array."""
    if img.mode in _SIXTEEN_BIT_MODES:
        array = np.asarray(img, dtype=np.int32).astype(np.float32)
        max_value = 65535.0
        bit_depth = 16
    else:
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            img = img.convert("RGB")
        array = np.asarray(img, dtype=np.uint8).astype(np.float32)
        max_value = 255.0
        bit_depth = 8

    if array.ndim == 2:
        array = array[:, :, np.newaxis]
    return array / max_value, bit_depth
