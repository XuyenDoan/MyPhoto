from pathlib import Path

import numpy as np

from myphoto.color_engine.sharpen import apply_sharpen, apply_sharpen_to_buffer
from myphoto.core.image import ImageBuffer


def _edge_image(size: int = 64) -> np.ndarray:
    """A sharp light/dark step edge down the middle — genuine detail to sharpen."""
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = 0.8
    rgb[:, size // 2 :] = 0.2
    return rgb


def test_sharp_edge_gets_more_contrast() -> None:
    rgb = _edge_image()

    result = apply_sharpen(rgb, amount=1.0)

    # Right at the edge, sharpening should push the bright side brighter
    # and the dark side darker (a stronger step), not flatten it.
    edge_col = rgb.shape[1] // 2
    bright_before = rgb[:, edge_col - 2].mean()
    bright_after = result[:, edge_col - 2].mean()
    dark_before = rgb[:, edge_col + 1].mean()
    dark_after = result[:, edge_col + 1].mean()
    assert bright_after >= bright_before
    assert dark_after <= dark_before
    assert (bright_after - dark_after) >= (bright_before - dark_before)


def test_low_amplitude_noise_is_not_amplified() -> None:
    # Simulates fine film grain: small-amplitude, spatially incoherent
    # variation on an otherwise flat midtone region.
    rng = np.random.default_rng(0)
    size = 64
    flat = np.full((size, size, 3), 0.5, dtype=np.float32)
    noise = rng.normal(0.0, 0.01, size=(size, size, 1)).astype(np.float32)
    grainy = np.clip(flat + noise, 0.0, 1.0)

    result = apply_sharpen(grainy, amount=1.0)

    # The noise-threshold should leave this essentially untouched, not
    # amplify its variance.
    assert np.std(result) <= np.std(grainy) * 1.2


def test_zero_amount_is_a_no_op() -> None:
    rgb = _edge_image()

    result = apply_sharpen(rgb, amount=0.0)

    assert np.allclose(result, rgb, atol=1e-4)


def test_apply_sharpen_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [_edge_image(), np.full((64, 64, 1), 0.6, dtype=np.float32)], axis=-1
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_sharpen_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.6)
    assert result.source_path == buffer.source_path
