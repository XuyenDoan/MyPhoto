# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project scaffolding: `src/myphoto` package layout (gui, workflow,
  preset_engine, color_engine + adapters, export_engine, image_loader,
  batch, settings, core), `tests/`, `presets/`.
- Project docs: README, LICENSE (MIT), CONTRIBUTING, Architecture,
  DeveloperGuide.
- Product specification committed at `docs/specs/MYPHOTO_CLAUDE_PROMPT.md`.
- Packaging config: `pyproject.toml`, `requirements.txt`, `.gitignore`.
- `myphoto.core.ImageBuffer`: the internal normalized-float32 image
  representation shared by every pipeline stage, plus `MyPhotoError`,
  `UnsupportedFormatError`, and `ImageDecodeError`.
- `myphoto.image_loader.ImageLoader`: decodes JPEG/PNG/TIFF/BMP via Pillow
  and RAW formats (CR2/CR3/NEF/ARW/RAF/ORF/RW2/DNG/...) via rawpy/LibRaw
  into `ImageBuffer`, preserving source bit depth, ICC profile (raster),
  and best-effort EXIF metadata.
- Unit tests for `core.ImageBuffer` and `image_loader` (format detection,
  8-bit/16-bit decoding, missing/unsupported/corrupt file handling).
- `myphoto.color_engine`: `ColorAdjustments`/`ColorBalanceAdjustment`
  parameter model (with `.scaled(strength)` for the Strength slider) and
  `ColorPipeline`, applying White Balance, Exposure, Tone Curve, RGB
  Curve, HSL, Color Balance, 3D LUT (Film Simulation), and Film Grain in
  the spec's pipeline order. Color math is behind a `ColorMath` adapter
  (Adapter Pattern), currently backed by OpenCV.
- `myphoto.preset_engine`: `PresetLoader` (discovers `*.json` presets from
  `presets/base_profiles/` and `presets/film_simulations/`, no hardcoding)
  and `PresetEngine.render()` implementing the Two-Layer Preset System.
- Shipped presets: 8 camera Base Profiles (Sony, Canon, Nikon, Fujifilm,
  OM System, Panasonic, Leica, iPhone) and 9 Film Simulations (Provia,
  Velvia, Astia, Classic Chrome, Classic Neg, Eterna, Acros, Nostalgic
  Neg, Reala Ace) — original color-style approximations, not decompiled
  proprietary algorithms.
- `myphoto.export_engine`: `ExportEngine.export()` writes JPEG (8-bit,
  via Pillow, with ICC + EXIF preservation) and PNG/TIFF (16-bit when the
  source supports it, via OpenCV) to a caller-chosen output directory,
  never overwriting the source image. `ExportOptions`/`build_output_path`
  support quality, output folder, and a `{stem}/{name}/{index}` rename
  pattern.
- `myphoto.image_loader.exif_utils.extract_exif` now returns the raw
  piexif IFD structure (instead of a flattened display dict) so EXIF can
  round-trip correctly through export.
- `myphoto.settings`: `AppSettings`/`SettingsStore`, persisting last base
  profile, last film simulation, last folder, export folder, and theme to
  an INI file via `QSettings`.
- `myphoto.batch`: `BatchJob`/`BatchItemResult`/`BatchProcessor`, running
  batch export on a `QThreadPool` with per-item progress and cooperative
  cancellation, without blocking the UI thread.
- `PresetEngine.render()` gains a `grain_amount` override, independent of
  `strength`, backing a separate Film Grain slider; `BatchJob` gained the
  matching `grain_amount` field.
- `myphoto.workflow.EditSession`: the GUI-facing orchestrator — image
  list management, current preset/strength/grain state,
  `render_preview()` (downsampled for interactive speed) and
  `export_all()` (delegates to `BatchProcessor` at full resolution).
- 98 unit tests total; ruff and strict mypy clean.
