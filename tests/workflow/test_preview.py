from pathlib import Path

import numpy as np

from myphoto.core.image import ImageBuffer
from myphoto.workflow.preview import downscaled


def _buffer(height: int, width: int) -> ImageBuffer:
    data = np.random.default_rng(0).random((height, width, 3)).astype(np.float32)
    return ImageBuffer(
        data=data, source_path=Path("x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )


def test_leaves_small_images_unchanged() -> None:
    buffer = _buffer(100, 200)
    assert downscaled(buffer, 1600) is buffer


def test_shrinks_large_images_preserving_aspect_ratio() -> None:
    buffer = _buffer(2000, 4000)
    result = downscaled(buffer, 1600)
    assert result.width == 1600
    assert result.height == 800
