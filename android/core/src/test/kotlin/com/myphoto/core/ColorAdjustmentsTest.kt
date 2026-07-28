package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class ColorAdjustmentsTest {

    private fun sample() = ColorAdjustments(
        whiteBalanceTemp = 0.4f,
        whiteBalanceTint = -0.2f,
        exposureEv = 1f,
        toneCurve = listOf(0f to 0.1f, 1f to 0.9f),
        hueShiftDegrees = 10f,
        saturationScale = 1.5f,
        lightnessScale = 1.2f,
        colorBalance = ColorBalanceAdjustment(shadows = Triple(0.1f, 0f, -0.1f)),
        grainAmount = 0.6f,
    )

    @Test
    fun `full strength is unchanged`() {
        val adjustments = sample()
        assertEquals(adjustments, adjustments.scaled(1f))
    }

    @Test
    fun `zero strength is identity`() {
        val result = sample().scaled(0f)
        assertEquals(0f, result.whiteBalanceTemp)
        assertEquals(0f, result.whiteBalanceTint)
        assertEquals(0f, result.exposureEv)
        assertEquals(0f, result.hueShiftDegrees)
        assertEquals(1f, result.saturationScale)
        assertEquals(1f, result.lightnessScale)
        assertEquals(Triple(0f, 0f, 0f), result.colorBalance.shadows)
        assertEquals(0f, result.grainAmount)
        assertEquals(0f to 0f, result.toneCurve[0])
        assertEquals(1f to 1f, result.toneCurve[1])
    }

    @Test
    fun `half strength is between`() {
        val result = sample().scaled(0.5f)
        assertTrue(result.exposureEv in 0f..1f)
        assertTrue(result.saturationScale in 1f..1.5f)
    }

    @Test
    fun `rejects out of range strength`() {
        assertThrows(IllegalArgumentException::class.java) { sample().scaled(1.5f) }
    }
}
