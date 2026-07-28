package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.Random
import kotlin.math.abs

private fun flatBuffer(width: Int, height: Int, r: Float, g: Float, b: Float): ImageBuffer {
    val data = FloatArray(width * height * 3)
    for (i in 0 until width * height) {
        data[i * 3] = r
        data[i * 3 + 1] = g
        data[i * 3 + 2] = b
    }
    return ImageBuffer(data, width, height, 3)
}

class ColorOperationsTest {

    @Test
    fun `white balance is identity at zero temp and tint`() {
        val buffer = flatBuffer(2, 2, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyWhiteBalance(buffer, temp = 0f, tint = 0f)
        assertEquals(0.5f, result.data[0], 1e-6f)
        assertEquals(0.5f, result.data[1], 1e-6f)
        assertEquals(0.5f, result.data[2], 1e-6f)
    }

    @Test
    fun `white balance warms red and cools blue`() {
        val buffer = flatBuffer(1, 1, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyWhiteBalance(buffer, temp = 1f, tint = 0f)
        assertTrue(result.data[0] > 0.5f)
        assertTrue(result.data[2] < 0.5f)
    }

    @Test
    fun `exposure doubles at one stop`() {
        val buffer = flatBuffer(1, 1, 0.25f, 0.25f, 0.25f)
        val result = ColorOperations.applyExposure(buffer, exposureEv = 1f)
        assertEquals(0.5f, result.data[0], 1e-6f)
    }

    @Test
    fun `curve identity is a no-op`() {
        assertEquals(0.3f, ColorOperations.applyCurve(0.3f, IDENTITY_CURVE), 1e-6f)
    }

    @Test
    fun `curve inverts`() {
        val curve: Curve = listOf(0f to 1f, 1f to 0f)
        assertEquals(0.7f, ColorOperations.applyCurve(0.3f, curve), 1e-6f)
    }

    @Test
    fun `hsl zero saturation desaturates`() {
        val buffer = flatBuffer(1, 1, 0.8f, 0.2f, 0.2f)
        val result = ColorOperations.applyHsl(buffer, hueShiftDegrees = 0f, saturationScale = 0f, lightnessScale = 1f)
        val spread = maxOf(result.data[0], result.data[1], result.data[2]) -
            minOf(result.data[0], result.data[1], result.data[2])
        assertTrue(abs(spread) < 1e-4f)
    }

    @Test
    fun `hsl no-op parameters return the same instance`() {
        val buffer = flatBuffer(1, 1, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyHsl(buffer, hueShiftDegrees = 0f, saturationScale = 1f, lightnessScale = 1f)
        assertTrue(result === buffer)
    }

    @Test
    fun `color balance zero adjustment is a no-op`() {
        val buffer = flatBuffer(1, 1, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyColorBalance(buffer, ColorBalanceAdjustment())
        assertTrue(result === buffer)
    }

    @Test
    fun `color balance shadow lift brightens dark pixels`() {
        val buffer = flatBuffer(1, 1, 0f, 0f, 0f)
        val adjustment = ColorBalanceAdjustment(shadows = Triple(0.1f, 0.1f, 0.1f))
        val result = ColorOperations.applyColorBalance(buffer, adjustment)
        assertTrue(result.data.all { it > 0f })
    }

    @Test
    fun `film grain zero amount is a no-op`() {
        val buffer = flatBuffer(4, 4, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyFilmGrain(buffer, amount = 0f)
        assertTrue(result === buffer)
    }

    @Test
    fun `film grain adds variation`() {
        val buffer = flatBuffer(32, 32, 0.5f, 0.5f, 0.5f)
        val result = ColorOperations.applyFilmGrain(buffer, amount = 0.5f, random = Random(42))
        assertFalse(result.data.contentEquals(buffer.data))
    }

    @Test
    fun `clamp restricts values to the unit range`() {
        val data = floatArrayOf(-0.5f, 1.5f, 0.5f)
        val buffer = ImageBuffer(data, 1, 1, 3)
        val result = ColorOperations.clampToUnitRange(buffer)
        assertEquals(0f, result.data[0], 1e-6f)
        assertEquals(1f, result.data[1], 1e-6f)
        assertEquals(0.5f, result.data[2], 1e-6f)
    }

    @Test
    fun `rgba alpha channel passes through untouched`() {
        val data = floatArrayOf(0.5f, 0.5f, 0.5f, 0.7f)
        val buffer = ImageBuffer(data, 1, 1, 4)
        val result = ColorOperations.applyExposure(buffer, exposureEv = 1f)
        assertEquals(0.7f, result.data[3], 1e-6f)
        assertNotEquals(0.5f, result.data[0])
    }
}
