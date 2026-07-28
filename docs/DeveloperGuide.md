# Developer Guide

## Requirements

- Python 3.13+
- Windows (primary target); development also works on Linux/macOS since
  the stack (PySide6, NumPy, OpenCV, etc.) is cross-platform.

## Setup

```bash
git clone https://github.com/XuyenDoan/MyPhoto.git
cd MyPhoto
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"
```

## Project layout

```
src/myphoto/
  gui/             PySide6 windows, widgets, preview/before-after view
  workflow/         Orchestrates GUI ↔ Preset Engine ↔ Color Engine ↔ Export Engine
  preset_engine/    Loads/applies two-layer JSON presets (base profile + film sim)
  color_engine/     Color pipeline; adapters/ wraps LibRaw, OCIO, LittleCMS, OIIO, OpenCV
  export_engine/    Writes JPEG/PNG/TIFF, EXIF, rename patterns
  image_loader/     Reads JPEG/PNG/TIFF/BMP/RAW into the internal image representation
  batch/            QThreadPool-based batch export with progress/cancel
  settings/         Persists last preset, last folder, export folder, theme
  core/             Shared domain types and pipeline contracts

presets/            JSON preset files (base profiles + film simulations)
tests/              Unit tests, mirroring the src/myphoto package layout
docs/               Architecture, this guide, and the product spec
```

## Running tests

```bash
pytest --cov
```

## Linting & type checking

```bash
ruff check .
mypy src
```

## Adding a color library adapter

1. Define (or extend) the relevant protocol in `color_engine/` (e.g. a
   `RawDecoder` or `ColorTransform` interface).
2. Implement it in `color_engine/adapters/<library>_adapter.py`.
3. Never import the third-party library outside `color_engine/adapters/`.
4. Add unit tests under `tests/color_engine/`.

## Adding a preset

Presets are JSON files under `presets/`. Do not hardcode preset values in
Python — the Preset Engine discovers and loads files from disk. The exact
schema is documented in `docs/Architecture.md` once the Preset Engine
ships; until then, treat any preset format changes as part of that PR.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/) — see
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Running the app

```bash
python -m myphoto.app
# or, after `pip install -e .`:
myphoto
```

## Building a Windows executable

```bash
pyinstaller myphoto.spec
```

Produces a `dist/MyPhoto/` folder (`MyPhoto.exe` on Windows) with
`presets/` bundled alongside it under `_internal/` — `myphoto.resources.
presets_dir()` finds it there via `sys._MEIPASS` at runtime. Verified end
to end on Linux (offscreen Qt platform); cross-check on Windows before
shipping, since PyInstaller's Windows build has its own quirks (codesigning,
antivirus false positives, etc.) not exercised here.
