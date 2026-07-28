"""Writes an :class:`ImageBuffer` to disk as JPEG/PNG/TIFF.

JPEG is always written at 8 bits/channel (the format has no higher-depth
mode); EXIF and ICC profile are preserved via Pillow/piexif. PNG and TIFF
are written via OpenCV, at 16 bits/channel whenever the source had more
than 8 bits of precision, to satisfy the "no quality loss" priority —
Pillow cannot itself encode a 3-channel 16-bit image. That path trades away
EXIF/ICC embedding for 16-bit PNG/TIFF output; see docs/Architecture.md for
the reasoning and the future OpenImageIO/LittleCMS adapter this can grow
into.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import piexif

from myphoto.core.errors import ExportError
from myphoto.core.image import ImageBuffer
from myphoto.export_engine.models import ExportOptions
from myphoto.export_engine.naming import build_output_path
from myphoto.image_loader.exif_utils import EMPTY_EXIF


class ExportEngine:
    """Renders a processed :class:`ImageBuffer` to a JPEG/PNG/TIFF file."""

    def export(self, buffer: ImageBuffer, options: ExportOptions) -> Path:
        """Write ``buffer`` per ``options`` and return the path written to.

        Raises:
            ExportError: the resolved output path is the source image, or
                the underlying encoder fails.
        """
        output_path = build_output_path(buffer.source_path, options.output_dir, options.format)
        if output_path.resolve() == Path(buffer.source_path).resolve():
            raise ExportError(output_path, "export path must not overwrite the source image")

        options.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            if options.format == "jpeg":
                self._write_jpeg(buffer, output_path, options.quality)
            else:
                self._write_cv2(buffer, output_path)
        except OSError as exc:
            raise ExportError(output_path, str(exc)) from exc

        return output_path

    def _write_jpeg(self, buffer: ImageBuffer, path: Path, quality: int) -> None:
        from PIL import Image

        rgb = buffer.data[..., :3]
        array = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
        image = Image.fromarray(array, mode="RGB")

        save_kwargs: dict[str, object] = {"quality": quality}
        if buffer.icc_profile is not None:
            save_kwargs["icc_profile"] = buffer.icc_profile
        image.save(path, format="JPEG", **save_kwargs)

        if buffer.exif and buffer.exif != EMPTY_EXIF:
            try:
                piexif.insert(piexif.dump(buffer.exif), str(path))
            except Exception:  # noqa: BLE001, S110 - EXIF embedding is best-effort.
                pass

    def _write_cv2(self, buffer: ImageBuffer, path: Path) -> None:
        rgb = buffer.data[..., :3]
        bgr: np.ndarray
        if buffer.bit_depth > 8:
            bgr = np.clip(rgb * 65535.0 + 0.5, 0, 65535).astype(np.uint16)[..., ::-1]
        else:
            bgr = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)[..., ::-1]

        if not cv2.imwrite(str(path), bgr):
            raise ExportError(path, "OpenCV failed to write the image")
