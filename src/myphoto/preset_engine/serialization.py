"""Converts preset JSON documents to/from :class:`ColorAdjustments`/:class:`Preset`.

JSON schema for a preset file::

    {
      "id": "provia",
      "name": "Provia",
      "kind": "film_simulation",           // or "base_profile"
      "lut": "provia.npy",                 // optional, path relative to the preset file
      "adjustments": {
        "white_balance": {"temp": 0.0, "tint": 0.0},
        "exposure_ev": 0.0,
        "tone_curve": [[0.0, 0.0], [1.0, 1.0]],
        "red_curve": [[0.0, 0.0], [1.0, 1.0]],
        "green_curve": [[0.0, 0.0], [1.0, 1.0]],
        "blue_curve": [[0.0, 0.0], [1.0, 1.0]],
        "hsl": {"hue_shift_degrees": 0.0, "saturation_scale": 1.0, "lightness_scale": 1.0},
        "color_balance": {
          "shadows": [0.0, 0.0, 0.0],
          "midtones": [0.0, 0.0, 0.0],
          "highlights": [0.0, 0.0, 0.0]
        },
        "grain": {"amount": 0.0, "size": 1.0}
      }
    }

Any field may be omitted; omitted fields default to a neutral (no-op) value.
"""

from __future__ import annotations

from typing import Any

from myphoto.color_engine.adjustments import (
    IDENTITY_CURVE,
    RGB,
    ColorAdjustments,
    ColorBalanceAdjustment,
    Curve,
)
from myphoto.preset_engine.models import Preset, PresetKind


def _curve_from_json(value: Any) -> Curve:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("curve must be a list of at least 2 [x, y] points")
    return tuple((float(point[0]), float(point[1])) for point in value)


def _rgb_from_json(value: Any) -> RGB:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("expected a 3-element [r, g, b] list")
    return (float(value[0]), float(value[1]), float(value[2]))


def adjustments_from_json(data: dict[str, Any]) -> ColorAdjustments:
    """Build a :class:`ColorAdjustments` from a parsed ``"adjustments"`` object."""
    white_balance = data.get("white_balance", {})
    hsl = data.get("hsl", {})
    color_balance = data.get("color_balance", {})
    grain = data.get("grain", {})

    return ColorAdjustments(
        white_balance_temp=float(white_balance.get("temp", 0.0)),
        white_balance_tint=float(white_balance.get("tint", 0.0)),
        exposure_ev=float(data.get("exposure_ev", 0.0)),
        tone_curve=_curve_from_json(data["tone_curve"]) if "tone_curve" in data else IDENTITY_CURVE,
        red_curve=_curve_from_json(data["red_curve"]) if "red_curve" in data else IDENTITY_CURVE,
        green_curve=_curve_from_json(data["green_curve"]) if "green_curve" in data else IDENTITY_CURVE,
        blue_curve=_curve_from_json(data["blue_curve"]) if "blue_curve" in data else IDENTITY_CURVE,
        hue_shift_degrees=float(hsl.get("hue_shift_degrees", 0.0)),
        saturation_scale=float(hsl.get("saturation_scale", 1.0)),
        lightness_scale=float(hsl.get("lightness_scale", 1.0)),
        color_balance=ColorBalanceAdjustment(
            shadows=_rgb_from_json(color_balance["shadows"]) if "shadows" in color_balance else (0.0, 0.0, 0.0),
            midtones=_rgb_from_json(color_balance["midtones"]) if "midtones" in color_balance else (0.0, 0.0, 0.0),
            highlights=_rgb_from_json(color_balance["highlights"])
            if "highlights" in color_balance
            else (0.0, 0.0, 0.0),
        ),
        grain_amount=float(grain.get("amount", 0.0)),
        grain_size=float(grain.get("size", 1.0)),
    )


def preset_from_json(data: dict[str, Any]) -> Preset:
    """Build a :class:`Preset` (without resolving ``lut_path``) from a parsed document."""
    return Preset(
        id=str(data["id"]),
        name=str(data["name"]),
        kind=PresetKind(data["kind"]),
        adjustments=adjustments_from_json(data.get("adjustments", {})),
        lut_path=None,
    )
