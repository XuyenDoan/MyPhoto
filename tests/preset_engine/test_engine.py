from pathlib import Path

import numpy as np
import pytest

from myphoto.core.image import ImageBuffer
from myphoto.preset_engine.engine import PresetEngine
from myphoto.preset_engine.loader import PresetLoader

REPO_PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"


@pytest.fixture
def loader() -> PresetLoader:
    return PresetLoader(REPO_PRESETS_DIR / "base_profiles", REPO_PRESETS_DIR / "film_simulations")


@pytest.fixture
def buffer() -> ImageBuffer:
    data = np.random.default_rng(0).random((16, 16, 3)).astype(np.float32)
    return ImageBuffer(
        data=data, source_path=Path("dummy.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )


def test_render_returns_valid_buffer(loader: PresetLoader, buffer: ImageBuffer) -> None:
    engine = PresetEngine(loader)
    result = engine.render(buffer, "fujifilm", "velvia", strength=1.0, rng=np.random.default_rng(0))

    assert result.data.shape == buffer.data.shape
    assert result.data.dtype == np.float32
    assert result.data.min() >= 0.0
    assert result.data.max() <= 1.0


def test_strength_scales_the_effect(loader: PresetLoader, buffer: ImageBuffer) -> None:
    engine = PresetEngine(loader)

    def deterministic_rng() -> np.random.Generator:
        return np.random.default_rng(0)

    full = engine.render(buffer, "fujifilm", "velvia", strength=1.0, rng=deterministic_rng())
    none = engine.render(buffer, "fujifilm", "velvia", strength=0.0, rng=deterministic_rng())
    base_only = engine.render(buffer, "fujifilm", "velvia", strength=0.0, rng=deterministic_rng())

    assert not np.allclose(full.data, none.data)
    np.testing.assert_allclose(none.data, base_only.data)


def test_unknown_base_profile_raises(loader: PresetLoader, buffer: ImageBuffer) -> None:
    from myphoto.core.errors import PresetNotFoundError

    engine = PresetEngine(loader)
    with pytest.raises(PresetNotFoundError):
        engine.render(buffer, "does-not-exist", "velvia")


@pytest.mark.parametrize(
    "film_simulation_id",
    [
        "provia", "velvia", "astia", "classic_chrome", "classic_neg",
        "eterna", "acros", "nostalgic_neg", "reala_ace",
    ],
)
def test_every_shipped_film_simulation_renders(
    loader: PresetLoader, buffer: ImageBuffer, film_simulation_id: str
) -> None:
    engine = PresetEngine(loader)
    result = engine.render(buffer, "fujifilm", film_simulation_id, strength=1.0)
    assert result.data.shape == buffer.data.shape
