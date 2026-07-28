"""Heuristic (non-ML) Film Simulation suggestion based on image statistics.

This is *not* a trained model — no machine learning, no bundled weights,
nothing sent over the network. It's a small set of deterministic rules over
simple color statistics (overall warmth, brightness, contrast, saturation,
and the fraction of pixels that look like skin tones / greenery / sky) that
map a photo's rough "scenario" to whichever shipped Film Simulation usually
suits it. It's meant as a fast starting point the user can always override,
not a claim of being "correct" — a proper learned scene classifier is a
much bigger project (see docs/Architecture.md).
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
    green_ratio: float  # fraction of pixels in a typical foliage hue range
    sky_ratio: float  # fraction of pixels in a typical sky hue range


def suggest_film_simulation_id(buffer: ImageBuffer, available_ids: set[str]) -> str:
    """Return the id of the best-matching Film Simulation preset for ``buffer``.

    ``available_ids`` is whatever the caller's :class:`~myphoto.preset_engine.loader.PresetLoader`
    actually has loaded — a scored id that isn't shipped (e.g. a future
    preset this heuristic doesn't know about yet) is simply skipped.
    """
    if buffer.data.size == 0 or not available_ids:
        return FALLBACK_PRESET_ID if FALLBACK_PRESET_ID in available_ids else next(iter(available_ids), FALLBACK_PRESET_ID)

    stats = _analyze(buffer)
    for preset_id, _score in sorted(_scores(stats).items(), key=lambda item: item[1], reverse=True):
        if preset_id in available_ids:
            return preset_id
    return next(iter(available_ids), FALLBACK_PRESET_ID)


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
        green_ratio=float(green_mask.mean()),
        sky_ratio=float(sky_mask.mean()),
    )


def _scores(stats: _SceneStats) -> dict[str, float]:
    """Score every shipped Film Simulation for how well it fits ``stats``.

    Each rule targets the scenario that preset is designed to flatter, e.g.
    Velvia for saturated nature/landscape shots, Astia for portraits. The
    exact weights are hand-tuned, not fit to data — treat this as "a
    reasonable guess", not ground truth.
    """
    nature_ratio = stats.green_ratio + stats.sky_ratio
    vividness = max(0.0, stats.mean_saturation - 0.3)
    mutedness = max(0.0, 0.4 - stats.mean_saturation)

    return {
        "astia": stats.skin_ratio * 3.0,
        "pro_neg_hi": stats.skin_ratio * 2.0 if stats.contrast >= 0.18 else stats.skin_ratio * 0.5,
        "pro_neg_std": stats.skin_ratio * 2.0 if stats.contrast < 0.18 else stats.skin_ratio * 0.5,
        "velvia": nature_ratio * 2.0 + vividness * 2.0,
        "reala_ace": vividness * 1.5 if stats.skin_ratio < 0.15 else vividness * 0.3,
        "acros": mutedness * 2.0 if stats.contrast > 0.2 else 0.0,
        "sepia": mutedness * 1.5 if stats.warmth > 0.02 else 0.0,
        "nostalgic_neg": stats.warmth * 2.0 if stats.brightness < 0.45 else 0.0,
        "classic_neg": mutedness * 1.5 if stats.warmth < 0 else mutedness * 0.5,
        "eterna_bleach_bypass": mutedness * 1.0 if stats.contrast > 0.25 else 0.0,
        "eterna": mutedness * 1.2 if stats.contrast <= 0.25 else 0.0,
        "classic_chrome": mutedness * 1.2,
        "provia": 0.2,  # small, always-present baseline so something always wins
    }
