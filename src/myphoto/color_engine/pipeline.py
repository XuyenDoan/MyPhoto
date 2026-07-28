"""Orchestrates the Color Pipeline stages in the order defined by the spec.

White Balance -> Exposure -> Tone Curve -> RGB Curve -> HSL ->
Color Balance -> Film Simulation (3D LUT) -> Film Grain
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from myphoto.color_engine import operations as ops
from myphoto.color_engine.adapters.base import ColorMath
from myphoto.color_engine.adapters.opencv_adapter import OpenCVColorMath
from myphoto.color_engine.adjustments import ColorAdjustments
from myphoto.core.image import ImageBuffer


class ColorPipeline:
    """Applies a :class:`ColorAdjustments` set to an :class:`ImageBuffer`."""

    def __init__(self, color_math: ColorMath | None = None) -> None:
        self._color_math = color_math if color_math is not None else OpenCVColorMath()

    def process(
        self,
        buffer: ImageBuffer,
        adjustments: ColorAdjustments,
        film_simulation_lut: np.ndarray | None = None,
        rng: np.random.Generator | None = None,
    ) -> ImageBuffer:
        """Run ``buffer`` through the full color pipeline and return a new buffer.

        ``buffer.data`` must have 3 (RGB) or 4 (RGBA) channels; the alpha
        channel, if present, passes through untouched.
        """
        if buffer.channels not in (3, 4):
            raise ValueError(
                f"ColorPipeline requires an RGB or RGBA buffer, got {buffer.channels} channels"
            )

        rgb = buffer.data[..., :3]
        alpha = buffer.data[..., 3:] if buffer.channels == 4 else None

        rgb = ops.apply_white_balance(rgb, adjustments.white_balance_temp, adjustments.white_balance_tint)
        rgb = ops.apply_exposure(rgb, adjustments.exposure_ev)
        rgb = ops.apply_curve(rgb, adjustments.tone_curve)
        rgb = ops.apply_rgb_curves(
            rgb, adjustments.red_curve, adjustments.green_curve, adjustments.blue_curve
        )
        rgb = ops.apply_hsl(
            rgb,
            adjustments.hue_shift_degrees,
            adjustments.saturation_scale,
            adjustments.lightness_scale,
            self._color_math,
        )
        rgb = ops.apply_color_balance(rgb, adjustments.color_balance)
        if film_simulation_lut is not None:
            rgb = ops.apply_3d_lut(rgb, film_simulation_lut)
        rgb = ops.apply_film_grain(
            rgb, adjustments.grain_amount, adjustments.grain_size, self._color_math, rng
        )

        rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        data = rgb if alpha is None else np.concatenate([rgb, alpha], axis=-1)

        return replace(buffer, data=data)
