# Presets

This directory holds the JSON preset files loaded by the Preset Engine at
runtime. Presets are never hardcoded in source — the engine discovers and
loads every `*.json` file here (and, later, from a user presets directory).

Each preset is one of two layers, applied in order:

1. **Base Profile** (`base_profiles/`) — normalizes a camera manufacturer's
   color response (Sony, Canon, Nikon, Fujifilm, OM System, Panasonic,
   Leica, iPhone) before any creative look is applied.
2. **Film Simulation** (`film_simulations/`) — applies a Fujifilm-inspired
   color style (Provia, Velvia, Astia, Classic Chrome, Classic Neg, Eterna,
   Acros, Nostalgic Neg, Reala Ace) on top of the normalized image.

These are style simulations, not reverse-engineered proprietary Fujifilm
algorithms.

## JSON schema

See the docstring in
[`src/myphoto/preset_engine/serialization.py`](../src/myphoto/preset_engine/serialization.py)
for the authoritative schema. Every field is optional and defaults to a
neutral (no-op) value, so a minimal preset is just:

```json
{ "id": "example", "name": "Example", "kind": "film_simulation" }
```

An optional `"lut"` field names a NumPy `.npy` file (shape `(N, N, N, 3)`,
values in `[0, 1]`), resolved relative to the preset's own file, applied as
a 3D LUT after the parametric adjustments.

The `PresetLoader` (`myphoto.preset_engine.PresetLoader`) discovers every
`*.json` file in `base_profiles/` and `film_simulations/` at startup —
nothing is hardcoded, and adding a new preset is just adding a new file.
