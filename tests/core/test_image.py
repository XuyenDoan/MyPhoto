from pathlib import Path

import numpy as np
import pytest

from myphoto.core.image import ImageBuffer


def _buffer(**overrides) -> ImageBuffer:
    defaults = {
        "data": np.zeros((4, 5, 3), dtype=np.float32),
        "source_path": Path("dummy.png"),
        "color_space": "sRGB",
        "bit_depth": 8,
        "is_raw": False,
    }
    defaults.update(overrides)
    return ImageBuffer(**defaults)


def test_dimensions_reflect_array_shape() -> None:
    buf = _buffer(data=np.zeros((10, 20, 3), dtype=np.float32))
    assert buf.height == 10
    assert buf.width == 20
    assert buf.channels == 3


def test_rejects_non_float32_data() -> None:
    with pytest.raises(ValueError, match="float32"):
        _buffer(data=np.zeros((4, 5, 3), dtype=np.uint8))


def test_rejects_wrong_ndim() -> None:
    with pytest.raises(ValueError, match="H, W, C"):
        _buffer(data=np.zeros((4, 5), dtype=np.float32))


def test_rejects_non_positive_bit_depth() -> None:
    with pytest.raises(ValueError, match="bit_depth"):
        _buffer(bit_depth=0)
