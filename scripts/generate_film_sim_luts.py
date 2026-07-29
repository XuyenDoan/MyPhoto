#!/usr/bin/env python3
"""Generates the 3D LUT .npy files for Film Simulation presets and patches
the preset JSON files to reference them.

Run manually whenever a recipe below changes::

    python scripts/generate_film_sim_luts.py

See `myphoto.preset_engine.lut_builder` for what these recipes do and why
they're deliberately modest, hue-*selective* refinements rather than a
from-scratch re-grade — the JSON `adjustments` already committed for each
preset still own the overall saturation/contrast level.

Provia, Acros, and Sepia are intentionally left without a LUT: Provia is
the neutral "standard" baseline, and Acros/Sepia are fully desaturated by
their JSON `hsl.saturation_scale` *before* the LUT stage runs, so there's
no hue information left for hue-selective bands to act on.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from myphoto.preset_engine.lut_builder import HueBand, LutRecipe, build_lut

REPO_ROOT = Path(__file__).resolve().parents[1]
FILM_SIM_DIR = REPO_ROOT / "presets" / "film_simulations"
LUT_DIR = FILM_SIM_DIR / "luts"

# Hue centers (OpenCV 0-360 HLS scale) reused across recipes below.
_SKIN = 25.0
_GREEN = 110.0
_BLUE = 220.0
_WARM = 35.0

_RECIPES: dict[str, LutRecipe] = {
    "velvia": LutRecipe(
        hue_bands=(
            HueBand(center=_GREEN, width=60, saturation_mult=1.15, lightness_mult=0.98),
            HueBand(center=_BLUE, width=50, saturation_mult=1.12),
            HueBand(center=_SKIN, width=25, saturation_mult=1.0),  # protect skin from the boost
        ),
        highlight_tint=(0.008, 0.004, -0.006),
    ),
    "astia": LutRecipe(
        hue_bands=(
            HueBand(center=_SKIN, width=25, hue_shift=-1.5, saturation_mult=0.95, lightness_mult=1.02),
            HueBand(center=_BLUE, width=50, saturation_mult=0.95),
        ),
    ),
    "pro_neg_hi": LutRecipe(
        hue_bands=(HueBand(center=_SKIN, width=25, saturation_mult=0.97, lightness_mult=0.99),),
    ),
    "pro_neg_std": LutRecipe(
        hue_bands=(HueBand(center=_SKIN, width=25, saturation_mult=0.93, lightness_mult=1.02),),
    ),
    "reala_ace": LutRecipe(
        hue_bands=(HueBand(center=_SKIN, width=25, saturation_mult=1.0),),
        overall_saturation=1.05,
    ),
    "classic_chrome": LutRecipe(
        hue_bands=(
            HueBand(center=_GREEN, width=60, hue_shift=-6.0, saturation_mult=0.85, lightness_mult=0.97),
            HueBand(center=50, width=30, saturation_mult=0.9),
        ),
        shadow_tint=(0.0, 0.006, 0.01),
        highlight_tint=(0.008, 0.004, -0.006),
    ),
    "classic_neg": LutRecipe(
        hue_bands=(
            HueBand(center=_GREEN, width=60, hue_shift=-5.0, saturation_mult=0.88),
            HueBand(center=_SKIN, width=25, hue_shift=3.0, saturation_mult=0.95),
        ),
        shadow_tint=(0.008, 0.0, 0.012),
        highlight_tint=(0.01, 0.005, -0.007),
    ),
    "eterna": LutRecipe(
        hue_bands=(
            HueBand(center=_GREEN, width=90, saturation_mult=0.85),
            HueBand(center=_BLUE, width=90, saturation_mult=0.88),
        ),
        overall_saturation=0.95,
        shadow_tint=(-0.004, 0.004, 0.01),
        highlight_tint=(0.01, 0.005, -0.004),
    ),
    "eterna_bleach_bypass": LutRecipe(
        hue_bands=(HueBand(center=0, width=180, saturation_mult=0.75),),
        shadow_tint=(-0.008, 0.004, 0.015),
        highlight_tint=(0.014, 0.008, -0.008),
    ),
    "acros": LutRecipe(
        shadow_tint=(-0.004, 0.0, 0.006),
        highlight_tint=(0.003, 0.0015, -0.003),
    ),
    "nostalgic_neg": LutRecipe(
        hue_bands=(
            HueBand(center=_WARM, width=30, saturation_mult=1.1, lightness_mult=1.02),
            HueBand(center=_BLUE, width=60, saturation_mult=0.8, lightness_mult=0.97),
        ),
        shadow_tint=(0.01, 0.004, -0.006),
        highlight_tint=(0.008, 0.005, -0.003),
    ),
}


def main() -> None:
    LUT_DIR.mkdir(parents=True, exist_ok=True)
    for preset_id, recipe in _RECIPES.items():
        json_path = FILM_SIM_DIR / f"{preset_id}.json"
        document = json.loads(json_path.read_text(encoding="utf-8"))

        lut = build_lut(recipe)
        lut_filename = f"luts/{preset_id}.npy"
        np.save(LUT_DIR / f"{preset_id}.npy", lut)

        document["lut"] = lut_filename
        json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {lut_filename} ({lut.nbytes / 1024:.0f} KiB) and updated {json_path.name}")


if __name__ == "__main__":
    main()
