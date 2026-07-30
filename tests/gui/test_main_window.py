from pathlib import Path

import numpy as np
from PIL import Image

from myphoto.gui.main_window import MainWindow
from myphoto.preset_engine.loader import PresetLoader
from myphoto.settings.store import SettingsStore

REPO_PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"


def _make_image(path: Path) -> None:
    array = (np.random.default_rng(0).random((10, 14, 3)) * 255).astype(np.uint8)
    Image.fromarray(array).save(path)


def _preset_loader() -> PresetLoader:
    return PresetLoader(REPO_PRESETS_DIR / "base_profiles", REPO_PRESETS_DIR / "film_simulations")


def test_window_constructs_and_populates_preset_dropdowns(qtbot, tmp_path: Path) -> None:
    window = MainWindow(_preset_loader(), SettingsStore(tmp_path / "settings.ini"))
    qtbot.addWidget(window)

    assert window._controls_panel._base_profile_combo.count() == 8
    assert window._controls_panel._film_simulation_combo.count() == 14
    # The dropdown selection must match what EditSession will actually render,
    # not just whatever preset happens to sort first alphabetically.
    assert window._controls_panel.selected_base_profile_id() == window._session.base_profile_id
    assert (
        window._controls_panel.selected_film_simulation_id()
        == window._session.film_simulation_id
    )


def test_dropping_images_triggers_preview(qtbot, tmp_path: Path) -> None:
    window = MainWindow(_preset_loader(), SettingsStore(tmp_path / "settings.ini"))
    qtbot.addWidget(window)

    photo = tmp_path / "photo.png"
    _make_image(photo)

    with qtbot.waitSignal(window._session.preview_ready, timeout=3000):
        window._image_list_panel.images_dropped.emit([photo])
        window._preview_debounce.start(0)

    assert window._preview_panel._rendered_pixmap is not None
    assert window._image_list_panel._list.count() == 1


def test_changing_film_simulation_updates_session_and_reschedules_preview(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(_preset_loader(), SettingsStore(tmp_path / "settings.ini"))
    qtbot.addWidget(window)
    photo = tmp_path / "photo.png"
    _make_image(photo)
    window._image_list_panel.images_dropped.emit([photo])
    qtbot.wait(50)

    window._controls_panel._film_simulation_combo.setCurrentIndex(1)
    new_id = window._controls_panel.selected_film_simulation_id()

    assert window._session.film_simulation_id == new_id
    assert window._preview_debounce.isActive()


def test_export_button_runs_batch_and_reports_completion(qtbot, tmp_path: Path) -> None:
    window = MainWindow(_preset_loader(), SettingsStore(tmp_path / "settings.ini"))
    qtbot.addWidget(window)

    photo = tmp_path / "photo.png"
    _make_image(photo)
    window._session.add_images([photo])
    window._controls_panel.set_output_dir(tmp_path / "out")

    with qtbot.waitSignal(window._session.batch_finished, timeout=5000):
        window._on_export_clicked()

    exported = list((tmp_path / "out").glob("*.jpg"))
    assert len(exported) == 1
    assert window._export_button.isEnabled()
