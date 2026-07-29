"""Purple/green fringe removal (chromatic aberration defringe).

Lateral chromatic aberration — a real lens defect, worse at a frame's
edges and in high-contrast areas (a dark branch against a bright sky) —
shows up as a thin colored fringe (usually purple/magenta or green) along
strong edges, where the lens focused red/green/blue slightly differently.
Judges in international competitions do notice it; it reads as a
technical flaw rather than a stylistic choice.

This implements *color-based defringing*, not full geometric lateral-CA
correction (which would resample the R and B channels at a slightly
different radial scale, estimated per-photo — a heavier, harder-to-verify
technique). Defringing is simpler and safer to apply automatically: find
strong-contrast edges (a Sobel gradient magnitude), and at those edges
only, desaturate the specific purple (R and B both elevated over G) or
green (G elevated over R and B) cast toward neutral. Everywhere else —
flat regions, legitimately purple or green *subject matter* away from a
high-contrast edge — is left untouched, so this can't mistake a purple
flower or green leaf for a lens defect.

Deterministic image processing — not a trained model, no network call,
no cost.
"""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer

#: Gradient-magnitude percentile above which a pixel counts as "a strong
#: edge" — defringing only ever touches these, never flat/low-contrast
#: regions.
_EDGE_PERCENTILE = 92.0

#: Caps how much of the detected fringe is removed, so this stays a
#: correction rather than desaturating real color near edges.
_MAX_DEFRINGE_SHIFT = 0.5

#: The "what counts as a strong edge" threshold is already a heuristic
#: cutoff, not a value that needs pixel-exact precision — estimating it
#: from a random subsample instead of every pixel avoids an expensive
#: full-image sort (``np.percentile``'s cost) on a high-resolution photo,
#: with no measurable change in behavior.
_PERCENTILE_SAMPLE_SIZE = 200_000


def correct_chromatic_aberration(rgb: np.ndarray, amount: float = 1.0) -> np.ndarray:
    """Return a defringed copy of ``rgb`` (``(H, W, 3)`` float32, values in ``[0, 1]``).

    ``amount`` scales the effect linearly; ``0.0`` returns ``rgb``
    unchanged (aside from a clip to ``[0, 1]``), ``1.0`` is the full effect.
    """
    if amount <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op

    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    r, g, b = clipped[..., 0], clipped[..., 1], clipped[..., 2]

    luminance = r * 0.2126 + g * 0.7152 + b * 0.0722
    grad_x = cv2.Sobel(luminance, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(luminance, cv2.CV_32F, 0, 1, ksize=3)
    gradient_magnitude = cv2.magnitude(grad_x, grad_y)

    flat_gradient = gradient_magnitude.reshape(-1)
    if flat_gradient.size > _PERCENTILE_SAMPLE_SIZE:
        sample_indices = np.random.default_rng(0).choice(flat_gradient.size, _PERCENTILE_SAMPLE_SIZE, replace=False)
        edge_threshold = float(np.percentile(flat_gradient[sample_indices], _EDGE_PERCENTILE))
    else:
        edge_threshold = float(np.percentile(flat_gradient, _EDGE_PERCENTILE))
    edge_strength = np.clip(gradient_magnitude - edge_threshold, 0.0, None)
    max_strength = float(edge_strength.max())
    edge_mask = edge_strength / max_strength if max_strength > 1e-6 else edge_strength

    purple_fringe = np.clip(np.minimum(r, b) - g, 0.0, None)
    green_fringe = np.clip(g - np.maximum(r, b), 0.0, None)

    shift = edge_mask * amount * _MAX_DEFRINGE_SHIFT
    new_r = r - np.minimum(purple_fringe * shift, purple_fringe)
    new_b = b - np.minimum(purple_fringe * shift, purple_fringe)
    new_g = g - np.minimum(green_fringe * shift, green_fringe)

    result: np.ndarray = np.clip(np.stack([new_r, new_g, new_b], axis=-1), 0.0, 1.0)
    return result


def correct_chromatic_aberration_to_buffer(buffer: ImageBuffer, amount: float = 1.0) -> ImageBuffer:
    """Apply :func:`correct_chromatic_aberration` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = correct_chromatic_aberration(buffer.data[..., :3], amount)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))
