package com.myphoto.core

import java.util.Random

/**
 * Renders an image through a Base Profile normalization pass, then a Film
 * Simulation pass whose intensity is controlled by [render]'s `strength`.
 * Mirrors `myphoto.preset_engine.engine.PresetEngine`.
 */
class PresetEngine(
    private val loader: PresetLoader,
    private val pipeline: ColorPipeline = ColorPipeline(),
) {

    /**
     * Returns [buffer] normalized by [baseProfileId] then styled by
     * [filmSimulationId] at the given [strength] (0.0-1.0).
     *
     * [grainAmount], if given, overrides the film simulation's grain
     * intensity (0.0-1.0) independently of [strength] — it backs a
     * separate Film Grain slider in the UI.
     */
    fun render(
        buffer: ImageBuffer,
        baseProfileId: String,
        filmSimulationId: String,
        strength: Float = 1f,
        grainAmount: Float? = null,
        random: Random = Random(),
    ): ImageBuffer {
        val baseProfile = loader.getBaseProfile(baseProfileId)
        val filmSimulation = loader.getFilmSimulation(filmSimulationId)

        val normalized = pipeline.process(buffer, baseProfile.adjustments, random)

        var adjustments = filmSimulation.adjustments.scaled(strength)
        if (grainAmount != null) {
            adjustments = adjustments.copy(grainAmount = grainAmount)
        }
        return pipeline.process(normalized, adjustments, random)
    }
}
