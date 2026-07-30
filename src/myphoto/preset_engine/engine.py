"""Applies the Two-Layer Preset System: Base Profile, then Film Simulation."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from myphoto.color_engine.pipeline import ColorPipeline
from myphoto.core.image import ImageBuffer
from myphoto.preset_engine.loader import PresetLoader


class PresetEngine:
    """Renders an image through a Base Profile normalization pass, then a
    Film Simulation pass whose intensity is controlled by ``strength``.
    """

    def __init__(self, loader: PresetLoader, pipeline: ColorPipeline | None = None) -> None:
        self._loader = loader
        self._pipeline = pipeline if pipeline is not None else ColorPipeline()

    @property
    def loader(self) -> PresetLoader:
        return self._loader

    def render(
        self,
        buffer: ImageBuffer,
        base_profile_id: str,
        film_simulation_id: str,
        strength: float = 1.0,
        grain_amount: float | None = None,
        rng: np.random.Generator | None = None,
    ) -> ImageBuffer:
        """Return ``buffer`` normalized by ``base_profile_id`` then styled by
        ``film_simulation_id`` at the given ``strength`` (0.0-1.0).

        ``grain_amount``, if given, overrides the film simulation's grain
        intensity (0.0-1.0) independently of ``strength`` — it backs the
        UI's separate Film Grain slider.
        """
        base_profile = self._loader.get_base_profile(base_profile_id)
        film_simulation = self._loader.get_film_simulation(film_simulation_id)

        normalized = self._pipeline.process(buffer, base_profile.adjustments, rng=rng)

        adjustments = film_simulation.adjustments.scaled(strength)
        if grain_amount is not None:
            adjustments = replace(adjustments, grain_amount=grain_amount)

        lut = np.load(film_simulation.lut_path) if film_simulation.lut_path is not None else None
        return self._pipeline.process(
            normalized, adjustments, film_simulation_lut=lut, rng=rng
        )
