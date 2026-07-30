"""AI-assisted composition crop suggestion.

`suggest_crop` proposes a rule-of-thirds-aligned crop, drawn as an overlay
on the preview so the user can see it before committing to anything.
`apply_composition_crop_to_buffer` applies that same suggestion to a
buffer's actual pixels — used when the "Gợi ý bố cục" checkbox is enabled,
so the exported photo is cropped to match what the overlay showed.

Finds the photo's main subject via a small AI model when possible (the
same face detector `preset_engine.auto_suggest` uses — see
`color_engine.face_detector`), falling back to classical saliency
detection (`cv2.saliency.StaticSaliencySpectralResidual`, spectral-residual
visual attention — no trained model, but still a real, general-purpose
"what looks visually interesting" detector) for non-portrait photos. Then
tries a few crop sizes and picks whichever one lands the subject closest
to a rule-of-thirds intersection while keeping as much of the frame as
possible.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from myphoto.color_engine.face_detector import detect_primary_face
from myphoto.core.image import ImageBuffer

#: Rule-of-thirds intersection points, as (x, y) fractions of the frame.
_THIRDS_POINTS: tuple[tuple[float, float], ...] = ((1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3))

#: Crop sizes to try, as a fraction of the original frame (aspect ratio kept).
_CROP_SCALES: tuple[float, ...] = (1.0, 0.92, 0.84)

#: Slight preference for less-aggressive (larger) crops, all else equal.
_AREA_PREFERENCE_WEIGHT = 0.05

#: Only consider the most visually salient this-percentile-and-above region.
_SALIENCY_PERCENTILE = 90.0


@dataclass(frozen=True, slots=True)
class CropSuggestion:
    """A suggested crop rectangle, in pixel coordinates of the analyzed image."""

    x: int
    y: int
    width: int
    height: int
    target_thirds_point: tuple[float, float]
    source: str  # "face" or "saliency"


def _subject_fraction(buffer: ImageBuffer) -> tuple[tuple[float, float], str] | None:
    """The main subject's location as an (x, y) fraction of the frame, and how it was found."""
    face = detect_primary_face(buffer)
    if face is not None:
        return face.center, "face"

    rgb = np.clip(buffer.data[..., :3], 0.0, 1.0).astype(np.float32)
    bgr_u8 = cv2.cvtColor((rgb * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()  # type: ignore[attr-defined]
    success, saliency_map = saliency.computeSaliency(bgr_u8)
    if not success:
        return None

    height, width = saliency_map.shape[:2]
    blurred = cv2.GaussianBlur(saliency_map, (0, 0), max(height, width) * 0.02)
    threshold = float(np.percentile(blurred, _SALIENCY_PERCENTILE))
    mask = blurred >= threshold
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    return (float(xs.mean()) / width, float(ys.mean()) / height), "saliency"


def suggest_crop(buffer: ImageBuffer) -> CropSuggestion | None:
    """Suggest a rule-of-thirds-aligned crop for ``buffer``, or ``None`` if
    no subject could be located (or detection fails).
    """
    try:
        subject = _subject_fraction(buffer)
    except Exception:  # noqa: BLE001 - a suggestion failure just means "no overlay", never a crash.
        return None
    if subject is None:
        return None
    (subject_x_frac, subject_y_frac), source = subject

    height, width = buffer.data.shape[:2]
    if height < 4 or width < 4:
        return None
    aspect = width / height
    subject_x, subject_y = subject_x_frac * width, subject_y_frac * height

    best: CropSuggestion | None = None
    best_score = float("-inf")
    for scale in _CROP_SCALES:
        crop_w = width * scale
        crop_h = crop_w / aspect
        if crop_h > height:
            crop_h = height * scale
            crop_w = crop_h * aspect

        for target_x_frac, target_y_frac in _THIRDS_POINTS:
            crop_x = min(max(subject_x - target_x_frac * crop_w, 0.0), width - crop_w)
            crop_y = min(max(subject_y - target_y_frac * crop_h, 0.0), height - crop_h)

            actual_x_frac = (subject_x - crop_x) / crop_w
            actual_y_frac = (subject_y - crop_y) / crop_h
            closeness = -((actual_x_frac - target_x_frac) ** 2 + (actual_y_frac - target_y_frac) ** 2)
            score = closeness + scale * _AREA_PREFERENCE_WEIGHT

            if score > best_score:
                best_score = score
                best = CropSuggestion(
                    x=int(crop_x),
                    y=int(crop_y),
                    width=int(crop_w),
                    height=int(crop_h),
                    target_thirds_point=(target_x_frac, target_y_frac),
                    source=source,
                )
    return best


def apply_composition_crop_to_buffer(buffer: ImageBuffer) -> ImageBuffer:
    """Return ``buffer`` cropped to :func:`suggest_crop`'s suggestion, or
    unchanged if no subject could be located.
    """
    suggestion = suggest_crop(buffer)
    if suggestion is None:
        return buffer
    data = buffer.data[
        suggestion.y : suggestion.y + suggestion.height,
        suggestion.x : suggestion.x + suggestion.width,
    ]
    return replace(buffer, data=data.astype(np.float32))
