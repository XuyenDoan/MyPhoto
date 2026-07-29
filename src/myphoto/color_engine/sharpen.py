"""Noise-aware capture sharpening (unsharp masking).

Standard unsharp mask technique: blur the image, subtract the blur from
the original to isolate "detail" (high-frequency content), then add that
detail back in, amplified. The one refinement that matters here: detail
is only added back where its *magnitude* exceeds a small threshold
(`_DETAIL_THRESHOLD`). Film grain (added by some Film Simulation presets)
and sensor noise are both low-amplitude, spatially incoherent detail —
without a threshold, unsharp masking amplifies them right along with
genuine edges, making a grainy photo look noisier rather than sharper.
Real edges (a subject's outline, in-focus texture) have much larger
local contrast and clear the threshold; grain mostly doesn't. This is
the same "threshold" control found in Lightroom/Photoshop's sharpening
tools, applied here as a smooth ramp rather than a hard cutoff to avoid
a visible transition.

Runs last in the pipeline, after the Film Simulation preset (including
its grain) and the post-preset guard — sharpening the final tonal/color
result rather than the pre-preset source, which is the conventional
"output sharpening" order.

Deterministic image processing — not a trained model, no network call,
no cost.
"""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer

#: Blur radius as a fraction of the image's longer side. Deliberately much
#: smaller than the correction passes in local_adjust.py (which look at
#: broad regions) — sharpening cares about fine detail, not large areas.
_BLUR_SIGMA_FRACTION = 0.0018

#: Detail below this magnitude (out of 1.0) is treated as noise/grain and
#: left alone; detail above it is sharpened at full strength. The ramp
#: between the two avoids a visible threshold edge.
_DETAIL_THRESHOLD = 0.02
_DETAIL_THRESHOLD_RAMP = 0.015

#: Caps how much amplification a single pass can apply, so this stays a
#: capture-sharpening pass rather than an aggressive, halo-prone effect.
_MAX_AMOUNT = 1.5


def apply_sharpen(rgb: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Return a sharpened copy of ``rgb`` (``(H, W, 3)`` float32, values in ``[0, 1]``).

    ``amount`` scales the effect linearly, capped at ``_MAX_AMOUNT``;
    ``0.0`` returns ``rgb`` unchanged (aside from a clip to ``[0, 1]``).
    """
    amount = max(0.0, min(amount, _MAX_AMOUNT))
    if amount <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op

    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    sigma = max(rgb.shape[0], rgb.shape[1]) * _BLUR_SIGMA_FRACTION
    blurred = cv2.GaussianBlur(clipped, (0, 0), sigma)
    detail = clipped - blurred

    detail_magnitude = np.abs(detail).max(axis=-1)
    mask = np.clip((detail_magnitude - _DETAIL_THRESHOLD) / _DETAIL_THRESHOLD_RAMP, 0.0, 1.0)

    result: np.ndarray = np.clip(clipped + detail * amount * mask[..., np.newaxis], 0.0, 1.0)
    return result


def apply_sharpen_to_buffer(buffer: ImageBuffer, amount: float = 1.0) -> ImageBuffer:
    """Apply :func:`apply_sharpen` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = apply_sharpen(buffer.data[..., :3], amount)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))
