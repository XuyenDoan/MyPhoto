from pathlib import Path

import numpy as np

from myphoto.color_engine.local_adjust import apply_local_balance, apply_local_balance_to_buffer
from myphoto.core.image import ImageBuffer


def _region_image(bright: float, dark: float, size: int = 64) -> np.ndarray:
    """A left/right split image: left half ``bright``, right half ``dark`` (all channels equal)."""
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = bright
    rgb[:, size // 2 :] = dark
    return rgb


def test_overexposed_region_gets_darkened_and_underexposed_gets_brightened() -> None:
    rgb = _region_image(bright=0.95, dark=0.05)

    result = apply_local_balance(rgb, strength=1.0)

    bright_half = result[:, :32]
    dark_half = result[:, 32:]
    assert bright_half.mean() < rgb[:, :32].mean()
    assert dark_half.mean() > rgb[:, 32:].mean()


def test_well_exposed_midtone_region_is_left_alone() -> None:
    rgb = np.full((32, 32, 3), 0.5, dtype=np.float32)

    result = apply_local_balance(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_zero_strength_is_a_no_op() -> None:
    rgb = _region_image(bright=0.9, dark=0.1)

    result = apply_local_balance(rgb, strength=0.0)

    assert np.allclose(result, rgb, atol=1e-4)


def test_oversaturated_region_gets_desaturated() -> None:
    size = 64
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = (1.0, 0.0, 0.0)  # fully saturated red, left half
    rgb[:, size // 2 :] = (0.5, 0.5, 0.5)  # neutral gray, right half

    result = apply_local_balance(rgb, strength=1.0)

    def chroma(region: np.ndarray) -> float:
        return float((region.max(axis=-1) - region.min(axis=-1)).mean())

    assert chroma(result[:, :32]) < chroma(rgb[:, :32])


def test_apply_local_balance_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [_region_image(bright=0.9, dark=0.1), np.full((64, 64, 1), 0.7, dtype=np.float32)], axis=-1
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_local_balance_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.7)
    assert result.source_path == buffer.source_path
    assert not np.allclose(result.data[..., :3], buffer.data[..., :3])
