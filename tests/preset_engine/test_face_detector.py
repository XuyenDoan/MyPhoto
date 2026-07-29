from pathlib import Path

import numpy as np

from myphoto.core.image import ImageBuffer
from myphoto.preset_engine.face_detector import face_confidence


def _buffer(rgb: np.ndarray) -> ImageBuffer:
    return ImageBuffer(
        data=rgb.astype(np.float32),
        source_path=Path("/tmp/photo.jpg"),
        color_space="sRGB",
        bit_depth=8,
        is_raw=False,
    )


def test_returns_a_probability_in_range() -> None:
    rgb = np.random.default_rng(0).random((64, 64, 3)).astype(np.float32)
    result = face_confidence(_buffer(rgb))
    assert 0.0 <= result <= 1.0


def test_flat_skin_colored_image_is_not_mistaken_for_a_face() -> None:
    # The point of switching from a hue-range heuristic to a real detector:
    # a uniform "skin-colored" patch has no facial structure and shouldn't
    # score as a confident face detection.
    rgb = np.tile(np.array([0.8, 0.6, 0.5], dtype=np.float32), (64, 64, 1))
    result = face_confidence(_buffer(rgb))
    assert result < 0.5


def test_degrades_to_zero_on_invalid_model_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "myphoto.preset_engine.face_detector.face_detector_model_path",
        lambda: Path("/nonexistent/model.onnx"),
    )
    monkeypatch.setattr("myphoto.preset_engine.face_detector._session", None)

    rgb = np.zeros((16, 16, 3), dtype=np.float32)
    assert face_confidence(_buffer(rgb)) == 0.0
