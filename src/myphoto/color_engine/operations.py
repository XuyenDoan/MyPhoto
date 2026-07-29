"""Pure, individually testable Color Pipeline operations.

Every function takes and returns an ``(H, W, 3)`` float32 RGB array with
values nominally in ``[0, 1]`` (intermediate stages may briefly exceed that
range before the final clip). None of these functions mutate their input.
"""

from __future__ import annotations

import numpy as np

from myphoto.color_engine.adapters.base import ColorMath
from myphoto.color_engine.adjustments import ColorBalanceAdjustment, Curve


def apply_white_balance(rgb: np.ndarray, temp: float, tint: float) -> np.ndarray:
    """Approximate a temperature/tint white-balance shift via per-channel gain."""
    r_gain = 1.0 + 0.35 * temp + 0.15 * tint
    g_gain = 1.0 - 0.25 * tint
    b_gain = 1.0 - 0.35 * temp + 0.15 * tint
    gains = np.array([r_gain, g_gain, b_gain], dtype=np.float32)
    return rgb * gains


def apply_exposure(rgb: np.ndarray, exposure_ev: float) -> np.ndarray:
    """Scale linear brightness by ``2 ** exposure_ev`` stops."""
    return rgb * np.float32(2.0**exposure_ev)


def apply_curve(rgb: np.ndarray, curve: Curve) -> np.ndarray:
    """Apply the same tone curve to every channel via piecewise-linear interpolation."""
    xs = np.array([p[0] for p in curve], dtype=np.float32)
    ys = np.array([p[1] for p in curve], dtype=np.float32)
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    result: np.ndarray = np.interp(rgb, xs, ys).astype(np.float32)
    return result


def apply_rgb_curves(rgb: np.ndarray, red: Curve, green: Curve, blue: Curve) -> np.ndarray:
    """Apply independent tone curves to the red, green, and blue channels."""
    out = np.empty_like(rgb)
    out[..., 0] = apply_curve(rgb[..., 0], red)
    out[..., 1] = apply_curve(rgb[..., 1], green)
    out[..., 2] = apply_curve(rgb[..., 2], blue)
    return out


def apply_hsl(
    rgb: np.ndarray,
    hue_shift_degrees: float,
    saturation_scale: float,
    lightness_scale: float,
    color_math: ColorMath,
) -> np.ndarray:
    """Shift hue and scale saturation/lightness in HLS space."""
    if hue_shift_degrees == 0.0 and saturation_scale == 1.0 and lightness_scale == 1.0:
        return rgb
    hls = color_math.rgb_to_hls(np.clip(rgb, 0.0, 1.0))
    hls[..., 0] = (hls[..., 0] + hue_shift_degrees) % 360.0
    hls[..., 1] = np.clip(hls[..., 1] * lightness_scale, 0.0, 1.0)
    hls[..., 2] = np.clip(hls[..., 2] * saturation_scale, 0.0, 1.0)
    return color_math.hls_to_rgb(hls)


def apply_color_balance(rgb: np.ndarray, adjustment: ColorBalanceAdjustment) -> np.ndarray:
    """Add a per-zone RGB offset, weighted by shadow/midtone/highlight luminance."""
    if adjustment.shadows == adjustment.midtones == adjustment.highlights == (0.0, 0.0, 0.0):
        return rgb
    luminance = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    shadow_w = np.clip(1.0 - luminance * 2.0, 0.0, 1.0)[..., np.newaxis]
    highlight_w = np.clip(luminance * 2.0 - 1.0, 0.0, 1.0)[..., np.newaxis]
    midtone_w = np.clip(1.0 - shadow_w - highlight_w, 0.0, 1.0)

    shadows = np.array(adjustment.shadows, dtype=np.float32)
    midtones = np.array(adjustment.midtones, dtype=np.float32)
    highlights = np.array(adjustment.highlights, dtype=np.float32)

    offset = shadow_w * shadows + midtone_w * midtones + highlight_w * highlights
    return rgb + offset


def apply_film_grain(
    rgb: np.ndarray,
    amount: float,
    size: float,
    color_math: ColorMath,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Add luminance-only Gaussian grain, generated at a coarser resolution for ``size`` > 1."""
    if amount <= 0.0:
        return rgb
    generator = rng if rng is not None else np.random.default_rng()
    height, width = rgb.shape[:2]
    small_height = max(1, round(height / max(size, 1.0)))
    small_width = max(1, round(width / max(size, 1.0)))
    noise = generator.normal(0.0, 1.0, size=(small_height, small_width, 1)).astype(np.float32)
    if (small_height, small_width) != (height, width):
        noise = color_math.resize(noise, width, height)
        if noise.ndim == 2:
            noise = noise[..., np.newaxis]
    result: np.ndarray = rgb + noise * np.float32(amount * 0.08)
    return result


#: Trilinear interpolation needs 8 full-size gathered-color arrays live at
#: once (the 8 corners of the LUT cube surrounding each pixel) — computed
#: over a whole high-resolution photo at once, that's a lot of peak memory
#: for a step that's otherwise perfectly row-independent. Processing in
#: row-band tiles bounds peak memory to roughly this many pixels' worth of
#: those 8 arrays, regardless of the source photo's resolution, with the
#: exact same math and result (just computed in pieces).
_LUT_TILE_MAX_PIXELS = 400_000


def _apply_3d_lut_tile(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    size = lut.shape[0]
    scaled = np.clip(rgb, 0.0, 1.0) * (size - 1)
    idx0 = np.floor(scaled).astype(np.int32)
    idx1 = np.clip(idx0 + 1, 0, size - 1)
    frac = (scaled - idx0).astype(np.float32)

    r0, g0, b0 = idx0[..., 0], idx0[..., 1], idx0[..., 2]
    r1, g1, b1 = idx1[..., 0], idx1[..., 1], idx1[..., 2]
    fr, fg, fb = frac[..., 0:1], frac[..., 1:2], frac[..., 2:3]

    c000, c001 = lut[r0, g0, b0], lut[r0, g0, b1]
    c010, c011 = lut[r0, g1, b0], lut[r0, g1, b1]
    c100, c101 = lut[r1, g0, b0], lut[r1, g0, b1]
    c110, c111 = lut[r1, g1, b0], lut[r1, g1, b1]

    c00 = c000 * (1 - fb) + c001 * fb
    c01 = c010 * (1 - fb) + c011 * fb
    c10 = c100 * (1 - fb) + c101 * fb
    c11 = c110 * (1 - fb) + c111 * fb

    c0 = c00 * (1 - fg) + c01 * fg
    c1 = c10 * (1 - fg) + c11 * fg

    result: np.ndarray = (c0 * (1 - fr) + c1 * fr).astype(np.float32)
    return result


def apply_3d_lut(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Apply an ``(N, N, N, 3)`` 3D LUT to ``rgb`` via trilinear interpolation.

    Processed in horizontal row-band tiles (see ``_LUT_TILE_MAX_PIXELS``)
    to bound peak memory on a high-resolution photo; the math and result
    are identical to processing the whole image at once.
    """
    height, width = rgb.shape[:2]
    tile_rows = max(1, _LUT_TILE_MAX_PIXELS // max(width, 1))
    if tile_rows >= height:
        return _apply_3d_lut_tile(rgb, lut)

    tiles = [_apply_3d_lut_tile(rgb[row : row + tile_rows], lut) for row in range(0, height, tile_rows)]
    result: np.ndarray = np.concatenate(tiles, axis=0)
    return result


def identity_lut(size: int = 17) -> np.ndarray:
    """Build a neutral (pass-through) ``(size, size, size, 3)`` 3D LUT, mainly for tests."""
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)
    r, g, b = np.meshgrid(ramp, ramp, ramp, indexing="ij")
    return np.stack([r, g, b], axis=-1).astype(np.float32)
