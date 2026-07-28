"""OpenCV-backed implementation of :class:`ColorMath`."""

from __future__ import annotations

import cv2
import numpy as np


class OpenCVColorMath:
    """Concrete :class:`~myphoto.color_engine.adapters.base.ColorMath` using OpenCV."""

    def rgb_to_hls(self, rgb: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(np.ascontiguousarray(rgb, dtype=np.float32), cv2.COLOR_RGB2HLS)

    def hls_to_rgb(self, hls: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(np.ascontiguousarray(hls, dtype=np.float32), cv2.COLOR_HLS2RGB)

    def resize(self, array: np.ndarray, width: int, height: int) -> np.ndarray:
        interpolation = cv2.INTER_AREA if width * height < array.shape[0] * array.shape[1] else cv2.INTER_LINEAR
        resized = cv2.resize(array, (width, height), interpolation=interpolation)
        if array.ndim == 3 and resized.ndim == 2:
            resized = resized[:, :, np.newaxis]
        return resized
