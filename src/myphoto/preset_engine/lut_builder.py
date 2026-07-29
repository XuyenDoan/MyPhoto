"""Builds 3D color-grading LUTs for Film Simulation presets.

A LUT built here is a *refinement* layered on top of a preset's existing
JSON `adjustments` (global tone curve / uniform HSL rotate-saturate /
3-zone color balance, still applied first — see `ColorPipeline`) —
specifically the **hue-selective** color grading a single global HSL
rotation cannot express (e.g. "boost greens and blues, but leave skin
tones alone"), plus shadow/highlight split-toning. Recipes are
deliberately modest relative-adjustments (multipliers close to 1.0): the
JSON stage already owns each preset's overall saturation/contrast level,
so the LUT's job is shaping *relative* differences between color bands,
not re-deciding the overall intensity.

Android doesn't apply LUTs (see `android/core`), so presets without one
(or before this module existed) still render identically there — this is
an additive desktop-only refinement, not a replacement of the shared
JSON-driven look.

These are original, hand-authored approximations of each simulation's
*reputation* in photography discussion (e.g. "Velvia boosts greens and
blues while protecting skin tones") — not decompiled or copied from
Fujifilm's actual algorithms/LUTs.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

RGB = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class HueBand:
    """A soft-edged hue range (OpenCV's 0-360 HLS hue scale) to adjust selectively."""

    center: float
    width: float  # half-width in degrees; a linear taper to 0 at the edge
    hue_shift: float = 0.0
    saturation_mult: float = 1.0
    lightness_mult: float = 1.0

    def weight(self, hue: np.ndarray) -> np.ndarray:
        delta = np.abs(((hue - self.center + 180.0) % 360.0) - 180.0)
        return np.clip(1.0 - delta / self.width, 0.0, 1.0)


@dataclass(frozen=True, slots=True)
class LutRecipe:
    """A hue-selective grading recipe: overlapping hue bands plus split-toning."""

    hue_bands: tuple[HueBand, ...] = ()
    overall_saturation: float = 1.0
    shadow_tint: RGB = (0.0, 0.0, 0.0)
    highlight_tint: RGB = (0.0, 0.0, 0.0)


def build_lut(recipe: LutRecipe, size: int = 17) -> np.ndarray:
    """Bake ``recipe`` into a ``(size, size, size, 3)`` float32 LUT."""
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)
    r, g, b = np.meshgrid(ramp, ramp, ramp, indexing="ij")
    rgb = np.stack([r, g, b], axis=-1).reshape(-1, 1, 3).astype(np.float32)

    hls = cv2.cvtColor(rgb, cv2.COLOR_RGB2HLS).reshape(-1, 3)
    hue, lightness, saturation = hls[:, 0].copy(), hls[:, 1].copy(), hls[:, 2].copy()

    for band in recipe.hue_bands:
        weight = band.weight(hue)
        hue = hue + weight * band.hue_shift
        saturation = saturation * (1.0 + weight * (band.saturation_mult - 1.0))
        lightness = lightness * (1.0 + weight * (band.lightness_mult - 1.0))

    hue = hue % 360.0
    saturation = np.clip(saturation * recipe.overall_saturation, 0.0, 1.0)
    lightness = np.clip(lightness, 0.0, 1.0)

    hls_out = np.stack([hue, lightness, saturation], axis=-1).reshape(-1, 1, 3).astype(np.float32)
    graded = cv2.cvtColor(hls_out, cv2.COLOR_HLS2RGB).reshape(-1, 3)

    luminance = graded[:, 0] * 0.2126 + graded[:, 1] * 0.7152 + graded[:, 2] * 0.0722
    shadow_weight = np.clip(1.0 - luminance * 2.0, 0.0, 1.0)[:, np.newaxis]
    highlight_weight = np.clip(luminance * 2.0 - 1.0, 0.0, 1.0)[:, np.newaxis]
    graded = graded + shadow_weight * np.array(recipe.shadow_tint, dtype=np.float32)
    graded = graded + highlight_weight * np.array(recipe.highlight_tint, dtype=np.float32)
    graded = np.clip(graded, 0.0, 1.0)

    result: np.ndarray = graded.reshape(size, size, size, 3).astype(np.float32)
    return result
