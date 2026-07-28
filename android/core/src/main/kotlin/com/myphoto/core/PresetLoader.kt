package com.myphoto.core

/**
 * Where [PresetLoader] reads preset JSON text from. On Android this is
 * backed by `AssetManager`; in tests, by an in-memory map — the `core`
 * module itself has no Android dependency.
 */
interface PresetSource {
    /** `(sourceName, jsonText)` pairs for every Base Profile preset file. */
    fun listBaseProfileDocuments(): List<Pair<String, String>>

    /** `(sourceName, jsonText)` pairs for every Film Simulation preset file. */
    fun listFilmSimulationDocuments(): List<Pair<String, String>>
}

/** Discovers and loads Base Profile and Film Simulation presets via a [PresetSource]. */
class PresetLoader(source: PresetSource) {

    private val baseProfiles: Map<String, Preset> =
        load(source.listBaseProfileDocuments(), PresetKind.BASE_PROFILE)
    private val filmSimulations: Map<String, Preset> =
        load(source.listFilmSimulationDocuments(), PresetKind.FILM_SIMULATION)

    fun listBaseProfiles(): List<Preset> = baseProfiles.values.sortedBy { it.name }

    fun listFilmSimulations(): List<Preset> = filmSimulations.values.sortedBy { it.name }

    fun getBaseProfile(id: String): Preset = baseProfiles[id] ?: throw PresetNotFoundException(id)

    fun getFilmSimulation(id: String): Preset = filmSimulations[id] ?: throw PresetNotFoundException(id)

    private fun load(documents: List<Pair<String, String>>, expectedKind: PresetKind): Map<String, Preset> {
        val result = LinkedHashMap<String, Preset>()
        for ((sourceName, text) in documents) {
            val preset = try {
                presetFrom(parsePresetDocument(text))
            } catch (exc: Exception) {
                throw PresetValidationException(sourceName, exc.message ?: exc.toString())
            }
            if (preset.kind != expectedKind) {
                throw PresetValidationException(
                    sourceName,
                    "expected kind ${expectedKind.name.lowercase()}, got ${preset.kind.name.lowercase()}",
                )
            }
            result[preset.id] = preset
        }
        return result
    }
}
