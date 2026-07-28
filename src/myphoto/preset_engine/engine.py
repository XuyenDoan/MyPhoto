"""Applies the Two-Layer Preset System: Base Profile, then Film Simulation."""

from __future__ import annotations

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

    def render(
        self,
        buffer: ImageBuffer,
        base_profile_id: str,
        film_simulation_id: str,
        strength: float = 1.0,
        rng: np.random.Generator | None = None,
    ) -> ImageBuffer:
        """Return ``buffer`` normalized by ``base_profile_id`` then styled by
        ``film_simulation_id`` at the given ``strength`` (0.0-1.0).
        """
        base_profile = self._loader.get_base_profile(base_profile_id)
        film_simulation = self._loader.get_film_simulation(film_simulation_id)

        normalized = self._pipeline.process(buffer, base_profile.adjustments, rng=rng)

        lut = np.load(film_simulation.lut_path) if film_simulation.lut_path is not None else None
        return self._pipeline.process(
            normalized,
            film_simulation.adjustments.scaled(strength),
            film_simulation_lut=lut,
            rng=rng,
        )
