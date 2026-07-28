from pathlib import Path

from myphoto.settings.models import AppSettings
from myphoto.settings.store import SettingsStore


def test_load_before_save_returns_defaults(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.ini")
    settings = store.load()

    assert settings == AppSettings()


def test_round_trips_all_fields(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.ini")
    original = AppSettings(
        last_base_profile_id="fujifilm",
        last_film_simulation_id="velvia",
        last_folder=tmp_path / "imports",
        export_folder=tmp_path / "exports",
        theme="dark",
    )

    store.save(original)
    reloaded = SettingsStore(tmp_path / "settings.ini").load()

    assert reloaded == original


def test_unknown_theme_falls_back_to_system(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    store = SettingsStore(path)
    store.save(AppSettings(theme="dark"))
    path.write_text(path.read_text().replace("dark", "not-a-theme"), encoding="utf-8")

    reloaded = SettingsStore(path).load()

    assert reloaded.theme == "system"


def test_creates_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "settings.ini"
    SettingsStore(nested)
    assert nested.parent.is_dir()
