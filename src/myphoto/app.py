"""Application entry point: ``python -m myphoto.app`` or the ``myphoto`` script."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from myphoto.gui.main_window import MainWindow
from myphoto.preset_engine.loader import PresetLoader
from myphoto.resources import presets_dir
from myphoto.settings.store import SettingsStore


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MyPhoto")
    app.setOrganizationName("MyPhoto")

    presets_root = presets_dir()
    preset_loader = PresetLoader(presets_root / "base_profiles", presets_root / "film_simulations")
    settings_store = SettingsStore()

    window = MainWindow(preset_loader, settings_store)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
