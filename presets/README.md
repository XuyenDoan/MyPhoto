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

The concrete JSON schema and the first set of preset files will be added
alongside the Preset Engine implementation.
