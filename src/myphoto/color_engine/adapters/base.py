"""Adapter Pattern interface between the Color Engine and third-party color math.

Concrete adapters wrap a specific library (OpenCV today; OpenColorIO and
LittleCMS are documented future adapters — see docs/Architecture.md) so the
rest of the Color Engine never imports those libraries directly.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class ColorMath(Protocol):
    """Low-level color-space and resampling primitives the pipeline needs."""

    def rgb_to_hls(self, rgb: np.ndarray) -> np.ndarray:
        """Convert an ``(H, W, 3)`` float32 RGB array in ``[0, 1]`` to HLS."""
        ...

    def hls_to_rgb(self, hls: np.ndarray) -> np.ndarray:
        """Convert an ``(H, W, 3)`` float32 HLS array back to RGB in ``[0, 1]``."""
        ...

    def resize(self, array: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize a 2D or 3D float32 array to ``(height, width, ...)``."""
        ...
