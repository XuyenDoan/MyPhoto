"""Discovers and loads preset JSON files from disk (never hardcoded)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from myphoto.core.errors import PresetNotFoundError, PresetValidationError
from myphoto.preset_engine.models import NO_FILM_SIMULATION_ID, Preset, PresetKind
from myphoto.preset_engine.serialization import preset_from_json


class PresetLoader:
    """Loads Base Profile and Film Simulation presets from their directories."""

    def __init__(self, base_profiles_dir: Path, film_simulations_dir: Path) -> None:
        self._base_profiles_dir = base_profiles_dir
        self._film_simulations_dir = film_simulations_dir
        self._base_profiles: dict[str, Preset] = {}
        self._film_simulations: dict[str, Preset] = {}
        self.reload()

    def reload(self) -> None:
        """Re-scan both preset directories, replacing any previously loaded presets."""
        self._base_profiles = self._load_dir(self._base_profiles_dir, PresetKind.BASE_PROFILE)
        self._film_simulations = self._load_dir(
            self._film_simulations_dir, PresetKind.FILM_SIMULATION
        )

    def list_base_profiles(self) -> list[Preset]:
        return sorted(self._base_profiles.values(), key=lambda preset: preset.name)

    def list_film_simulations(self) -> list[Preset]:
        return sorted(
            self._film_simulations.values(),
            key=lambda preset: (preset.id != NO_FILM_SIMULATION_ID, preset.name),
        )


    def get_base_profile(self, preset_id: str) -> Preset:
        return self._get(self._base_profiles, preset_id)

    def get_film_simulation(self, preset_id: str) -> Preset:
        return self._get(self._film_simulations, preset_id)

    @staticmethod
    def _get(presets: dict[str, Preset], preset_id: str) -> Preset:
        try:
            return presets[preset_id]
        except KeyError:
            raise PresetNotFoundError(preset_id) from None

    def _load_dir(self, directory: Path, expected_kind: PresetKind) -> dict[str, Preset]:
        presets: dict[str, Preset] = {}
        if not directory.is_dir():
            return presets

        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                preset = preset_from_json(document)
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
                raise PresetValidationError(path, str(exc)) from exc

            if preset.kind is not expected_kind:
                raise PresetValidationError(
                    path, f"expected kind {expected_kind.value!r}, got {preset.kind.value!r}"
                )

            lut_name = document.get("lut")
            if lut_name is not None:
                preset = replace(preset, lut_path=path.parent / lut_name)

            presets[preset.id] = preset
        return presets
