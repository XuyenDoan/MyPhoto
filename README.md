# MyPhoto

A small, fast, and stable Windows desktop app that does exactly one thing
well: apply high-quality, Fujifilm-inspired film simulation color looks to
your photos.

MyPhoto is **not** a Lightroom or Photoshop replacement. There is no crop,
no layers, no brushes, no healing, no object removal, no AI portrait tools.
Just:

**Drag photos in → pick a Fujifilm-style color → export.**

## Features

- Drag & drop import: JPEG, PNG, TIFF, BMP, RAW
- Before/After preview with zoom
- Two-layer preset system: camera **Base Profile** normalization, then a
  **Film Simulation** look (Provia, Velvia, Astia, Classic Chrome,
  Classic Neg, Eterna, Acros, Nostalgic Neg, Reala Ace)
- Adjustable simulation **Strength** and **Film Grain**
- Batch export to JPEG/PNG/TIFF with quality, export folder, and rename
  pattern controls — never overwrites the original
- EXIF preserved where possible
- Color-managed pipeline (RAW decode → ICC → color space → tone/RGB
  curves → HSL → color balance → film simulation → 3D LUT → grain),
  16-bit/32-bit-float where supported

See [`docs/specs/MYPHOTO_CLAUDE_PROMPT.md`](docs/specs/MYPHOTO_CLAUDE_PROMPT.md)
for the full product specification driving this project, and
[`docs/Architecture.md`](docs/Architecture.md) for the technical design.

## Tech stack

Python 3.13+, PySide6, NumPy, Pillow, OpenCV (basic ops only), rawpy/LibRaw,
OpenColorIO, LittleCMS, OpenImageIO (where appropriate), 3D LUT / Hald CLUT,
piexif. Third-party color libraries are wrapped behind an Adapter Pattern —
MyPhoto only implements the Preset Engine, Workflow, Batch Processor, and UI
itself. See [`docs/Architecture.md`](docs/Architecture.md).

## Project status

First functional end-to-end version: Image Loader, Color Engine, Preset
Engine (8 Base Profiles, 9 Film Simulations), Export Engine, Batch
Processor, Settings, and the PySide6 GUI are all implemented and tested
(100+ unit tests, ruff- and strict-mypy-clean), and `pyinstaller
myphoto.spec` produces a working build. See [`CHANGELOG.md`](CHANGELOG.md)
for details and known limitations (e.g. ICC/EXIF embedding on 16-bit
PNG/TIFF export).

## Getting started (development)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest
python -m myphoto.app          # run the app
```

See [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md) for details.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
