package com.myphoto.core

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.Random
import kotlin.random.Random as KRandom

private fun randomBuffer(width: Int, height: Int, channels: Int = 3, seed: Int = 1): ImageBuffer {
    val random = KRandom(seed)
    val data = FloatArray(width * height * channels) { random.nextFloat() }
    return ImageBuffer(data, width, height, channels)
}

class ColorPipelineTest {

    @Test
    fun `identity adjustments leave the image nearly unchanged`() {
        val buffer = randomBuffer(6, 6)
        val result = ColorPipeline().process(buffer, ColorAdjustments(), Random(0))
        for (i in buffer.data.indices) {
            assertEquals(buffer.data[i], result.data[i], 1e-5f)
        }
    }

    @Test
    fun `output is clamped to the unit range`() {
        val buffer = randomBuffer(6, 6)
        val result = ColorPipeline().process(buffer, ColorAdjustments(exposureEv = 5f))
        assertTrue(result.data.all { it in 0f..1f })
    }

    @Test
    fun `rgba alpha passes through untouched`() {
        val buffer = randomBuffer(4, 4, channels = 4)
        val result = ColorPipeline().process(buffer, ColorAdjustments(exposureEv = 2f))
        for (i in 0 until buffer.width * buffer.height) {
            assertEquals(buffer.data[i * 4 + 3], result.data[i * 4 + 3], 1e-6f)
        }
    }
}
