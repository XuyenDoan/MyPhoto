"""Internal image representation shared by every pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ImageBuffer:
    """A decoded image in MyPhoto's internal working format.

    ``data`` is always a float32 array of shape ``(height, width, channels)``
    with values normalized to ``[0.0, 1.0]``, regardless of the source file's
    bit depth. Downstream pipeline stages (white balance, tone curve, film
    simulation, ...) operate on this normalized representation; the original
    bit depth is kept in ``bit_depth`` so the Export Engine can choose an
    appropriate output precision.
    """

    data: np.ndarray
    source_path: Path
    color_space: str
    bit_depth: int
    is_raw: bool
    icc_profile: bytes | None = None
    exif: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.data.ndim != 3:
            raise ValueError(
                f"ImageBuffer.data must have shape (H, W, C), got {self.data.shape}"
            )
        if self.data.dtype != np.float32:
            raise ValueError(f"ImageBuffer.data must be float32, got {self.data.dtype}")
        if self.bit_depth <= 0:
            raise ValueError(f"bit_depth must be positive, got {self.bit_depth}")

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def channels(self) -> int:
        return int(self.data.shape[2])
