import pytest

from myphoto.preset_engine.models import PresetKind
from myphoto.preset_engine.serialization import adjustments_from_json, preset_from_json


def test_adjustments_from_json_full_document() -> None:
    doc = {
        "white_balance": {"temp": 0.2, "tint": -0.1},
        "exposure_ev": 0.5,
        "tone_curve": [[0.0, 0.05], [1.0, 0.95]],
        "red_curve": [[0.0, 0.0], [1.0, 1.0]],
        "green_curve": [[0.0, 0.0], [1.0, 1.0]],
        "blue_curve": [[0.0, 0.0], [1.0, 1.0]],
        "hsl": {"hue_shift_degrees": 5.0, "saturation_scale": 1.2, "lightness_scale": 0.9},
        "color_balance": {
            "shadows": [0.01, 0.0, -0.01],
            "midtones": [0.0, 0.0, 0.0],
            "highlights": [0.02, 0.0, 0.0],
        },
        "grain": {"amount": 0.3, "size": 1.5},
    }
    adjustments = adjustments_from_json(doc)

    assert adjustments.white_balance_temp == 0.2
    assert adjustments.white_balance_tint == -0.1
    assert adjustments.exposure_ev == 0.5
    assert adjustments.tone_curve == ((0.0, 0.05), (1.0, 0.95))
    assert adjustments.hue_shift_degrees == 5.0
    assert adjustments.saturation_scale == 1.2
    assert adjustments.color_balance.shadows == (0.01, 0.0, -0.01)
    assert adjustments.color_balance.highlights == (0.02, 0.0, 0.0)
    assert adjustments.grain_amount == 0.3
    assert adjustments.grain_size == 1.5


def test_adjustments_from_json_defaults_missing_fields() -> None:
    adjustments = adjustments_from_json({})
    assert adjustments.white_balance_temp == 0.0
    assert adjustments.exposure_ev == 0.0
    assert adjustments.tone_curve == ((0.0, 0.0), (1.0, 1.0))
    assert adjustments.saturation_scale == 1.0
    assert adjustments.color_balance.shadows == (0.0, 0.0, 0.0)
    assert adjustments.grain_amount == 0.0


def test_curve_requires_at_least_two_points() -> None:
    with pytest.raises(ValueError, match="curve"):
        adjustments_from_json({"tone_curve": [[0.5, 0.5]]})


def test_color_balance_zone_requires_three_components() -> None:
    with pytest.raises(ValueError, match="r, g, b"):
        adjustments_from_json({"color_balance": {"shadows": [0.1, 0.1]}})


def test_preset_from_json_builds_preset() -> None:
    preset = preset_from_json(
        {
            "id": "provia",
            "name": "Provia (Standard)",
            "kind": "film_simulation",
            "adjustments": {"exposure_ev": 0.1},
        }
    )
    assert preset.id == "provia"
    assert preset.name == "Provia (Standard)"
    assert preset.kind is PresetKind.FILM_SIMULATION
    assert preset.adjustments.exposure_ev == 0.1
    assert preset.lut_path is None


def test_preset_from_json_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        preset_from_json({"id": "x", "name": "X", "kind": "not_a_kind"})


def test_preset_from_json_requires_id_and_name() -> None:
    with pytest.raises(KeyError):
        preset_from_json({"kind": "base_profile"})
