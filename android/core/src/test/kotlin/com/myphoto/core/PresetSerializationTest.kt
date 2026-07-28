package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class PresetSerializationTest {

    @Test
    fun `full document parses every field`() {
        val text = """
            {
              "id": "provia",
              "name": "Provia (Standard)",
              "kind": "film_simulation",
              "adjustments": {
                "white_balance": {"temp": 0.2, "tint": -0.1},
                "exposure_ev": 0.5,
                "tone_curve": [[0.0, 0.05], [1.0, 0.95]],
                "hsl": {"hue_shift_degrees": 5.0, "saturation_scale": 1.2, "lightness_scale": 0.9},
                "color_balance": {
                  "shadows": [0.01, 0.0, -0.01],
                  "highlights": [0.02, 0.0, 0.0]
                },
                "grain": {"amount": 0.3, "size": 1.5}
              }
            }
        """.trimIndent()

        val preset = presetFrom(parsePresetDocument(text))

        assertEquals("provia", preset.id)
        assertEquals(PresetKind.FILM_SIMULATION, preset.kind)
        assertEquals(0.2f, preset.adjustments.whiteBalanceTemp)
        assertEquals(-0.1f, preset.adjustments.whiteBalanceTint)
        assertEquals(0.5f, preset.adjustments.exposureEv)
        assertEquals(listOf(0.0f to 0.05f, 1.0f to 0.95f), preset.adjustments.toneCurve)
        assertEquals(5f, preset.adjustments.hueShiftDegrees)
        assertEquals(Triple(0.01f, 0f, -0.01f), preset.adjustments.colorBalance.shadows)
        assertEquals(0.3f, preset.adjustments.grainAmount)
    }

    @Test
    fun `missing fields default to identity`() {
        val text = """{"id": "x", "name": "X", "kind": "base_profile"}"""
        val preset = presetFrom(parsePresetDocument(text))

        assertEquals(0f, preset.adjustments.whiteBalanceTemp)
        assertEquals(1f, preset.adjustments.saturationScale)
        assertEquals(IDENTITY_CURVE, preset.adjustments.toneCurve)
    }

    @Test
    fun `curve requires at least two points`() {
        assertThrows(IllegalArgumentException::class.java) {
            curveFrom(listOf(listOf(0.5f, 0.5f)))
        }
    }

    @Test
    fun `color balance zone requires exactly three components`() {
        assertThrows(IllegalArgumentException::class.java) {
            rgbFrom(listOf(0.1f, 0.1f))
        }
    }

    @Test
    fun `unknown preset kind throws`() {
        assertThrows(IllegalArgumentException::class.java) { presetKindFrom("not_a_kind") }
    }
}
