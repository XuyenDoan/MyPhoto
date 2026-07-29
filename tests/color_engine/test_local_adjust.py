from pathlib import Path

import numpy as np

from myphoto.color_engine.local_adjust import (
    _BLUR_DOWNSAMPLE_MAX_DIM,
    _large_blur,
    apply_exposure_guard,
    apply_local_balance,
    apply_local_balance_to_buffer,
    apply_post_preset_guard_to_buffer,
    apply_saturation_guard,
    apply_saturation_guard_to_buffer,
)
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


def test_warm_color_cast_is_neutralized() -> None:
    # A uniform warm (orange-ish) cast across the whole photo, as if lit by
    # incandescent bulbs — gray-world should pull the channel means together.
    rgb = np.full((32, 32, 3), 0.5, dtype=np.float32)
    rgb[..., 0] = 0.65  # red channel biased high
    rgb[..., 2] = 0.35  # blue channel biased low

    result = apply_local_balance(rgb, strength=1.0)

    means = result.reshape(-1, 3).mean(axis=0)
    original_spread = float(rgb.reshape(-1, 3).mean(axis=0).max() - rgb.reshape(-1, 3).mean(axis=0).min())
    corrected_spread = float(means.max() - means.min())
    assert corrected_spread < original_spread


def test_saturation_guard_pulls_down_blown_chroma() -> None:
    size = 64
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = (1.0, 0.0, 0.05)  # fully saturated, left half
    rgb[:, size // 2 :] = (0.5, 0.4, 0.6)  # moderately saturated, right half

    result = apply_saturation_guard(rgb, strength=1.0)

    def sat(region: np.ndarray) -> float:
        return float((region.max(axis=-1) - region.min(axis=-1)).mean())

    assert sat(result[:, :32]) < sat(rgb[:, :32])


def test_saturation_guard_leaves_a_vivid_but_not_blown_preset_look_alone() -> None:
    # A moderately vivid, tonally-varied region — the kind a Film Simulation
    # preset like Velvia is *meant* to produce — must not be flattened.
    rgb = np.full((32, 32, 3), (0.5, 0.4, 0.6), dtype=np.float32)

    result = apply_saturation_guard(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_apply_saturation_guard_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [
            np.tile(np.array([1.0, 0.0, 0.05], dtype=np.float32), (64, 64, 1)),
            np.full((64, 64, 1), 0.7, dtype=np.float32),
        ],
        axis=-1,
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_saturation_guard_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.7)
    assert result.source_path == buffer.source_path
    assert not np.allclose(result.data[..., :3], buffer.data[..., :3])


def test_exposure_guard_recovers_fully_clipped_highlight() -> None:
    rgb = _region_image(bright=0.995, dark=0.5)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert result[:, :32].mean() < rgb[:, :32].mean()


def test_exposure_guard_recovers_fully_blocked_shadow() -> None:
    rgb = _region_image(bright=0.5, dark=0.005)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert result[:, 32:].mean() > rgb[:, 32:].mean()


def test_exposure_guard_leaves_a_normal_contrast_range_alone() -> None:
    # Within [_POST_PRESET_SHADOW_FLOOR, _POST_PRESET_HIGHLIGHT_CEILING] —
    # a preset's normal punchy-but-not-clipped contrast must be untouched.
    rgb = _region_image(bright=0.85, dark=0.15)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_post_preset_guard_combines_exposure_and_saturation_fixes() -> None:
    size = 64
    data = np.zeros((size, size, 3), dtype=np.float32)
    data[:, : size // 2] = (0.995, 0.995, 0.995)  # clipped highlight, left half
    data[:, size // 2 :] = (1.0, 0.0, 0.05)  # blown chroma, right half
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_post_preset_guard_to_buffer(buffer)

    assert result.data[:, :32].mean() < data[:, :32].mean()
    right = result.data[:, 32:]
    assert (right.max(axis=-1) - right.min(axis=-1)).mean() < (
        data[:, 32:].max(axis=-1) - data[:, 32:].min(axis=-1)
    ).mean()


def test_large_blur_downsample_path_matches_full_res_blur_closely() -> None:
    # A map bigger than the downsample threshold should take the
    # downsample-blur-upsample path but still produce essentially the same
    # broad-region result as blurring at full resolution directly.
    size = _BLUR_DOWNSAMPLE_MAX_DIM + 200
    rng = np.random.default_rng(0)
    single_channel = _region_image(bright=0.9, dark=0.1, size=size)[..., 0]
    single_channel = single_channel + rng.normal(0.0, 0.01, size=single_channel.shape).astype(np.float32)

    import cv2

    sigma = size * 0.08
    exact = cv2.GaussianBlur(single_channel, (0, 0), sigma)
    fast = _large_blur(single_channel, sigma)

    assert fast.shape == exact.shape
    assert np.abs(fast - exact).mean() < 0.01


def test_large_blur_small_image_matches_direct_gaussian_blur_exactly() -> None:
    import cv2

    single_channel = _region_image(bright=0.8, dark=0.2, size=64)[..., 0]
    sigma = 5.0

    exact = cv2.GaussianBlur(single_channel, (0, 0), sigma)
    fast = _large_blur(single_channel, sigma)

    assert np.allclose(fast, exact)


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
