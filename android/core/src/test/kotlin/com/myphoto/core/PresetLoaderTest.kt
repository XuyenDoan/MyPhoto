package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

private class FakePresetSource(
    private val baseProfiles: List<Pair<String, String>> = emptyList(),
    private val filmSimulations: List<Pair<String, String>> = emptyList(),
) : PresetSource {
    override fun listBaseProfileDocuments() = baseProfiles
    override fun listFilmSimulationDocuments() = filmSimulations
}

class PresetLoaderTest {

    @Test
    fun `loads base profiles and film simulations`() {
        val source = FakePresetSource(
            baseProfiles = listOf("sony.json" to """{"id":"sony","name":"Sony","kind":"base_profile"}"""),
            filmSimulations = listOf(
                "provia.json" to """{"id":"provia","name":"Provia","kind":"film_simulation"}"""
            ),
        )
        val loader = PresetLoader(source)

        assertEquals(listOf("sony"), loader.listBaseProfiles().map { it.id })
        assertEquals(listOf("provia"), loader.listFilmSimulations().map { it.id })
        assertEquals("Sony", loader.getBaseProfile("sony").name)
    }

    @Test
    fun `empty source yields empty lists`() {
        val loader = PresetLoader(FakePresetSource())
        assertTrue(loader.listBaseProfiles().isEmpty())
        assertTrue(loader.listFilmSimulations().isEmpty())
    }

    @Test
    fun `unknown preset id throws`() {
        val loader = PresetLoader(FakePresetSource())
        assertThrows(PresetNotFoundException::class.java) { loader.getBaseProfile("nope") }
    }

    @Test
    fun `malformed json throws validation exception`() {
        val source = FakePresetSource(baseProfiles = listOf("broken.json" to "{not valid json"))
        assertThrows(PresetValidationException::class.java) { PresetLoader(source) }
    }

    @Test
    fun `wrong kind for directory throws validation exception`() {
        val source = FakePresetSource(
            baseProfiles = listOf("oops.json" to """{"id":"oops","name":"Oops","kind":"film_simulation"}""")
        )
        assertThrows(PresetValidationException::class.java) { PresetLoader(source) }
    }
}
