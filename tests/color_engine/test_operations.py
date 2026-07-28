import numpy as np
import pytest

from myphoto.color_engine import operations as ops
from myphoto.color_engine.adapters.opencv_adapter import OpenCVColorMath
from myphoto.color_engine.adjustments import ColorBalanceAdjustment


@pytest.fixture
def color_math() -> OpenCVColorMath:
    return OpenCVColorMath()


@pytest.fixture
def flat_rgb() -> np.ndarray:
    return np.full((4, 4, 3), 0.5, dtype=np.float32)


def test_white_balance_neutral_is_identity(flat_rgb: np.ndarray) -> None:
    result = ops.apply_white_balance(flat_rgb, temp=0.0, tint=0.0)
    np.testing.assert_allclose(result, flat_rgb)


def test_white_balance_warms_red_and_cools_blue(flat_rgb: np.ndarray) -> None:
    result = ops.apply_white_balance(flat_rgb, temp=1.0, tint=0.0)
    assert result[0, 0, 0] > flat_rgb[0, 0, 0]  # red boosted
    assert result[0, 0, 2] < flat_rgb[0, 0, 2]  # blue reduced


def test_exposure_doubles_at_one_stop(flat_rgb: np.ndarray) -> None:
    result = ops.apply_exposure(flat_rgb, exposure_ev=1.0)
    np.testing.assert_allclose(result, flat_rgb * 2.0, rtol=1e-6)


def test_curve_identity_is_noop() -> None:
    values = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
    result = ops.apply_curve(values, ((0.0, 0.0), (1.0, 1.0)))
    np.testing.assert_allclose(result, values, atol=1e-6)


def test_curve_inverts() -> None:
    values = np.array([0.0, 0.25, 1.0], dtype=np.float32)
    result = ops.apply_curve(values, ((0.0, 1.0), (1.0, 0.0)))
    np.testing.assert_allclose(result, 1.0 - values, atol=1e-6)


def test_rgb_curves_apply_independently() -> None:
    rgb = np.full((2, 2, 3), 0.5, dtype=np.float32)
    boost_red = ((0.0, 0.0), (1.0, 1.0), (0.5, 0.9))
    identity = ((0.0, 0.0), (1.0, 1.0))
    result = ops.apply_rgb_curves(rgb, boost_red, identity, identity)
    assert result[0, 0, 0] > 0.8
    np.testing.assert_allclose(result[..., 1], 0.5, atol=1e-6)
    np.testing.assert_allclose(result[..., 2], 0.5, atol=1e-6)


def test_hsl_zero_saturation_desaturates(color_math: OpenCVColorMath) -> None:
    rgb = np.zeros((2, 2, 3), dtype=np.float32)
    rgb[..., 0] = 0.8
    rgb[..., 1] = 0.2
    rgb[..., 2] = 0.2
    result = ops.apply_hsl(rgb, 0.0, saturation_scale=0.0, lightness_scale=1.0, color_math=color_math)
    channel_spread = result[..., :3].max(axis=-1) - result[..., :3].min(axis=-1)
    np.testing.assert_allclose(channel_spread, 0.0, atol=1e-5)


def test_hsl_noop_parameters_are_skipped(color_math: OpenCVColorMath, flat_rgb: np.ndarray) -> None:
    result = ops.apply_hsl(flat_rgb, 0.0, 1.0, 1.0, color_math)
    assert result is flat_rgb


def test_color_balance_zero_adjustment_is_noop(flat_rgb: np.ndarray) -> None:
    result = ops.apply_color_balance(flat_rgb, ColorBalanceAdjustment())
    assert result is flat_rgb


def test_color_balance_shadow_lift_brightens_dark_pixels() -> None:
    rgb = np.zeros((1, 1, 3), dtype=np.float32)
    adjustment = ColorBalanceAdjustment(shadows=(0.1, 0.1, 0.1))
    result = ops.apply_color_balance(rgb, adjustment)
    assert np.all(result > rgb)


def test_film_grain_zero_amount_is_noop(flat_rgb: np.ndarray, color_math: OpenCVColorMath) -> None:
    result = ops.apply_film_grain(flat_rgb, amount=0.0, size=1.0, color_math=color_math)
    assert result is flat_rgb


def test_film_grain_adds_variation(color_math: OpenCVColorMath) -> None:
    rgb = np.full((32, 32, 3), 0.5, dtype=np.float32)
    rng = np.random.default_rng(42)
    result = ops.apply_film_grain(rgb, amount=0.5, size=1.0, color_math=color_math, rng=rng)
    assert not np.allclose(result, rgb)
    assert result.std() > 0.0


def test_3d_lut_identity_is_approximately_noop() -> None:
    rgb = np.random.default_rng(0).random((5, 5, 3)).astype(np.float32)
    lut = ops.identity_lut(size=9)
    result = ops.apply_3d_lut(rgb, lut)
    np.testing.assert_allclose(result, rgb, atol=1e-2)
