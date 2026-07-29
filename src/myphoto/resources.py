"""Locates bundled resources (``presets/``, ``models/``) at runtime.

Works both from a source checkout (both directories live beside ``src/``)
and from a PyInstaller-frozen build (bundled as data and extracted under
``sys._MEIPASS``).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _find_bundled_dir(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / name
        if candidate.is_dir():
            return candidate

    for parent in Path(__file__).resolve().parents:
        candidate = parent / name
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(f"Could not locate the {name}/ directory")


def presets_dir() -> Path:
    return _find_bundled_dir("presets")


def face_detector_model_path() -> Path:
    """Path to the bundled ONNX face-detector model (see ``models/README.md``)."""
    return _find_bundled_dir("models") / "face_detector.onnx"
