"""Reads/writes :class:`AppSettings` via ``QSettings`` (INI format)."""

from __future__ import annotations

from pathlib import Path
from typing import get_args

from PySide6.QtCore import QSettings, QStandardPaths

from myphoto.settings.models import AppSettings, Theme

_VALID_THEMES: tuple[Theme, ...] = get_args(Theme)


def default_settings_path() -> Path:
    """The per-user config file MyPhoto uses when no explicit path is given."""
    config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    return Path(config_dir) / "MyPhoto" / "settings.ini"


class SettingsStore:
    """Persists :class:`AppSettings` to an INI file via ``QSettings``."""

    def __init__(self, path: Path | None = None) -> None:
        resolved_path = path if path is not None else default_settings_path()
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = QSettings(str(resolved_path), QSettings.Format.IniFormat)

    def load(self) -> AppSettings:
        theme = self._settings.value("appearance/theme", "system", type=str)
        return AppSettings(
            last_base_profile_id=self._read_optional_str("preset/base_profile_id"),
            last_film_simulation_id=self._read_optional_str("preset/film_simulation_id"),
            last_folder=self._read_optional_path("paths/last_folder"),
            export_folder=self._read_optional_path("paths/export_folder"),
            theme=theme if theme in _VALID_THEMES else "system",
        )

    def save(self, settings: AppSettings) -> None:
        self._settings.setValue("preset/base_profile_id", settings.last_base_profile_id or "")
        self._settings.setValue(
            "preset/film_simulation_id", settings.last_film_simulation_id or ""
        )
        self._settings.setValue(
            "paths/last_folder", str(settings.last_folder) if settings.last_folder else ""
        )
        self._settings.setValue(
            "paths/export_folder", str(settings.export_folder) if settings.export_folder else ""
        )
        self._settings.setValue("appearance/theme", settings.theme)
        self._settings.sync()

    def _read_optional_str(self, key: str) -> str | None:
        value = str(self._settings.value(key, "", type=str))
        return value or None

    def _read_optional_path(self, key: str) -> Path | None:
        value = self._read_optional_str(key)
        return Path(value) if value else None
