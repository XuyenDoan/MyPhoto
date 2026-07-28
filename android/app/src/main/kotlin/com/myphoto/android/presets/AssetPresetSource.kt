package com.myphoto.android.presets

import android.content.res.AssetManager
import com.myphoto.core.PresetSource

/**
 * Reads preset JSON files from `assets/presets/base_profiles/` and
 * `assets/presets/film_simulations/`, which is copied from the repo-root
 * `presets/` directory at build time (see the `copyPresets` Gradle task
 * in `app/build.gradle.kts`) — that directory is the single source of
 * truth, shared with the desktop app.
 */
class AssetPresetSource(private val assets: AssetManager) : PresetSource {

    override fun listBaseProfileDocuments(): List<Pair<String, String>> = readDir("presets/base_profiles")

    override fun listFilmSimulationDocuments(): List<Pair<String, String>> = readDir("presets/film_simulations")

    private fun readDir(path: String): List<Pair<String, String>> {
        val names = assets.list(path) ?: emptyArray()
        return names.filter { it.endsWith(".json") }.sorted().map { name ->
            val text = assets.open("$path/$name").bufferedReader().use { it.readText() }
            name to text
        }
    }
}
