# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Android app** (`android/`), a native Kotlin/Jetpack Compose companion
  to the desktop app — see `docs/specs/ANDROID_ADDENDUM.md` for the scope
  decision and `docs/Architecture.md`'s Android section for the design.
  - `android/core`: pure Kotlin/JVM port of the Color Engine and Preset
    Engine (`ImageBuffer`, `ColorAdjustments`, `ColorOperations`,
    `ColorPipeline`, preset JSON (de)serialization via
    kotlinx.serialization, `PresetLoader`, `PresetEngine`) — no Android
    dependency, so it builds/tests with a plain JDK + Gradle. Reads the
    exact same `presets/` JSON files as the desktop app. 44 JUnit 5 tests,
    including one that loads and validates every preset shipped in
    `presets/`. Built and unit-tested successfully.
  - `android/app`: Jetpack Compose UI, system Photo Picker import
    (JPEG/PNG only — no RAW on Android), `MyPhotoViewModel` (mirrors
    desktop's `EditSession`: image list, current preset/strength/grain,
    debounced preview, batch export), `MediaStoreExporter` (exports to a
    `Pictures/MyPhoto` gallery album, never touching the original),
    DataStore-backed settings for last-used presets. **Written but not
    build-verified** — the development environment's network policy
    blocks `dl.google.com`/`maven.google.com` (Android Gradle
    Plugin/SDK); needs an Android Studio build + device/emulator smoke
    test before shipping. See `android/README.md`.

- `.github/workflows/android-build.yml`: builds `android/app`'s debug APK
  on GitHub Actions (runs `:core:test` first, then
  `:app:assembleDebug`) and uploads it as a downloadable artifact —
  works around this project's sandbox not having access to
  `dl.google.com`/`maven.google.com`, and lets anyone get an installable
  APK without setting up Android Studio locally.

### Fixed

- `ControlsPanel`'s Base Profile / Film Simulation dropdowns now select
  the preset `EditSession` actually starts with (`fujifilm`/`provia`)
  instead of defaulting to index 0 of the alphabetically sorted list
  (previously showing e.g. "Canon"/"Acros" while rendering with Fujifilm/
  Provia underneath — found via a manual screenshot walkthrough).

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
- `myphoto.gui`: `ImageListPanel` (drag & drop import), `PreviewPanel`
  (Before/After toggle, Ctrl+wheel zoom), `ControlsPanel` (Base Profile /
  Film Simulation dropdowns, Strength and Film Grain sliders, export
  format/quality/folder/rename-pattern), and `MainWindow`, which wires
  them all to `EditSession` with a debounced preview re-render.
- `myphoto.app.main()`: the process entry point (`myphoto` console
  script), plus `myphoto.resources.presets_dir()` to locate the bundled
  `presets/` directory from both a source checkout and a PyInstaller
  build.
- 102 unit tests total (including full-window smoke tests: preset
  dropdowns populate, drop-to-preview, control changes reschedule
  preview, Export button drives a real batch export); ruff and strict
  mypy clean.
- `myphoto.spec`: PyInstaller build spec bundling `presets/`. Verified
  end to end on Linux with an offscreen Qt platform (builds, launches,
  resolves the bundled presets directory via `sys._MEIPASS`, runs the
  Qt event loop without crashing) — a Windows build should still be
  smoke-tested before shipping, since PyInstaller's Windows path has
  its own quirks not exercised on Linux.
