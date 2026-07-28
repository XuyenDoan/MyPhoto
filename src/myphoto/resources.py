"""Locates bundled resources (currently just ``presets/``) at runtime.

Works both from a source checkout (``presets/`` lives beside ``src/``) and
from a PyInstaller-frozen build (``presets/`` is bundled as data and
extracted under ``sys._MEIPASS``).
"""

from __future__ import annotations

import sys
from pathlib import Path


def presets_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / "presets"
        if candidate.is_dir():
            return candidate

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "presets"
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError("Could not locate the presets/ directory")
