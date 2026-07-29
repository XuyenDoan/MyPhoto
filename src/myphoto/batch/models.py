"""Batch job configuration and per-item results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from myphoto.export_engine.models import ExportOptions


@dataclass(frozen=True, slots=True)
class BatchJob:
    """One batch export request: a set of source images and shared render/export settings."""

    source_paths: tuple[Path, ...]
    base_profile_id: str
    film_simulation_id: str
    strength: float
    export_options: ExportOptions
    grain_amount: float | None = None
    local_balance_enabled: bool = False
    auto_level_enabled: bool = False
    fix_chromatic_aberration_enabled: bool = False
    auto_sharpen_enabled: bool = False


@dataclass(frozen=True, slots=True)
class BatchItemResult:
    """The outcome of processing a single image within a :class:`BatchJob`."""

    source_path: Path
    output_path: Path | None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None
