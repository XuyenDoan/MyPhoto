"""Parameters describing one pass through the Color Pipeline.

A :class:`ColorAdjustments` instance is produced by the Preset Engine
(combining a Base Profile and a Film Simulation layer, scaled by Strength)
and consumed by :class:`~myphoto.color_engine.pipeline.ColorPipeline`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RGB = tuple[float, float, float]

#: A tone/RGB curve as ordered (input, output) control points in [0, 1].
Curve = tuple[tuple[float, float], ...]

IDENTITY_CURVE: Curve = ((0.0, 0.0), (1.0, 1.0))


@dataclass(frozen=True, slots=True)
class ColorBalanceAdjustment:
    """Additive RGB offsets applied per luminosity zone (lift/gamma/gain style)."""

    shadows: RGB = (0.0, 0.0, 0.0)
    midtones: RGB = (0.0, 0.0, 0.0)
    highlights: RGB = (0.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class ColorAdjustments:
    """The full set of Color Pipeline parameters for a single render pass."""

    white_balance_temp: float = 0.0
    """-1.0 (cooler/blue) .. +1.0 (warmer/amber)."""

    white_balance_tint: float = 0.0
    """-1.0 (green) .. +1.0 (magenta)."""

    exposure_ev: float = 0.0

    tone_curve: Curve = IDENTITY_CURVE
    red_curve: Curve = IDENTITY_CURVE
    green_curve: Curve = IDENTITY_CURVE
    blue_curve: Curve = IDENTITY_CURVE

    hue_shift_degrees: float = 0.0
    saturation_scale: float = 1.0
    lightness_scale: float = 1.0

    color_balance: ColorBalanceAdjustment = field(default_factory=ColorBalanceAdjustment)

    grain_amount: float = 0.0
    """0.0 (no grain) .. 1.0 (heavy grain)."""

    grain_size: float = 1.0
    """Relative grain particle size; 1.0 is the baseline size."""

    def scaled(self, strength: float) -> ColorAdjustments:
        """Return a copy linearly blended toward identity by ``strength`` (0..1).

        ``strength=1.0`` returns ``self`` unchanged; ``strength=0.0`` returns
        an adjustment set with no visible effect. This backs the UI's
        Strength slider.
        """
        if not 0.0 <= strength <= 1.0:
            raise ValueError(f"strength must be in [0, 1], got {strength}")

        def lerp(value: float, identity: float) -> float:
            return identity + (value - identity) * strength

        def lerp_curve(curve: Curve) -> Curve:
            if strength >= 1.0:
                return curve
            return tuple((x, lerp(y, x)) for x, y in curve)

        def lerp_rgb(rgb: RGB) -> RGB:
            return (lerp(rgb[0], 0.0), lerp(rgb[1], 0.0), lerp(rgb[2], 0.0))

        return ColorAdjustments(
            white_balance_temp=lerp(self.white_balance_temp, 0.0),
            white_balance_tint=lerp(self.white_balance_tint, 0.0),
            exposure_ev=lerp(self.exposure_ev, 0.0),
            tone_curve=lerp_curve(self.tone_curve),
            red_curve=lerp_curve(self.red_curve),
            green_curve=lerp_curve(self.green_curve),
            blue_curve=lerp_curve(self.blue_curve),
            hue_shift_degrees=lerp(self.hue_shift_degrees, 0.0),
            saturation_scale=lerp(self.saturation_scale, 1.0),
            lightness_scale=lerp(self.lightness_scale, 1.0),
            color_balance=ColorBalanceAdjustment(
                shadows=lerp_rgb(self.color_balance.shadows),
                midtones=lerp_rgb(self.color_balance.midtones),
                highlights=lerp_rgb(self.color_balance.highlights),
            ),
            grain_amount=lerp(self.grain_amount, 0.0),
            grain_size=self.grain_size,
        )
