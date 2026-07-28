"""Downscaling for fast interactive preview rendering."""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer


def downscaled(buffer: ImageBuffer, max_dimension: int) -> ImageBuffer:
    """Return ``buffer`` resized so its longer side is at most ``max_dimension``.

    Returns ``buffer`` unchanged if it's already within the limit. Used to
    keep interactive preview renders fast regardless of the source image's
    (or RAW file's) full resolution; batch export always processes the
    full-resolution buffer.
    """
    longer_side = max(buffer.height, buffer.width)
    if longer_side <= max_dimension:
        return buffer

    scale = max_dimension / longer_side
    new_width = max(1, round(buffer.width * scale))
    new_height = max(1, round(buffer.height * scale))

    resized = cv2.resize(buffer.data, (new_width, new_height), interpolation=cv2.INTER_AREA)
    if resized.ndim == 2:
        resized = resized[:, :, np.newaxis]
    return replace(buffer, data=resized.astype(np.float32))
