from pathlib import Path

import numpy as np
import pytest

from myphoto.color_engine.adjustments import ColorAdjustments
from myphoto.color_engine.pipeline import ColorPipeline
from myphoto.core.image import ImageBuffer


def _buffer(channels: int = 3, size: int = 6) -> ImageBuffer:
    rng = np.random.default_rng(1)
    data = rng.random((size, size, channels)).astype(np.float32)
    return ImageBuffer(
        data=data,
        source_path=Path("dummy.png"),
        color_space="sRGB",
        bit_depth=8,
        is_raw=False,
    )


def test_identity_adjustments_leave_image_nearly_unchanged() -> None:
    buffer = _buffer()
    result = ColorPipeline().process(buffer, ColorAdjustments(), rng=np.random.default_rng(0))
    np.testing.assert_allclose(result.data, buffer.data, atol=1e-5)


def test_rgba_alpha_channel_passes_through_untouched() -> None:
    buffer = _buffer(channels=4)
    adjustments = ColorAdjustments(exposure_ev=2.0)
    result = ColorPipeline().process(buffer, adjustments)
    np.testing.assert_allclose(result.data[..., 3], buffer.data[..., 3])
    assert not np.allclose(result.data[..., :3], buffer.data[..., :3])


def test_output_is_clipped_to_unit_range() -> None:
    buffer = _buffer()
    adjustments = ColorAdjustments(exposure_ev=5.0)
    result = ColorPipeline().process(buffer, adjustments)
    assert result.data.min() >= 0.0
    assert result.data.max() <= 1.0


def test_rejects_unsupported_channel_count() -> None:
    buffer = _buffer(channels=1)
    with pytest.raises(ValueError, match="RGB or RGBA"):
        ColorPipeline().process(buffer, ColorAdjustments())


def test_preserves_buffer_metadata() -> None:
    buffer = _buffer()
    result = ColorPipeline().process(buffer, ColorAdjustments(exposure_ev=0.5))
    assert result.source_path == buffer.source_path
    assert result.color_space == buffer.color_space
    assert result.bit_depth == buffer.bit_depth
    assert result.is_raw == buffer.is_raw
