from myphoto.color_engine.adjustments import ColorAdjustments, ColorBalanceAdjustment


def _sample() -> ColorAdjustments:
    return ColorAdjustments(
        white_balance_temp=0.4,
        white_balance_tint=-0.2,
        exposure_ev=1.0,
        tone_curve=((0.0, 0.1), (1.0, 0.9)),
        hue_shift_degrees=10.0,
        saturation_scale=1.5,
        lightness_scale=1.2,
        color_balance=ColorBalanceAdjustment(shadows=(0.1, 0.0, -0.1)),
        grain_amount=0.6,
    )


def test_scaled_full_strength_is_unchanged() -> None:
    adjustments = _sample()
    assert adjustments.scaled(1.0) == adjustments


def test_scaled_zero_strength_is_identity() -> None:
    result = _sample().scaled(0.0)
    assert result.white_balance_temp == 0.0
    assert result.white_balance_tint == 0.0
    assert result.exposure_ev == 0.0
    assert result.hue_shift_degrees == 0.0
    assert result.saturation_scale == 1.0
    assert result.lightness_scale == 1.0
    assert result.color_balance.shadows == (0.0, 0.0, 0.0)
    assert result.grain_amount == 0.0
    assert result.tone_curve[0] == (0.0, 0.0)
    assert result.tone_curve[1] == (1.0, 1.0)


def test_scaled_half_strength_is_between() -> None:
    result = _sample().scaled(0.5)
    assert 0.0 < result.exposure_ev < 1.0
    assert 1.0 < result.saturation_scale < 1.5


def test_scaled_rejects_out_of_range_strength() -> None:
    import pytest

    with pytest.raises(ValueError, match="strength"):
        _sample().scaled(1.5)
