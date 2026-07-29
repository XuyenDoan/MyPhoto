"""Heuristic (non-ML) Film Simulation suggestion based on image statistics.

This is *not* a trained model — no machine learning, no bundled weights,
nothing sent over the network. It's a nearest-centroid classifier: each
Film Simulation has a hand-authored "typical photo" feature vector (how
warm/bright/contrasty/saturated a photo suits it, plus how much skin tone
or foliage/sky it usually has), and the loaded photo's own measured
statistics are matched to whichever centroid is closest (normalized
Euclidean distance across every feature at once).

Why nearest-centroid rather than a simple weighted-sum-of-signals score
(this module's first version): a weighted sum lets one strong signal (e.g.
high overall saturation) dominate and push a vivid preset to the top for
almost any colorful photo, regardless of how well the *rest* of the photo's
character actually matches that preset's scenario. Distance-to-centroid
requires the photo to be close across every dimension at once, so a photo
only gets matched to Velvia when it's genuinely landscape-like *and*
vivid together — not just "somewhat saturated somewhere in the frame".

Provia's centroid sits at roughly the population-typical values, so
ordinary/ambiguous photos land on it (the "standard" simulation) rather
than on a more stylized preset by default.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from myphoto.color_engine.adapters.opencv_adapter import OpenCVColorMath
from myphoto.core.image import ImageBuffer

#: Used when nothing else scores above zero, or the analysis can't run
#: (e.g. an empty image) — Provia is the "standard" simulation.
FALLBACK_PRESET_ID = "provia"

#: Analysis only needs a rough read on the image's content, not full
#: resolution — capping this keeps auto-suggest instant even on large photos.
_ANALYSIS_MAX_DIMENSION = 256


@dataclass(frozen=True, slots=True)
class _SceneStats:
    warmth: float  # mean red - mean blue; positive = warm, negative = cool
    brightness: float  # mean HLS lightness, 0..1
    contrast: float  # std of HLS lightness, 0..1
    mean_saturation: float  # mean HLS saturation, 0..1
    skin_ratio: float  # fraction of pixels in a typical skin-tone range
    nature_ratio: float  # fraction of pixels in typical foliage/sky hue ranges


#: (warmth, brightness, contrast, saturation, skin_ratio, nature_ratio) —
#: hand-authored "typical photo" centroid for each shipped Film Simulation.
_CENTROIDS: dict[str, tuple[float, float, float, float, float, float]] = {
    "provia": (0.00, 0.50, 0.18, 0.35, 0.05, 0.10),
    "velvia": (0.02, 0.50, 0.22, 0.60, 0.00, 0.55),
    "astia": (0.03, 0.55, 0.15, 0.40, 0.60, 0.05),
    "pro_neg_hi": (0.02, 0.50, 0.22, 0.35, 0.50, 0.05),
    "pro_neg_std": (0.02, 0.50, 0.14, 0.30, 0.50, 0.05),
    "reala_ace": (0.00, 0.50, 0.20, 0.45, 0.10, 0.30),
    "classic_chrome": (-0.03, 0.45, 0.16, 0.28, 0.10, 0.15),
    "classic_neg": (-0.05, 0.45, 0.18, 0.30, 0.15, 0.10),
    "eterna": (-0.02, 0.45, 0.12, 0.25, 0.10, 0.15),
    "eterna_bleach_bypass": (0.00, 0.45, 0.30, 0.15, 0.05, 0.10),
    "acros": (0.00, 0.50, 0.28, 0.05, 0.05, 0.10),
    "sepia": (0.10, 0.40, 0.20, 0.05, 0.10, 0.10),
    "nostalgic_neg": (0.12, 0.32, 0.16, 0.30, 0.20, 0.10),
}

#: Per-feature normalization divisor, roughly each feature's typical spread
#: across real photos — keeps one high-range feature (e.g. saturation)
#: from dominating the distance just because its raw numbers are bigger.
_FEATURE_SCALE = (0.15, 0.30, 0.15, 0.30, 0.50, 0.50)


def suggest_film_simulation_id(buffer: ImageBuffer, available_ids: set[str]) -> str:
    """Return the id of the closest-matching Film Simulation preset for ``buffer``.

    ``available_ids`` is whatever the caller's :class:`~myphoto.preset_engine.loader.PresetLoader`
    actually has loaded — a preset this heuristic knows about but that isn't
    shipped is simply skipped.
    """
    if buffer.data.size == 0 or not available_ids:
        return FALLBACK_PRESET_ID if FALLBACK_PRESET_ID in available_ids else next(iter(available_ids), FALLBACK_PRESET_ID)

    stats = _analyze(buffer)
    vector = (stats.warmth, stats.brightness, stats.contrast, stats.mean_saturation, stats.skin_ratio, stats.nature_ratio)

    ranked = sorted(_CENTROIDS.items(), key=lambda item: _distance(vector, item[1]))
    for preset_id, _centroid in ranked:
        if preset_id in available_ids:
            return preset_id
    return next(iter(available_ids), FALLBACK_PRESET_ID)


def _distance(
    vector: tuple[float, float, float, float, float, float],
    centroid: tuple[float, float, float, float, float, float],
) -> float:
    return sum(((v - c) / scale) ** 2 for v, c, scale in zip(vector, centroid, _FEATURE_SCALE, strict=True))


def _analyze(buffer: ImageBuffer) -> _SceneStats:
    rgb = np.clip(buffer.data[..., :3], 0.0, 1.0).astype(np.float32)
    height, width = rgb.shape[:2]
    longer_side = max(height, width)
    if longer_side > _ANALYSIS_MAX_DIMENSION:
        step = max(1, longer_side // _ANALYSIS_MAX_DIMENSION)
        rgb = rgb[::step, ::step]

    hls = OpenCVColorMath().rgb_to_hls(rgb)
    hue, lightness, saturation = hls[..., 0], hls[..., 1], hls[..., 2]

    warmth = float(rgb[..., 0].mean() - rgb[..., 2].mean())
    brightness = float(lightness.mean())
    contrast = float(lightness.std())
    mean_saturation = float(saturation.mean())

    # Hue ranges below are OpenCV's 0-360 HLS hue scale, chosen generously
    # (not from any ground-truth dataset) to catch typical cases.
    skin_mask = (
        (hue >= 5) & (hue <= 45) & (saturation >= 0.15) & (saturation <= 0.75) & (lightness >= 0.25) & (lightness <= 0.85)
    )
    green_mask = (hue >= 70) & (hue <= 170) & (saturation >= 0.15)
    sky_mask = (hue >= 180) & (hue <= 260) & (saturation >= 0.1) & (lightness >= 0.4)

    return _SceneStats(
        warmth=warmth,
        brightness=brightness,
        contrast=contrast,
        mean_saturation=mean_saturation,
        skin_ratio=float(skin_mask.mean()),
        nature_ratio=float((green_mask | sky_mask).mean()),
    )
