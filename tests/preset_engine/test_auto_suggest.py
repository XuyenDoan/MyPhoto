from pathlib import Path

import numpy as np

from myphoto.core.image import ImageBuffer
from myphoto.preset_engine.auto_suggest import FALLBACK_PRESET_ID, suggest_film_simulation_id

_ALL_IDS = {
    "provia", "velvia", "astia", "classic_chrome", "classic_neg",
    "pro_neg_hi", "pro_neg_std", "eterna", "eterna_bleach_bypass",
    "acros", "sepia", "nostalgic_neg", "reala_ace",
}


def _buffer(rgb: np.ndarray) -> ImageBuffer:
    return ImageBuffer(
        data=rgb.astype(np.float32),
        source_path=Path("/tmp/photo.jpg"),
        color_space="sRGB",
        bit_depth=8,
        is_raw=False,
    )


def _uniform(rgb: tuple[float, float, float], size: int = 32) -> np.ndarray:
    return np.tile(np.array(rgb, dtype=np.float32), (size, size, 1))


def test_saturated_greenery_and_sky_suggests_velvia() -> None:
    top = np.tile(np.array([0.1, 0.7, 0.1], dtype=np.float32), (16, 32, 1))
    bottom = np.tile(np.array([0.2, 0.5, 0.9], dtype=np.float32), (16, 32, 1))
    rgb = np.concatenate([top, bottom], axis=0)

    assert suggest_film_simulation_id(_buffer(rgb), _ALL_IDS) == "velvia"


def test_skin_tone_dominant_image_suggests_astia() -> None:
    rgb = _uniform((0.8, 0.6, 0.5))

    assert suggest_film_simulation_id(_buffer(rgb), _ALL_IDS) == "astia"


def test_high_contrast_desaturated_image_suggests_acros() -> None:
    rgb = np.zeros((32, 32, 3), dtype=np.float32)
    rgb[::2] = 0.2
    rgb[1::2] = 0.8

    assert suggest_film_simulation_id(_buffer(rgb), _ALL_IDS) == "acros"


def test_ordinary_saturated_outdoor_snapshot_does_not_default_to_velvia() -> None:
    # A regular sky+ground+building daylight photo — noticeably colorful but
    # not a punchy landscape shot. The nearest-centroid classifier should
    # NOT reach for the vivid preset just because saturation is moderately
    # high somewhere in frame (the failure mode of the old weighted-sum
    # scorer, which over-picked Velvia for ordinary photos).
    sky = np.tile(np.array([0.5, 0.65, 0.85], dtype=np.float32), (10, 32, 1))
    midground = np.tile(np.array([0.55, 0.5, 0.4], dtype=np.float32), (12, 32, 1))
    grass = np.tile(np.array([0.3, 0.5, 0.25], dtype=np.float32), (10, 32, 1))
    rgb = np.concatenate([sky, midground, grass], axis=0)

    assert suggest_film_simulation_id(_buffer(rgb), _ALL_IDS) != "velvia"


def test_warm_dim_muted_image_suggests_nostalgic_neg() -> None:
    rgb = _uniform((0.32, 0.22, 0.12))

    assert suggest_film_simulation_id(_buffer(rgb), _ALL_IDS) == "nostalgic_neg"


def test_falls_back_when_suggested_id_not_available() -> None:
    rgb = _uniform((0.8, 0.6, 0.5))  # would suggest astia

    assert suggest_film_simulation_id(_buffer(rgb), {"provia"}) == "provia"


def test_empty_available_ids_returns_fallback_constant() -> None:
    rgb = _uniform((0.5, 0.5, 0.5))

    assert suggest_film_simulation_id(_buffer(rgb), set()) == FALLBACK_PRESET_ID
