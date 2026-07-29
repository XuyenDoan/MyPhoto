import numpy as np

from myphoto.preset_engine.lut_builder import HueBand, LutRecipe, build_lut


def test_identity_recipe_is_near_identity() -> None:
    lut = build_lut(LutRecipe(), size=9)
    ramp = np.linspace(0.0, 1.0, 9, dtype=np.float32)
    r, g, b = np.meshgrid(ramp, ramp, ramp, indexing="ij")
    grid = np.stack([r, g, b], axis=-1)

    assert lut.shape == (9, 9, 9, 3)
    assert np.allclose(lut, grid, atol=1e-3)


def test_hue_band_boosts_saturation_only_within_the_band() -> None:
    # A pure green (hue=120) and a pure red (hue=0) at the same lightness/saturation.
    green = np.array([0.2, 0.8, 0.2], dtype=np.float32)
    red = np.array([0.8, 0.2, 0.2], dtype=np.float32)

    recipe = LutRecipe(hue_bands=(HueBand(center=120, width=40, saturation_mult=1.5),))
    lut = build_lut(recipe, size=17)

    def sample(rgb: np.ndarray) -> np.ndarray:
        idx = np.clip((rgb * 16).round().astype(int), 0, 16)
        return lut[idx[0], idx[1], idx[2]]

    graded_green = sample(green)
    graded_red = sample(red)

    # Green should be pushed further from gray (more saturated); red should
    # be left essentially alone since it's outside the boosted hue band.
    def chroma(rgb: np.ndarray) -> float:
        return float(rgb.max() - rgb.min())

    assert chroma(graded_green) > chroma(green) + 0.05
    assert abs(chroma(graded_red) - chroma(red)) < 0.03  # grid-quantization noise from nearest-index sampling


def test_split_toning_tints_shadows_and_highlights_oppositely() -> None:
    recipe = LutRecipe(shadow_tint=(0.0, 0.0, 0.05), highlight_tint=(0.05, 0.0, 0.0))
    lut = build_lut(recipe, size=9)

    shadow = lut[0, 0, 0]  # near-black grid corner
    highlight = lut[-1, -1, -1]  # near-white grid corner

    assert shadow[2] > shadow[0]  # shadows pushed toward blue
    assert highlight[0] >= highlight[2]  # highlights pushed toward red (or unaffected at pure white)
