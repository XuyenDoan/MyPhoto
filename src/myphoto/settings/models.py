"""Persisted application settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Theme = Literal["system", "light", "dark"]


@dataclass(frozen=True, slots=True)
class AppSettings:
    """The subset of app state that survives a restart."""

    last_base_profile_id: str | None = None
    last_film_simulation_id: str | None = None
    last_folder: Path | None = None
    export_folder: Path | None = None
    theme: Theme = "system"
