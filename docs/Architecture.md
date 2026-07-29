# Architecture

Full product spec: [`specs/MYPHOTO_CLAUDE_PROMPT.md`](specs/MYPHOTO_CLAUDE_PROMPT.md).

## Guiding principle

MyPhoto does not reimplement RAW decoding, color management, or LUT math
from scratch. It wraps proven open-source libraries behind adapters and
keeps its own code focused on four things: the **Preset Engine**, the
**Workflow**, the **Batch Processor**, and the **UI**.

## Layers

```
GUI
 │
 ▼
Workflow
 │
 ▼
Preset Engine
 │
 ▼
Color Engine  (adapters over LibRaw/rawpy, OpenColorIO, LittleCMS, OpenImageIO, OpenCV)
 │
 ▼
Export Engine
 │
 ▼
Image Loader
```

Each layer is an independent module with a narrow interface; the GUI never
talks to the Color Engine or Image Loader directly — only through Workflow.

Mapped to `src/myphoto/`:

| Layer          | Package                          |
|----------------|-----------------------------------|
| GUI            | `myphoto.gui`                     |
| Workflow       | `myphoto.workflow`                |
| Preset Engine  | `myphoto.preset_engine`           |
| Color Engine   | `myphoto.color_engine` (+ `.adapters`) |
| Export Engine  | `myphoto.export_engine`           |
| Image Loader   | `myphoto.image_loader`            |
| Batch Processor| `myphoto.batch`                   |
| Settings       | `myphoto.settings`                |
| Shared domain  | `myphoto.core`                    |

## Color pipeline

Processing order for a single image:

```
Image Loader → RAW Decoder → ICC Profile → Color Space → White Balance →
Exposure → Tone Curve → RGB Curve → HSL → Color Balance →
Film Simulation → 3D LUT → Film Grain → Export
```

Library priority per the spec, from most- to least-preferred, chosen per
operation:

1. LibRaw / rawpy — RAW decoding
2. OpenColorIO — color space transforms, LUT application
3. LittleCMS — ICC profile handling
4. OpenImageIO — I/O for formats/bit depths where it's the better fit
5. OpenCV — only for basic array operations not covered above

Every call into one of these libraries goes through an adapter in
`color_engine/adapters/`, implementing a small internal protocol (e.g.
`RawDecoder`, `ColorTransform`, `LutApplier`). This keeps the pipeline
swappable and testable without depending on a specific library's API
throughout the codebase.

## Two-layer preset system

1. **Base Profile** — normalizes color response per camera manufacturer
   (Sony, Canon, Nikon, Fujifilm, OM System, Panasonic, Leica, iPhone)
   before any creative look is applied.
2. **Film Simulation** — applies a Fujifilm-inspired look (Provia, Velvia,
   Astia, Classic Chrome, Classic Neg, PRO Neg. Hi, PRO Neg. Std, Eterna,
   Eterna Bleach Bypass, Acros, Sepia, Nostalgic Neg, Reala Ace) on top of
   the normalized image. These are original simulations of a visual style,
   not decompiled/copied proprietary algorithms.

Presets are plain JSON files loaded at runtime from `presets/base_profiles/`
and `presets/film_simulations/` (and later a user presets directory) —
never hardcoded. `PresetLoader` scans both directories for `*.json` files;
`PresetEngine.render()` runs an image through the Base Profile's adjustments
via `ColorPipeline`, then through the Film Simulation's adjustments (scaled
by the UI's Strength value via `ColorAdjustments.scaled()`), optionally
applying an associated 3D LUT (`.npy`, shape `(N, N, N, 3)`). The full JSON
schema is documented in `presets/README.md` and
`myphoto.preset_engine.serialization`.

## Export Engine

`myphoto.export_engine.ExportEngine.export()` writes a processed
`ImageBuffer` to JPEG, PNG, or TIFF:

- **JPEG** is always 8-bit (the format has no higher-depth mode) and is
  written via Pillow, which supports embedding both the ICC profile and
  EXIF (`piexif.insert` after save).
- **PNG/TIFF** are written via OpenCV at 16-bit/channel whenever the
  source had more than 8 bits of precision, since Pillow cannot encode a
  3-channel 16-bit image (`Image.fromarray` only supports single-channel
  16-bit "I;16"). This preserves pixel precision but currently does not
  embed ICC/EXIF for the 16-bit path — `piexif.insert` requires a
  JPEG/TIFF layout it recognizes, which OpenCV's writer doesn't produce.
  A future OpenImageIO or LittleCMS adapter (see Color Engine section)
  could close this gap without changing the `ExportEngine` interface.

`ExportOptions` never lets the resolved output path equal the source path
— exporting always requires (and creates) a separate output directory.
Filenames are the source stem plus a fixed `export_engine.naming.EXPORT_SUFFIX`
(`_myphoto`) plus the format's extension, via `naming.build_output_path` —
e.g. `IMG_0001.jpg` exports as `IMG_0001_myphoto.jpg`, so an edited photo is
never mistaken for its untouched source sitting in the same folder.

## Workflow

`myphoto.workflow.EditSession` is the single object the GUI reads from and
calls into — it owns the imported image list, current selection, and
current Base Profile/Film Simulation/Strength/Grain state, and wires a
`PresetEngine` + `BatchProcessor` together:

- `render_preview()` loads the selected image, downsamples it
  (`workflow.preview.downscaled`, longer side capped at 1600px) for
  interactive speed, optionally re-picks `film_simulation_id` when
  `auto_suggest_enabled` is set (see below), runs it through
  `PresetEngine.render()`, and emits `preview_ready(original, rendered)` or
  `preview_failed(message)` — this is what backs the Before/After view.
- `export_all(export_options)` builds a `BatchJob` from the full image
  list and current settings and hands it to `BatchProcessor`, forwarding
  its `progress`/`item_finished`/`finished` signals. Batch export always
  processes full-resolution buffers; only the preview is downsampled.

The `Strength` slider scales the film simulation's whole adjustment set
(`ColorAdjustments.scaled()`); the `Film Grain` slider is independent —
`PresetEngine.render(..., grain_amount=...)` overrides the final grain
intensity after strength scaling, so a user can dial grain up or down
without changing how strongly the rest of the look is applied.

### Auto-suggest Film Simulation

`preset_engine.auto_suggest.suggest_film_simulation_id()` is a
deterministic nearest-centroid classifier — not a trained ML model, no
bundled weights, nothing sent over the network. It computes simple
statistics from the loaded image (warmth, brightness, contrast, mean
saturation, and the fraction of pixels that fall in typical skin-tone or
foliage/sky hue ranges, via `OpenCVColorMath.rgb_to_hls`), then finds
whichever shipped Film Simulation's hand-authored "typical photo" feature
vector is closest (normalized Euclidean distance across all 6 features at
once). Distance-based matching deliberately avoids the failure mode of a
simple weighted-sum score, where one dominant signal (e.g. overall
saturation) could push a vivid preset to the top for almost any colorful
photo — a photo only matches Velvia when it's close to *both* landscape
content and real vividness simultaneously, not from one strong feature
alone. Provia's centroid sits at roughly typical photo values, so
ambiguous/ordinary photos land on it by default. `EditSession.auto_suggest_enabled`
(off by default) gates
whether `render_preview()` calls it; when it changes `film_simulation_id`,
`film_simulation_suggested(str)` fires so `ControlsPanel` can move its
dropdown to match. This is a fast, offline, always-overridable starting
point — not a claim of "correctness"; a real learned scene classifier
(local ONNX model or a cloud vision API) is a substantially larger project
and was deliberately left out of scope here.

## Batch processing

`myphoto.batch.BatchProcessor` runs a `BatchJob` (source images + preset +
strength + `ExportOptions`) on a dedicated `QThreadPool` sized to
`QThread.idealThreadCount() - 1` (minimum 1) — one core deliberately left
free so the CPU-bound decode/render/encode work on every other core
doesn't starve the Qt event loop and make the UI stutter — one
`BatchItemRunnable` (load -> `PresetEngine.render` -> `ExportEngine.export`)
per image, all queued at once so the pool keeps every worker thread busy
across the whole batch. It emits `progress(completed, total)` and
`item_finished(BatchItemResult)` after each item, and
`finished(list[BatchItemResult])` once every item is done; `cancel()` makes
not-yet-started items short-circuit to a `"cancelled"` result. The UI
thread never blocks on image processing.

Each `QRunnable` is created with `setAutoDelete(False)` and kept alive by
the processor until it finishes — PySide6 can otherwise garbage-collect a
runnable (and the Qt signal object it owns) mid-emit and crash.

## Quality priorities

1. Color accuracy
2. No quality loss from source to export
3. 16-bit intermediate representation, 32-bit float where the pipeline
   stage supports it
4. Linear-light operations where color-correct, gamma-correct handling at
   display/encode boundaries

## GUI

`myphoto.gui` implements the four-region layout from the spec on top of
`EditSession`:

- `ImageListPanel` (left) — a `QListWidget` accepting drag & drop of
  supported files, emitting `images_dropped`/`selection_changed`.
- `PreviewPanel` (center) — shows either the rendered or (via a "Show
  Original" checkbox) the original image, fit to the available viewport by
  default (preserving the photo's own aspect ratio, so portrait photos
  render tall and landscape photos render wide, instead of a fixed-shape
  crop), with Ctrl+wheel zooming further in/out from that fitted baseline.
- `ControlsPanel` (right) — Base Profile / Film Simulation dropdowns
  (populated from `PresetLoader`), an Auto-suggest Film Simulation
  checkbox (off by default; disables the dropdown while on), a Strength
  slider, a Film Grain checkbox (off by default) + amount slider, and the
  export destination fields (format, quality, output folder).
- A bottom bar — progress bar, Cancel, and Export buttons.
- `myphoto.gui.theme` applies a dark Fusion palette + QSS stylesheet
  application-wide (accent color, styled group boxes/buttons/sliders/
  scrollbars) for a more polished look than Qt's default widget style.

`MainWindow` wires these to `EditSession` and debounces preview
re-renders (150ms `QTimer`) so dragging a slider doesn't trigger a render
per pixel of mouse movement. `myphoto.app.main()` is the process entry
point (`myphoto` console script); it resolves the bundled `presets/`
directory via `myphoto.resources.presets_dir()`, which works both from a
source checkout and from a PyInstaller-frozen build.

## Android

A native Android app was added alongside the Windows desktop app, per the
decision recorded in
[`docs/specs/ANDROID_ADDENDUM.md`](specs/ANDROID_ADDENDUM.md): a separate
Kotlin codebase under `android/`, not an attempt to run the PySide6 app on
a phone (PySide6/rawpy/OpenCV don't meaningfully target Android).

`android/core` is a pure-Kotlin/JVM module — no Android dependency — that
mirrors `src/myphoto/color_engine` and `src/myphoto/preset_engine`
operation-for-operation:

| Desktop (Python)                                | Android (Kotlin)                         |
|--------------------------------------------------|-------------------------------------------|
| `core.ImageBuffer`                                | `core.ImageBuffer` (flat `FloatArray`)     |
| `color_engine.adjustments.ColorAdjustments`       | `core.ColorAdjustments`                    |
| `color_engine.operations`                         | `core.ColorOperations`                     |
| `color_engine.pipeline.ColorPipeline`             | `core.ColorPipeline`                       |
| `preset_engine.serialization`                     | `core.PresetSerialization` (kotlinx.serialization) |
| `preset_engine.loader.PresetLoader`               | `core.PresetLoader` (via a `PresetSource` interface — `AssetPresetSource` on Android) |
| `preset_engine.engine.PresetEngine`               | `core.PresetEngine`                        |

Both sides read the **same JSON files** from the repo-root `presets/` —
Android's `:app` module copies them into `assets/presets/` at build time
(see the `copyPresets` Gradle task in `android/app/build.gradle.kts`), so
there is exactly one source of truth for preset parameters across
platforms, per the "Preset lưu dạng JSON, không hardcode" rule.

`android/app` is the Jetpack Compose application: Android's system Photo
Picker for import (JPEG/PNG/HEIC — no RAW, see the addendum), a
`MyPhotoViewModel` that plays the same role as desktop's `EditSession`
(image list, current preset/strength/grain, debounced preview render,
batch export), and `MediaStoreExporter`, which writes exports into a
`Pictures/MyPhoto` gallery album — every export is a new MediaStore item,
so (like the desktop Export Engine) the original is never overwritten.

See [`android/README.md`](../android/README.md) for build instructions
and the full scope-difference list. `:core` was built and unit-tested in
this project's development environment (44 JUnit tests); `:app` needed
the Android Gradle Plugin and Android SDK (served from
`dl.google.com`/`maven.google.com`), which that environment's network
policy blocked, so it's built by
[`.github/workflows/android-build.yml`](../.github/workflows/android-build.yml)
on GitHub Actions instead — `:app:assembleDebug` succeeds there and
produces an installable debug APK on every push to `main` touching
`android/**`. That confirms the module compiles and packages correctly;
it has not yet been smoke-tested on a real device or emulator.

## Non-goals

Crop, layers, brush tools, healing, object removal, AI portrait editing —
see the spec's "KHÔNG BAO GỒM" section. Any feature request outside color/
film simulation, preview, and export is out of scope by design (this
applies equally to the Android app).
