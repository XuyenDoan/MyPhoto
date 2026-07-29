"""Local (per-region) exposure and saturation balancing.

Unlike the rest of the Color Pipeline — one global exposure/tone-curve/HSL
adjustment applied uniformly to the whole image — this looks at *where* a
photo is over/under-exposed or over-saturated and corrects each region on
its own. A bright sky and a shaded foreground in the same frame get pulled
toward balanced exposure independently, instead of one global slider that
can only compromise between the two.

Exposure technique: blur the luminance channel with a large-radius
Gaussian to estimate each region's *local* exposure level (the detail/
texture stays in the un-blurred original), then apply a per-pixel
multiplicative RGB gain — the same kind of operation the pipeline's
global `apply_exposure()` already uses (`rgb * 2**ev`), just spatially
varying instead of a single scalar. Scaling R/G/B together preserves hue
ratios exactly, unlike shifting HLS lightness while holding saturation
fixed — that seemed like the obvious approach at first, but HLS
saturation is lightness-relative, so pulling a near-white or near-black
pixel toward mid-gray while holding its HLS-S constant actually *increases*
its real chroma, which showed up as a visible, unwanted color cast on
supposedly neutral bright/dark regions during testing. Multiplicative RGB
gain doesn't have that failure mode.

Saturation technique: pull down (never up) any region whose *local*
saturation is unusually high, in HLS space, after the exposure pass.
One-directional deliberately: a region that's genuinely gray/neutral (a
wall, an overcast sky) isn't "under-saturated" in need of rescue — forcing
color into it would introduce a false tint, not fix anything.

This is a from-scratch, deterministic image-processing technique — not a
trained model, no network call, no cost.
"""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer

#: Regions whose local luminance sits far from this are nudged toward it.
_TARGET_LUMINANCE = 0.5

#: Regions whose local saturation exceeds this are pulled back down toward
#: it; regions below it are left alone (see module docstring).
_MAX_TARGET_SATURATION = 0.55

#: Gaussian blur radius as a fraction of the image's longer side — large
#: enough to capture "this whole area is blown out", not per-pixel noise.
_BLUR_SIGMA_FRACTION = 0.08

#: Multiplicative exposure gain is clamped to this range (~-1/+1.1 stops)
#: so this stays a corrective nudge rather than a heavy-handed rewrite.
_MIN_EXPOSURE_GAIN = 0.5
_MAX_EXPOSURE_GAIN = 2.2

#: Floor for local luminance before computing a gain ratio, so a
#: near-black region doesn't produce a runaway gain.
_MIN_LUMINANCE_FOR_GAIN = 0.03

_MAX_SATURATION_SHIFT = 0.4


def apply_local_balance(rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Return a corrected copy of ``rgb`` (``(H, W, 3)`` float32, values in ``[0, 1]``).

    ``strength`` scales the correction linearly; ``0.0`` returns ``rgb``
    unchanged (aside from a clip to ``[0, 1]``), ``1.0`` is the full effect.
    """
    if strength <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op

    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    sigma = max(rgb.shape[0], rgb.shape[1]) * _BLUR_SIGMA_FRACTION

    luminance = clipped[..., 0] * 0.2126 + clipped[..., 1] * 0.7152 + clipped[..., 2] * 0.0722
    local_luminance = cv2.GaussianBlur(luminance, (0, 0), sigma)

    raw_gain = _TARGET_LUMINANCE / np.maximum(local_luminance, _MIN_LUMINANCE_FOR_GAIN)
    gain = 1.0 + (raw_gain - 1.0) * strength
    gain = np.clip(gain, _MIN_EXPOSURE_GAIN, _MAX_EXPOSURE_GAIN)
    exposed = np.clip(clipped * gain[..., np.newaxis], 0.0, 1.0)

    hls = cv2.cvtColor(exposed, cv2.COLOR_RGB2HLS)
    saturation = hls[..., 2]
    local_saturation = cv2.GaussianBlur(saturation, (0, 0), sigma)

    excess = np.clip(local_saturation - _MAX_TARGET_SATURATION, 0.0, None)
    saturation_shift = np.clip(excess * strength, 0.0, _MAX_SATURATION_SHIFT)
    hls[..., 2] = np.clip(saturation - saturation_shift, 0.0, 1.0)

    result: np.ndarray = cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)
    return result


def apply_local_balance_to_buffer(buffer: ImageBuffer, strength: float = 1.0) -> ImageBuffer:
    """Apply :func:`apply_local_balance` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = apply_local_balance(buffer.data[..., :3], strength)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))
