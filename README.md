# MyPhoto

A small, fast, and stable app — Windows desktop and Android — that does
exactly one thing well: apply high-quality, Fujifilm-inspired film
simulation color looks to your photos.

MyPhoto is **not** a Lightroom or Photoshop replacement. There is no crop,
no layers, no brushes, no healing, no object removal, no AI portrait tools.
Just:

**Pick photos in → pick a Fujifilm-style color → export.**

## Features

- Drag & drop import: JPEG, PNG, TIFF, BMP, RAW
- Before/After preview with zoom
- Two-layer preset system: camera **Base Profile** normalization, then a
  **Film Simulation** look (Provia, Velvia, Astia, Classic Chrome,
  Classic Neg, PRO Neg. Hi, PRO Neg. Std, Eterna, Eterna Bleach Bypass,
  Acros, Sepia, Nostalgic Neg, Reala Ace)
- Optional **Auto-Balance Light & Color** (beta) — corrects over/under-
  exposed and over-saturated *regions* of a photo independently (not one
  global slider), before the preset is applied; deterministic, offline
- Optional **Auto-suggest Film Simulation** (beta) — picks a preset from
  the photo's color statistics plus a real local face detector (small
  ONNX model, fully offline, no cost); always overridable
- Adjustable simulation **Strength**; **Film Grain** is opt-in via a
  checkbox (off by default) plus an amount slider
- Batch export to JPEG/PNG/TIFF with quality and export folder controls,
  running in parallel across the machine's CPU cores (one core held back
  for UI responsiveness) — never overwrites the original; exported files
  get a `_myphoto` suffix so an edited photo is never mistaken for its
  source
- EXIF preserved where possible
- Color-managed pipeline (RAW decode → ICC → color space → tone/RGB
  curves → HSL → color balance → film simulation → 3D LUT → grain),
  16-bit/32-bit-float where supported

See [`docs/specs/MYPHOTO_CLAUDE_PROMPT.md`](docs/specs/MYPHOTO_CLAUDE_PROMPT.md)
for the full product specification driving this project,
[`docs/specs/ANDROID_ADDENDUM.md`](docs/specs/ANDROID_ADDENDUM.md) for the
Android-specific scope, and [`docs/Architecture.md`](docs/Architecture.md)
for the technical design of both platforms.

## Tech stack

**Desktop:** Python 3.13+, PySide6, NumPy, Pillow, OpenCV (basic ops
only), rawpy/LibRaw, OpenColorIO, LittleCMS, OpenImageIO (where
appropriate), 3D LUT / Hald CLUT, piexif, onnxruntime (a small local face
detector backing auto-suggest — see Architecture.md). Third-party color
libraries are wrapped behind an Adapter Pattern — MyPhoto only implements
the Preset Engine, Workflow, Batch Processor, and UI itself.

**Android:** Kotlin + Jetpack Compose, a pure-Kotlin `core` module
mirroring the desktop Color/Preset Engines, MediaStore for export, the
system Photo Picker for import (JPEG/PNG only — no RAW on this platform).

See [`docs/Architecture.md`](docs/Architecture.md) for details on both.

## Project status

**Desktop:** first functional end-to-end version — Image Loader, Color
Engine, Preset Engine (8 Base Profiles, 13 Film Simulations), Export
Engine, Batch Processor, Settings, and the PySide6 GUI are all
implemented and tested (100+ unit tests, ruff- and strict-mypy-clean),
and `pyinstaller myphoto.spec` produces a working build.

**Android:** `android/core` (the color/preset engine port) is implemented
and unit-tested (44 JUnit tests, pure Kotlin/JVM). `android/app` (the
Compose UI, MediaStore export, Photo Picker import) is implemented but
**not yet build-verified** — it needs to be opened in Android Studio and
smoke-tested on a device/emulator; see
[`android/README.md`](android/README.md) for why and what to check.

See [`CHANGELOG.md`](CHANGELOG.md) for full details and known limitations
(e.g. ICC/EXIF embedding on 16-bit PNG/TIFF export on desktop).

## Getting started (development)

### Desktop

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest
python -m myphoto.app          # run the app
```

See [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md) for details.

### Android

```bash
cd android
./gradlew :core:test           # pure Kotlin/JVM, no Android SDK required
```

Open `android/` in Android Studio to build/run `:app`. See
[`android/README.md`](android/README.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
