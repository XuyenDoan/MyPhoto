"""Converts an :class:`ImageBuffer` to a displayable ``QImage``/``QPixmap``."""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage, QPixmap

from myphoto.core.image import ImageBuffer


def to_qimage(buffer: ImageBuffer) -> QImage:
    """Render ``buffer`` as an 8-bit RGB ``QImage`` for on-screen display.

    Display only needs 8 bits/channel regardless of the buffer's working
    precision; export uses the full-precision data directly.
    """
    rgb = np.clip(buffer.data[..., :3] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    rgb = np.ascontiguousarray(rgb)
    height, width, _ = rgb.shape
    image = QImage(rgb.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
    return image.copy()


def to_qpixmap(buffer: ImageBuffer) -> QPixmap:
    return QPixmap.fromImage(to_qimage(buffer))
