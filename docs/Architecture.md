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
   Astia, Classic Chrome, Classic Neg, Eterna, Acros, Nostalgic Neg, Reala
   Ace) on top of the normalized image. These are original simulations of
   a visual style, not decompiled/copied proprietary algorithms.

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
Filenames are built from a `rename_pattern` (`{stem}`, `{name}`, `{index}`)
via `export_engine.naming.build_output_path`.

## Batch processing

`myphoto.batch.BatchProcessor` runs a `BatchJob` (source images + preset +
strength + `ExportOptions`) on a `QThreadPool`, one `BatchItemRunnable`
(load -> `PresetEngine.render` -> `ExportEngine.export`) per image. It
emits `progress(completed, total)` and `item_finished(BatchItemResult)`
after each item, and `finished(list[BatchItemResult])` once every item is
done; `cancel()` makes not-yet-started items short-circuit to a
`"cancelled"` result. The UI thread never blocks on image processing.

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

## Non-goals

Crop, layers, brush tools, healing, object removal, AI portrait editing —
see the spec's "KHÔNG BAO GỒM" section. Any feature request outside color/
film simulation, preview, and export is out of scope by design.
