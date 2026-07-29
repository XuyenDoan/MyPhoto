from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from myphoto.core.image import ImageBuffer
from myphoto.export_engine.models import ExportOptions
from myphoto.preset_engine.loader import PresetLoader
from myphoto.workflow.session import EditSession

REPO_PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"


@pytest.fixture
def preset_loader() -> PresetLoader:
    return PresetLoader(REPO_PRESETS_DIR / "base_profiles", REPO_PRESETS_DIR / "film_simulations")


@pytest.fixture
def session(preset_loader: PresetLoader) -> EditSession:
    return EditSession(preset_loader)


def _make_image(path: Path) -> None:
    array = (np.random.default_rng(0).random((6, 8, 3)) * 255).astype(np.uint8)
    Image.fromarray(array).save(path)


def test_add_images_selects_first_and_ignores_duplicates(session: EditSession, tmp_path: Path) -> None:
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    events = []
    session.images_changed.connect(lambda: events.append(1))

    session.add_images([a, b, a])

    assert session.image_paths == [a, b]
    assert session.current_index == 0
    assert len(events) == 1


def test_remove_image_adjusts_current_index(session: EditSession, tmp_path: Path) -> None:
    paths = [tmp_path / f"{i}.png" for i in range(3)]
    session.add_images(paths)
    session.select(2)

    session.remove_image(2)

    assert session.image_paths == paths[:2]
    assert session.current_index == 1


def test_remove_last_image_clears_selection(session: EditSession, tmp_path: Path) -> None:
    session.add_images([tmp_path / "a.png"])
    session.remove_image(0)
    assert session.current_index is None


def test_select_out_of_range_raises(session: EditSession) -> None:
    with pytest.raises(IndexError):
        session.select(0)


def test_render_preview_without_selection_is_noop(session: EditSession) -> None:
    events = []
    session.preview_ready.connect(lambda *_: events.append(1))
    session.preview_failed.connect(lambda *_: events.append(1))
    session.render_preview()
    assert events == []


def test_render_preview_success(session: EditSession, tmp_path: Path, qtbot) -> None:
    path = tmp_path / "photo.png"
    _make_image(path)
    session.add_images([path])
    session.base_profile_id = "fujifilm"
    session.film_simulation_id = "velvia"

    with qtbot.waitSignal(session.preview_ready, timeout=2000) as blocker:
        session.render_preview()

    original, rendered = blocker.args
    assert isinstance(original, ImageBuffer)
    assert isinstance(rendered, ImageBuffer)
    assert rendered.data.shape == original.data.shape


def test_render_preview_failure_emits_preview_failed(session: EditSession, tmp_path: Path, qtbot) -> None:
    session.add_images([tmp_path / "missing.png"])

    with qtbot.waitSignal(session.preview_failed, timeout=2000) as blocker:
        session.render_preview()

    assert blocker.args[0]


def test_auto_suggest_updates_film_simulation_and_emits_signal(
    session: EditSession, tmp_path: Path, qtbot, monkeypatch
) -> None:
    # face_confidence comes from a real pretrained face detector; mock it
    # here since this test is about the session/signal wiring, not about
    # whether a tiny synthetic patch happens to look like a real face.
    monkeypatch.setattr("myphoto.preset_engine.auto_suggest._face_confidence", lambda buffer: 0.95)

    path = tmp_path / "portrait.png"
    skin_tone = np.tile(np.array([204, 153, 128], dtype=np.uint8), (8, 8, 1))
    Image.fromarray(skin_tone, mode="RGB").save(path)
    session.add_images([path])
    session.film_simulation_id = "velvia"  # deliberately not what auto-suggest should pick
    session.auto_suggest_enabled = True

    with qtbot.waitSignal(session.film_simulation_suggested, timeout=2000) as blocker:
        session.render_preview()

    assert blocker.args[0] == "astia"
    assert session.film_simulation_id == "astia"


def test_local_balance_affects_rendered_but_not_original_preview(
    session: EditSession, tmp_path: Path, qtbot
) -> None:
    path = tmp_path / "photo.png"
    array = np.zeros((32, 32, 3), dtype=np.uint8)
    array[:, :16] = 250  # overexposed left half
    array[:, 16:] = 5  # underexposed right half
    Image.fromarray(array, mode="RGB").save(path)
    session.add_images([path])
    session.base_profile_id = "fujifilm"
    session.film_simulation_id = "provia"
    session.local_balance_enabled = True

    with qtbot.waitSignal(session.preview_ready, timeout=2000) as blocker:
        session.render_preview()

    original, rendered = blocker.args
    # "Show Original" must stay the true source, unaffected by the correction.
    assert np.array_equal(original.data, array.astype(np.float32) / 255.0)
    # The overexposed region should read darker after correction+rendering.
    assert rendered.data[:, :16].mean() < original.data[:, :16].mean()


def test_chromatic_aberration_fix_affects_rendered_but_not_original_preview(
    session: EditSession, tmp_path: Path, qtbot
) -> None:
    path = tmp_path / "photo.png"
    array = np.full((32, 32, 3), 200, dtype=np.uint8)
    array[:, 16:] = (20, 20, 20)  # a strong edge down the middle
    array[:, 15] = (150, 40, 140)  # purple fringe column right on the edge
    Image.fromarray(array, mode="RGB").save(path)
    session.add_images([path])
    session.fix_chromatic_aberration_enabled = True

    with qtbot.waitSignal(session.preview_ready, timeout=2000) as blocker:
        session.render_preview()

    original, rendered = blocker.args
    assert np.array_equal(original.data, array.astype(np.float32) / 255.0)
    original_chroma = original.data[0, 15].max() - original.data[0, 15].min()
    rendered_chroma = rendered.data[0, 15].max() - rendered.data[0, 15].min()
    assert rendered_chroma < original_chroma


def test_auto_sharpen_increases_edge_contrast(session: EditSession, tmp_path: Path, qtbot) -> None:
    path = tmp_path / "photo.png"
    array = np.zeros((32, 32, 3), dtype=np.uint8)
    array[:, :16] = 200
    array[:, 16:] = 40
    Image.fromarray(array, mode="RGB").save(path)
    session.add_images([path])
    session.base_profile_id = "fujifilm"
    session.film_simulation_id = "provia"
    session.auto_sharpen_enabled = True

    with qtbot.waitSignal(session.preview_ready, timeout=2000) as blocker:
        session.render_preview()

    original, rendered = blocker.args
    assert np.array_equal(original.data, array.astype(np.float32) / 255.0)
    # Right at the edge, sharpening should widen the gap between the two sides.
    original_gap = original.data[:, 14].mean() - original.data[:, 17].mean()
    rendered_gap = rendered.data[:, 14].mean() - rendered.data[:, 17].mean()
    assert rendered_gap >= original_gap


def test_composition_suggest_emits_suggestion_when_enabled(
    session: EditSession, tmp_path: Path, qtbot, monkeypatch
) -> None:
    from myphoto.color_engine.composition_suggest import CropSuggestion

    fake_suggestion = CropSuggestion(x=1, y=2, width=3, height=4, target_thirds_point=(1 / 3, 1 / 3), source="face")
    monkeypatch.setattr("myphoto.workflow.session.suggest_crop", lambda buffer: fake_suggestion)

    path = tmp_path / "photo.png"
    _make_image(path)
    session.add_images([path])
    session.composition_suggest_enabled = True

    with qtbot.waitSignal(session.composition_suggested, timeout=2000) as blocker:
        session.render_preview()

    assert blocker.args[0] is fake_suggestion


def test_composition_suggest_disabled_emits_nothing(
    session: EditSession, tmp_path: Path, qtbot
) -> None:
    path = tmp_path / "photo.png"
    _make_image(path)
    session.add_images([path])
    session.composition_suggest_enabled = False

    events: list[object] = []
    session.composition_suggested.connect(lambda suggestion: events.append(suggestion))

    with qtbot.waitSignal(session.preview_ready, timeout=2000):
        session.render_preview()

    assert events == []


def test_auto_level_crops_rendered_but_not_original_preview(
    session: EditSession, tmp_path: Path, qtbot
) -> None:
    import cv2

    def tilted_horizon(size: int = 300, degrees: float = 8.0) -> np.ndarray:
        rgb = np.zeros((size, size, 3), dtype=np.float32)
        rgb[: size // 2] = (0.85, 0.85, 0.9)
        rgb[size // 2 :] = (0.15, 0.35, 0.15)
        matrix = cv2.getRotationMatrix2D((size / 2, size / 2), degrees, 1.0)
        return cv2.warpAffine(rgb, matrix, (size, size), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    path = tmp_path / "tilted.png"
    array = (tilted_horizon() * 255).astype(np.uint8)
    Image.fromarray(array, mode="RGB").save(path)
    session.add_images([path])
    session.auto_level_enabled = True

    with qtbot.waitSignal(session.preview_ready, timeout=2000) as blocker:
        session.render_preview()

    original, rendered = blocker.args
    assert original.height == 300 and original.width == 300
    assert rendered.height < 300
    assert rendered.width < 300


def test_export_all_forwards_batch_finished(session: EditSession, tmp_path: Path, qtbot) -> None:
    path = tmp_path / "photo.png"
    _make_image(path)
    session.add_images([path])
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")

    with qtbot.waitSignal(session.batch_finished, timeout=5000) as blocker:
        session.export_all(options)

    results = blocker.args[0]
    assert len(results) == 1
    assert results[0].succeeded
