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

## Batch processing

`myphoto.batch` runs exports on a `QThreadPool` with one worker per image,
reporting progress back to the GUI thread via Qt signals, and supporting
cancellation. The UI thread never blocks on image processing.

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
