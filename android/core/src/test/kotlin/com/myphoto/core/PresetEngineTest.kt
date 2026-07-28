package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import java.io.File
import java.util.Random

/** Reads the real preset JSON files shipped at `presets/` in the repo root. */
private class RepoPresetSource : PresetSource {
    private val root: File = findRepoPresetsDir()

    override fun listBaseProfileDocuments() = readDir(File(root, "base_profiles"))
    override fun listFilmSimulationDocuments() = readDir(File(root, "film_simulations"))

    private fun readDir(dir: File): List<Pair<String, String>> =
        (dir.listFiles { file -> file.extension == "json" } ?: emptyArray())
            .sortedBy { it.name }
            .map { it.name to it.readText() }

    private fun findRepoPresetsDir(): File {
        var dir: File? = File("").absoluteFile
        while (dir != null) {
            val candidate = File(dir, "presets")
            if (candidate.isDirectory) return candidate
            dir = dir.parentFile
        }
        throw IllegalStateException("Could not locate the repo's presets/ directory from tests")
    }
}

private fun testBuffer(): ImageBuffer {
    val random = kotlin.random.Random(0)
    val data = FloatArray(16 * 16 * 3) { random.nextFloat() }
    return ImageBuffer(data, 16, 16, 3)
}

class PresetEngineTest {

    private val loader = PresetLoader(RepoPresetSource())

    @Test
    fun `render returns a valid buffer`() {
        val engine = PresetEngine(loader)
        val result = engine.render(testBuffer(), "fujifilm", "velvia", strength = 1f, random = Random(0))
        assertEquals(testBuffer().data.size, result.data.size)
        assertTrue(result.data.all { it in 0f..1f })
    }

    @Test
    fun `strength scales the effect`() {
        val engine = PresetEngine(loader)
        val buffer = testBuffer()
        val full = engine.render(buffer, "fujifilm", "velvia", strength = 1f, random = Random(0))
        val none = engine.render(buffer, "fujifilm", "velvia", strength = 0f, random = Random(0))
        assertNotEquals(full.data.toList(), none.data.toList())
    }

    @Test
    fun `grain amount overrides preset independently of strength`() {
        val engine = PresetEngine(loader)
        val buffer = testBuffer()
        val noGrain = engine.render(
            buffer, "fujifilm", "classic_neg", strength = 1f, grainAmount = 0f, random = Random(0)
        )
        val withGrain = engine.render(
            buffer, "fujifilm", "classic_neg", strength = 1f, grainAmount = 0.9f, random = Random(0)
        )
        val noGrainVariance = noGrain.data.map { it.toDouble() }.let { values -> values.variance() }
        val withGrainVariance = withGrain.data.map { it.toDouble() }.let { values -> values.variance() }
        assertTrue(withGrainVariance > noGrainVariance)
    }

    @Test
    fun `unknown base profile throws`() {
        val engine = PresetEngine(loader)
        assertThrows(PresetNotFoundException::class.java) {
            engine.render(testBuffer(), "does-not-exist", "velvia")
        }
    }

    @ParameterizedTest
    @ValueSource(
        strings = [
            "provia", "velvia", "astia", "classic_chrome", "classic_neg",
            "eterna", "acros", "nostalgic_neg", "reala_ace",
        ]
    )
    fun `every shipped film simulation renders`(filmSimulationId: String) {
        val engine = PresetEngine(loader)
        val result = engine.render(testBuffer(), "fujifilm", filmSimulationId, strength = 1f)
        assertEquals(testBuffer().data.size, result.data.size)
    }

    @Test
    fun `all shipped presets are discoverable`() {
        val baseIds = loader.listBaseProfiles().map { it.id }.toSet()
        val simIds = loader.listFilmSimulations().map { it.id }.toSet()
        assertEquals(
            setOf("sony", "canon", "nikon", "fujifilm", "om_system", "panasonic", "leica", "iphone"),
            baseIds,
        )
        assertEquals(
            setOf(
                "provia", "velvia", "astia", "classic_chrome", "classic_neg",
                "eterna", "acros", "nostalgic_neg", "reala_ace",
            ),
            simIds,
        )
    }
}

private fun List<Double>.variance(): Double {
    val mean = average()
    return sumOf { (it - mean) * (it - mean) } / size
}
