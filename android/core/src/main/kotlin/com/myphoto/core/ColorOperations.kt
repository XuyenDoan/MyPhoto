package com.myphoto.core

import java.util.Random

/**
 * Pure, individually testable Color Pipeline operations. Every function
 * takes and returns an [ImageBuffer] and never mutates its input. Mirrors
 * `myphoto.color_engine.operations` on the desktop side, minus 3D LUT
 * support (no shipped preset currently uses one; see docs/Architecture.md).
 */
object ColorOperations {

    fun applyWhiteBalance(buffer: ImageBuffer, temp: Float, tint: Float): ImageBuffer {
        if (temp == 0f && tint == 0f) return buffer
        val rGain = 1f + 0.35f * temp + 0.15f * tint
        val gGain = 1f - 0.25f * tint
        val bGain = 1f - 0.35f * temp + 0.15f * tint
        return mapRgb(buffer) { r, g, b -> Triple(r * rGain, g * gGain, b * bGain) }
    }

    fun applyExposure(buffer: ImageBuffer, exposureEv: Float): ImageBuffer {
        if (exposureEv == 0f) return buffer
        val gain = Math.pow(2.0, exposureEv.toDouble()).toFloat()
        return mapRgb(buffer) { r, g, b -> Triple(r * gain, g * gain, b * gain) }
    }

    /** Piecewise-linear interpolation through [curve]'s control points. */
    fun applyCurve(value: Float, curve: Curve): Float {
        val sorted = curve.sortedBy { it.first }
        val first = sorted.first()
        val last = sorted.last()
        if (value <= first.first) return first.second
        if (value >= last.first) return last.second
        for (i in 0 until sorted.size - 1) {
            val (x0, y0) = sorted[i]
            val (x1, y1) = sorted[i + 1]
            if (value in x0..x1) {
                if (x1 == x0) return y0
                val t = (value - x0) / (x1 - x0)
                return y0 + (y1 - y0) * t
            }
        }
        return last.second
    }

    fun applyToneCurve(buffer: ImageBuffer, curve: Curve): ImageBuffer {
        if (curve == IDENTITY_CURVE) return buffer
        return mapRgb(buffer) { r, g, b ->
            Triple(applyCurve(r, curve), applyCurve(g, curve), applyCurve(b, curve))
        }
    }

    fun applyRgbCurves(buffer: ImageBuffer, red: Curve, green: Curve, blue: Curve): ImageBuffer {
        if (red == IDENTITY_CURVE && green == IDENTITY_CURVE && blue == IDENTITY_CURVE) return buffer
        return mapRgb(buffer) { r, g, b -> Triple(applyCurve(r, red), applyCurve(g, green), applyCurve(b, blue)) }
    }

    fun applyHsl(
        buffer: ImageBuffer,
        hueShiftDegrees: Float,
        saturationScale: Float,
        lightnessScale: Float,
    ): ImageBuffer {
        if (hueShiftDegrees == 0f && saturationScale == 1f && lightnessScale == 1f) return buffer
        return mapRgb(buffer) { r, g, b ->
            val (h, l, s) = rgbToHsl(r.coerceIn(0f, 1f), g.coerceIn(0f, 1f), b.coerceIn(0f, 1f))
            val newHue = ((h + hueShiftDegrees) % 360f + 360f) % 360f
            val newLightness = (l * lightnessScale).coerceIn(0f, 1f)
            val newSaturation = (s * saturationScale).coerceIn(0f, 1f)
            hslToRgb(newHue, newLightness, newSaturation)
        }
    }

    fun applyColorBalance(buffer: ImageBuffer, adjustment: ColorBalanceAdjustment): ImageBuffer {
        if (adjustment == ColorBalanceAdjustment()) return buffer
        val (sr, sg, sb) = adjustment.shadows
        val (mr, mg, mb) = adjustment.midtones
        val (hr, hg, hb) = adjustment.highlights
        return mapRgb(buffer) { r, g, b ->
            val luminance = r * 0.2126f + g * 0.7152f + b * 0.0722f
            val shadowWeight = (1f - luminance * 2f).coerceIn(0f, 1f)
            val highlightWeight = (luminance * 2f - 1f).coerceIn(0f, 1f)
            val midtoneWeight = (1f - shadowWeight - highlightWeight).coerceIn(0f, 1f)
            Triple(
                r + shadowWeight * sr + midtoneWeight * mr + highlightWeight * hr,
                g + shadowWeight * sg + midtoneWeight * mg + highlightWeight * hg,
                b + shadowWeight * sb + midtoneWeight * mb + highlightWeight * hb,
            )
        }
    }

    /** Adds luminance-only Gaussian grain. */
    fun applyFilmGrain(buffer: ImageBuffer, amount: Float, random: Random = Random()): ImageBuffer {
        if (amount <= 0f) return buffer
        val out = buffer.data.copyOf()
        val pixelCount = buffer.width * buffer.height
        val channels = buffer.channels
        for (i in 0 until pixelCount) {
            val noise = random.nextGaussian().toFloat() * amount * 0.08f
            val base = i * channels
            out[base] += noise
            out[base + 1] += noise
            out[base + 2] += noise
        }
        return buffer.copyWithData(out)
    }

    fun clampToUnitRange(buffer: ImageBuffer): ImageBuffer {
        val out = FloatArray(buffer.data.size) { i -> buffer.data[i].coerceIn(0f, 1f) }
        return buffer.copyWithData(out)
    }

    private inline fun mapRgb(
        buffer: ImageBuffer,
        transform: (Float, Float, Float) -> Triple<Float, Float, Float>,
    ): ImageBuffer {
        val channels = buffer.channels
        val out = FloatArray(buffer.data.size)
        val pixelCount = buffer.width * buffer.height
        for (i in 0 until pixelCount) {
            val base = i * channels
            val (r, g, b) = transform(buffer.data[base], buffer.data[base + 1], buffer.data[base + 2])
            out[base] = r
            out[base + 1] = g
            out[base + 2] = b
            if (channels == 4) out[base + 3] = buffer.data[base + 3]
        }
        return buffer.copyWithData(out)
    }

    private fun rgbToHsl(r: Float, g: Float, b: Float): Triple<Float, Float, Float> {
        val maxChannel = maxOf(r, g, b)
        val minChannel = minOf(r, g, b)
        val lightness = (maxChannel + minChannel) / 2f
        if (maxChannel == minChannel) return Triple(0f, lightness, 0f)

        val delta = maxChannel - minChannel
        val saturation =
            if (lightness > 0.5f) delta / (2f - maxChannel - minChannel) else delta / (maxChannel + minChannel)
        val hue = when (maxChannel) {
            r -> ((g - b) / delta + (if (g < b) 6f else 0f))
            g -> (b - r) / delta + 2f
            else -> (r - g) / delta + 4f
        } * 60f
        return Triple(hue, lightness, saturation)
    }

    private fun hslToRgb(h: Float, l: Float, s: Float): Triple<Float, Float, Float> {
        if (s == 0f) return Triple(l, l, l)

        fun hueToRgb(p: Float, q: Float, tIn: Float): Float {
            var t = tIn
            if (t < 0f) t += 1f
            if (t > 1f) t -= 1f
            return when {
                t < 1f / 6f -> p + (q - p) * 6f * t
                t < 1f / 2f -> q
                t < 2f / 3f -> p + (q - p) * (2f / 3f - t) * 6f
                else -> p
            }
        }

        val q = if (l < 0.5f) l * (1f + s) else l + s - l * s
        val p = 2f * l - q
        val hueNorm = h / 360f
        return Triple(
            hueToRgb(p, q, hueNorm + 1f / 3f),
            hueToRgb(p, q, hueNorm),
            hueToRgb(p, q, hueNorm - 1f / 3f),
        )
    }
}
