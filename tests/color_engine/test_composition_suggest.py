from pathlib import Path

import cv2
import numpy as np

from myphoto.color_engine.composition_suggest import suggest_crop
from myphoto.core.image import ImageBuffer


def _buffer(rgb: np.ndarray) -> ImageBuffer:
    return ImageBuffer(
        data=rgb.astype(np.float32),
        source_path=Path("/tmp/photo.jpg"),
        color_space="sRGB",
        bit_depth=8,
        is_raw=False,
    )


def _synthetic_face_image(size: int = 480, offset_x: int = -100) -> np.ndarray:
    """A real-enough facial structure, off-center, so a crop suggestion is meaningful."""
    cx, cy = size // 2 + offset_x, size // 2
    img = np.full((size, size, 3), (235, 220, 200), dtype=np.uint8)
    cv2.ellipse(img, (cx, cy), (90, 120), 0, 0, 360, (200, 175, 150), -1)
    for ex in (cx - 38, cx + 38):
        ey = cy - 18
        cv2.ellipse(img, (ex, ey), (18, 11), 0, 0, 360, (255, 255, 255), -1)
        cv2.circle(img, (ex, ey), 7, (120, 90, 60), -1)
        cv2.circle(img, (ex, ey), 3, (10, 10, 10), -1)
    cv2.ellipse(img, (cx, cy + 80), (30, 10), 0, 0, 180, (100, 60, 60), -1)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def test_suggests_a_crop_using_the_detected_face() -> None:
    rgb = _synthetic_face_image()
    suggestion = suggest_crop(_buffer(rgb))

    assert suggestion is not None
    assert suggestion.source == "face"
    assert 0 <= suggestion.x < suggestion.x + suggestion.width <= rgb.shape[1]
    assert 0 <= suggestion.y < suggestion.y + suggestion.height <= rgb.shape[0]


def test_suggested_crop_preserves_original_aspect_ratio() -> None:
    rgb = np.zeros((300, 500, 3), dtype=np.float32)
    rgb[100:200, 200:300] = (0.9, 0.1, 0.1)  # a distinct salient patch, off-center

    suggestion = suggest_crop(_buffer(rgb))

    assert suggestion is not None
    original_aspect = 500 / 300
    suggested_aspect = suggestion.width / suggestion.height
    assert abs(suggested_aspect - original_aspect) < 0.05


def test_falls_back_to_saliency_when_no_face_present() -> None:
    rgb = np.zeros((200, 200, 3), dtype=np.float32)
    rgb[20:60, 20:60] = (0.95, 0.9, 0.1)  # a bright, distinct patch, no face

    suggestion = suggest_crop(_buffer(rgb))

    assert suggestion is not None
    assert suggestion.source == "saliency"


def test_too_small_image_returns_none() -> None:
    rgb = np.zeros((2, 2, 3), dtype=np.float32)
    assert suggest_crop(_buffer(rgb)) is None
