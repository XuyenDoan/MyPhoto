"""Real (deep-learning) face detection.

Backs `preset_engine.auto_suggest`'s portrait signal and
`color_engine.composition_suggest`'s subject-location signal. Replaces an
earlier hue-range "does this look like skin color" heuristic — that
approach had no way to distinguish an actual face from any other object
sharing a similar hue/saturation range (wood, sand, orange fabric, ...),
and skewed unreliably across different skin tones. A trained face
detector generalizes far better.

Model: "Ultra-Light-Fast-Generic-Face-Detector-1MB" (version-RFB-320,
MIT-licensed), bundled at `models/face_detector.onnx` — see
`models/README.md` for attribution. Runs fully offline via `onnxruntime`
(CPU): no network call, no per-image cost, no photo ever leaves the
device.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import onnxruntime as ort

from myphoto.core.image import ImageBuffer
from myphoto.resources import face_detector_model_path

_INPUT_SIZE = (320, 240)  # (width, height), fixed by the model
_MEAN = 127.0
_STD = 128.0

_session: ort.InferenceSession | None = None


@dataclass(frozen=True, slots=True)
class FaceBox:
    """A detected face, as a fraction (0..1) of the image's width/height."""

    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2.0, (self.y0 + self.y1) / 2.0)


def _get_session() -> ort.InferenceSession:
    global _session
    if _session is None:
        _session = ort.InferenceSession(
            str(face_detector_model_path()), providers=["CPUExecutionProvider"]
        )
    return _session


def _run(buffer: ImageBuffer) -> tuple[np.ndarray, np.ndarray]:
    """Returns raw ``(scores, boxes)`` from the model: scores ``(N, 2)``,
    boxes ``(N, 4)`` as ``(x0, y0, x1, y1)`` fractions of the image.
    """
    session = _get_session()
    # Resize to the model's fixed input size *before* the clip/scale copy —
    # doing it in the other order (as an earlier version did) allocates a
    # full-resolution float32 copy of the source photo just to immediately
    # shrink it to 320x240, wasteful on a high-megapixel photo.
    resized = cv2.resize(buffer.data[..., :3], _INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
    resized = np.clip(resized, 0.0, 1.0).astype(np.float32) * 255.0
    normalized = (resized - _MEAN) / _STD
    input_tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

    input_name = session.get_inputs()[0].name
    scores, boxes = session.run(None, {input_name: input_tensor})
    return scores[0, :, 1], boxes[0]


def face_confidence(buffer: ImageBuffer) -> float:
    """Return the highest face-detection confidence found in ``buffer`` (0..1).

    Degrades to 0.0 ("no face detected") on any failure — a missing/broken
    model, or an unusual image shape — never crashes preview rendering;
    auto-suggest just falls back to its other signals.
    """
    try:
        face_scores, _boxes = _run(buffer)
        return float(np.clip(face_scores.max(), 0.0, 1.0))
    except Exception:  # noqa: BLE001 - see docstring: always degrade, never raise.
        return 0.0


def detect_primary_face(buffer: ImageBuffer, threshold: float = 0.7) -> FaceBox | None:
    """Return the highest-confidence detected face's bounding box, or
    ``None`` if nothing clears ``threshold`` (or detection fails).
    """
    try:
        face_scores, boxes = _run(buffer)
        best_index = int(np.argmax(face_scores))
        best_score = float(face_scores[best_index])
        if best_score < threshold:
            return None
        x0, y0, x1, y1 = (float(v) for v in boxes[best_index])
        return FaceBox(
            x0=min(max(x0, 0.0), 1.0),
            y0=min(max(y0, 0.0), 1.0),
            x1=min(max(x1, 0.0), 1.0),
            y1=min(max(y1, 0.0), 1.0),
            confidence=best_score,
        )
    except Exception:  # noqa: BLE001 - degrade to "no face found", never raise.
        return None
