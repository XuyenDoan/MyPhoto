"""Preset domain model: one layer (Base Profile or Film Simulation)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from myphoto.color_engine.adjustments import ColorAdjustments


class PresetKind(str, Enum):
    """Which layer of the Two-Layer Preset System a preset belongs to."""

    BASE_PROFILE = "base_profile"
    FILM_SIMULATION = "film_simulation"


@dataclass(frozen=True, slots=True)
class Preset:
    """One loaded preset: identity plus the color adjustments it applies."""

    id: str
    name: str
    kind: PresetKind
    adjustments: ColorAdjustments
    lut_path: Path | None = None
    """Optional absolute path to a ``.npy`` 3D LUT array (shape ``(N, N, N, 3)``)."""
