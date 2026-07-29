from pathlib import Path

import cv2
import numpy as np

from myphoto.color_engine.face_detector import detect_primary_face, face_confidence
from myphoto.core.image import ImageBuffer


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


def _synthetic_face_image(size: int = 480) -> np.ndarray:
    """A crude but real facial structure (eyes/nose/mouth), enough for the
    trained detector to genuinely recognize — a flat color patch (as in
    the test above) is not.
    """
    cx, cy = size // 2, size // 2
    img = np.full((size, size, 3), (235, 220, 200), dtype=np.uint8)
    cv2.ellipse(img, (cx, cy), (110, 145), 0, 0, 360, (200, 175, 150), -1)
    for ex in (cx - 45, cx + 45):
        ey = cy - 20
        cv2.ellipse(img, (ex, ey), (22, 13), 0, 0, 360, (255, 255, 255), -1)
        cv2.circle(img, (ex, ey), 9, (120, 90, 60), -1)
        cv2.circle(img, (ex, ey), 4, (10, 10, 10), -1)
    cv2.ellipse(img, (cx, cy + 95), (35, 12), 0, 0, 180, (100, 60, 60), -1)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def test_detects_primary_face_bounding_box_near_center() -> None:
    rgb = _synthetic_face_image()
    face = detect_primary_face(_buffer(rgb), threshold=0.5)

    assert face is not None
    center_x, center_y = face.center
    assert 0.3 < center_x < 0.7
    assert 0.3 < center_y < 0.7


def test_no_face_returns_none() -> None:
    rgb = np.tile(np.array([0.8, 0.6, 0.5], dtype=np.float32), (64, 64, 1))
    assert detect_primary_face(_buffer(rgb)) is None


def test_degrades_to_zero_on_invalid_model_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "myphoto.color_engine.face_detector.face_detector_model_path",
        lambda: Path("/nonexistent/model.onnx"),
    )
    monkeypatch.setattr("myphoto.color_engine.face_detector._session", None)

    rgb = np.zeros((16, 16, 3), dtype=np.float32)
    assert face_confidence(_buffer(rgb)) == 0.0
