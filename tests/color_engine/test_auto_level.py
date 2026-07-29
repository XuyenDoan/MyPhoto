from pathlib import Path

import cv2
import numpy as np

from myphoto.color_engine.auto_level import (
    apply_auto_level_to_buffer,
    auto_level,
    detect_tilt_degrees,
)
from myphoto.core.image import ImageBuffer


def _level_horizon_image(size: int = 300) -> np.ndarray:
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[: size // 2] = (0.85, 0.85, 0.9)  # "sky"
    rgb[size // 2 :] = (0.15, 0.35, 0.15)  # "ground"
    return rgb


def _tilted(rgb: np.ndarray, degrees: float) -> np.ndarray:
    height, width = rgb.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    return cv2.warpAffine(rgb, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def test_detects_tilt_in_a_rotated_horizon() -> None:
    tilted = _tilted(_level_horizon_image(), degrees=8.0)

    angle = detect_tilt_degrees(tilted)

    assert angle is not None
    assert 3.0 < abs(angle) < 15.0


def test_already_level_image_is_not_corrected() -> None:
    level = _level_horizon_image()

    result = auto_level(level)

    assert result.shape == level.shape
    assert np.allclose(result, level, atol=1e-3)


def test_auto_level_crops_and_reduces_measured_tilt() -> None:
    tilted = _tilted(_level_horizon_image(), degrees=8.0)

    result = auto_level(tilted)

    assert result.shape[0] < tilted.shape[0]
    assert result.shape[1] < tilted.shape[1]

    corrected_angle = detect_tilt_degrees(result)
    assert corrected_angle is None or abs(corrected_angle) < 2.0


def test_apply_to_buffer_preserves_metadata_and_crops() -> None:
    tilted = _tilted(_level_horizon_image(), degrees=8.0)
    buffer = ImageBuffer(
        data=tilted, source_path=Path("/tmp/x.jpg"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_auto_level_to_buffer(buffer)

    assert result.source_path == buffer.source_path
    assert result.height < buffer.height
    assert result.width < buffer.width


def test_flat_featureless_image_is_left_unchanged() -> None:
    flat = np.full((64, 64, 3), 0.5, dtype=np.float32)

    result = auto_level(flat)

    assert result.shape == flat.shape
    assert np.allclose(result, flat)
