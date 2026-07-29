"""Automatic horizon/tilt straightening.

A crooked horizon (or any dominant straight line — a shoreline, a
building edge used as a leveling reference) is one of the most commonly
cited technical flaws in photography competition critiques. This detects
the photo's dominant near-horizontal line via classical edge/line
detection (Canny + probabilistic Hough transform — no trained model, no
network call, no cost) and rotates the image to level it, then crops to
the largest axis-aligned rectangle that fits inside the rotated frame
(rotating a rectangle necessarily leaves triangular gaps at the corners;
there's no way to straighten a tilted photo without losing some edge
content).

Deliberately conservative: only lines within `_MAX_CORRECTABLE_ANGLE` of
level are considered (so a deliberately dramatic Dutch-angle shot, or a
photo with no clear horizontal reference, isn't force-rotated), and a
photo with no confident line detection is returned unchanged.
"""

from __future__ import annotations

import math
from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer

#: Ignore candidate lines tilted further than this from level — a
#: genuinely dramatic diagonal composition shouldn't be "corrected".
_MAX_CORRECTABLE_ANGLE_DEGREES = 15.0

#: Below this, the photo is considered already level; skip the (lossy,
#: crop-inducing) rotation entirely.
_MIN_ANGLE_TO_CORRECT_DEGREES = 0.3

_CANNY_LOW = 50
_CANNY_HIGH = 150
_HOUGH_THRESHOLD = 60
_HOUGH_MIN_LINE_LENGTH_FRACTION = 0.25
_HOUGH_MAX_LINE_GAP = 20


def detect_tilt_degrees(rgb: np.ndarray) -> float | None:
    """Return the photo's dominant tilt in degrees (positive = rotated clockwise),
    or ``None`` if no confident near-horizontal line is found.
    """
    gray = cv2.cvtColor(np.clip(rgb, 0.0, 1.0).astype(np.float32), cv2.COLOR_RGB2GRAY)
    gray_u8 = (gray * 255.0).astype(np.uint8)
    edges = cv2.Canny(gray_u8, _CANNY_LOW, _CANNY_HIGH)

    height, width = gray.shape[:2]
    min_line_length = max(width, height) * _HOUGH_MIN_LINE_LENGTH_FRACTION
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=_HOUGH_THRESHOLD,
        minLineLength=min_line_length,
        maxLineGap=_HOUGH_MAX_LINE_GAP,
    )
    if lines is None:
        return None

    angles: list[float] = []
    weights: list[float] = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = float(x2 - x1), float(y2 - y1)
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        # Normalize into (-90, 90], then only keep near-horizontal candidates.
        if angle > 90:
            angle -= 180
        elif angle <= -90:
            angle += 180
        if abs(angle) > _MAX_CORRECTABLE_ANGLE_DEGREES:
            continue
        angles.append(angle)
        weights.append(length)

    if not angles:
        return None

    return float(np.average(angles, weights=weights))


def _largest_inscribed_rect(width: int, height: int, angle_radians: float) -> tuple[float, float]:
    """The largest axis-aligned ``(w, h)`` rectangle that fits inside a
    ``width`` x ``height`` rectangle rotated by ``angle_radians``.

    Standard closed-form solution (assumes the rotation is small enough
    that the inscribed rectangle's corners touch all four sides — true
    here since candidate angles are capped well under 45 degrees).
    """
    if width <= 0 or height <= 0:
        return (0.0, 0.0)

    angle = abs(angle_radians)
    sin_a, cos_a = math.sin(angle), math.cos(angle)
    cos_2a = cos_a * cos_a - sin_a * sin_a
    if cos_2a <= 1e-6:
        shorter = float(min(width, height))
        return (shorter, shorter)

    crop_w = (width * cos_a - height * sin_a) / cos_2a
    crop_h = (height * cos_a - width * sin_a) / cos_2a
    crop_w = max(1.0, min(float(width), crop_w))
    crop_h = max(1.0, min(float(height), crop_h))
    return (crop_w, crop_h)


def _rotate_and_crop(data: np.ndarray, angle_degrees: float) -> np.ndarray:
    height, width = data.shape[:2]
    center = (width / 2.0, height / 2.0)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    rotated = cv2.warpAffine(
        data.astype(np.float32), rotation_matrix, (width, height),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT,
    )
    if rotated.ndim == 2:
        rotated = rotated[..., np.newaxis]

    crop_w, crop_h = _largest_inscribed_rect(width, height, math.radians(angle_degrees))
    x0 = int((width - crop_w) / 2)
    y0 = int((height - crop_h) / 2)
    result: np.ndarray = rotated[y0 : y0 + int(crop_h), x0 : x0 + int(crop_w)]
    return result


def auto_level(rgb: np.ndarray) -> np.ndarray:
    """Detect and correct the photo's dominant tilt, cropping out the rotated
    frame's corner gaps. Returns ``rgb`` unchanged if no correction is warranted.
    """
    clipped: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    angle = detect_tilt_degrees(clipped)
    if angle is None or abs(angle) < _MIN_ANGLE_TO_CORRECT_DEGREES:
        return clipped
    return _rotate_and_crop(clipped, angle)


def apply_auto_level_to_buffer(buffer: ImageBuffer) -> ImageBuffer:
    """Apply :func:`auto_level` to ``buffer``, rotating/cropping every channel identically."""
    rgb = np.clip(buffer.data[..., :3], 0.0, 1.0).astype(np.float32)
    angle = detect_tilt_degrees(rgb)
    if angle is None or abs(angle) < _MIN_ANGLE_TO_CORRECT_DEGREES:
        return buffer

    data = _rotate_and_crop(buffer.data, angle)
    return replace(buffer, data=data.astype(np.float32))
