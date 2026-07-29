"""Real (deep-learning) face-presence detection for `preset_engine.auto_suggest`.

Replaces an earlier hue-range "does this look like skin color" heuristic —
that approach had no way to distinguish an actual face from any other
object sharing a similar hue/saturation range (wood, sand, orange fabric,
...), and skewed unreliably across different skin tones. A trained face
detector generalizes far better.

Model: "Ultra-Light-Fast-Generic-Face-Detector-1MB" (version-RFB-320,
MIT-licensed), bundled at `models/face_detector.onnx` — see
`models/README.md` for attribution. Runs fully offline via `onnxruntime`
(CPU): no network call, no per-image cost, no photo ever leaves the
device.
"""

from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

from myphoto.core.image import ImageBuffer
from myphoto.resources import face_detector_model_path

_INPUT_SIZE = (320, 240)  # (width, height), fixed by the model
_MEAN = 127.0
_STD = 128.0

_session: ort.InferenceSession | None = None


def _get_session() -> ort.InferenceSession:
    global _session
    if _session is None:
        _session = ort.InferenceSession(
            str(face_detector_model_path()), providers=["CPUExecutionProvider"]
        )
    return _session


def face_confidence(buffer: ImageBuffer) -> float:
    """Return the highest face-detection confidence found in ``buffer`` (0..1).

    Degrades to 0.0 ("no face detected") on any failure — a missing/broken
    model, or an unusual image shape — never crashes preview rendering;
    auto-suggest just falls back to its other signals.
    """
    try:
        session = _get_session()
        rgb = np.clip(buffer.data[..., :3], 0.0, 1.0).astype(np.float32) * 255.0
        resized = cv2.resize(rgb, _INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        normalized = (resized - _MEAN) / _STD
        input_tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

        input_name = session.get_inputs()[0].name
        scores, _boxes = session.run(None, {input_name: input_tensor})
        face_scores = scores[0, :, 1]  # class index 1 = "face"
        return float(np.clip(face_scores.max(), 0.0, 1.0))
    except Exception:  # noqa: BLE001 - see docstring: always degrade, never raise.
        return 0.0
