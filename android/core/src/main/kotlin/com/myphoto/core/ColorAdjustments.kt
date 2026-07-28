package com.myphoto.core

/** A tone/RGB curve as ordered (input, output) control points in `[0, 1]`. */
typealias Curve = List<Pair<Float, Float>>

val IDENTITY_CURVE: Curve = listOf(0f to 0f, 1f to 1f)

/** Additive RGB offsets applied per luminosity zone (lift/gamma/gain style). */
data class ColorBalanceAdjustment(
    val shadows: Triple<Float, Float, Float> = Triple(0f, 0f, 0f),
    val midtones: Triple<Float, Float, Float> = Triple(0f, 0f, 0f),
    val highlights: Triple<Float, Float, Float> = Triple(0f, 0f, 0f),
)

/**
 * The full set of Color Pipeline parameters for a single render pass.
 * Mirrors `myphoto.color_engine.adjustments.ColorAdjustments` on desktop.
 */
data class ColorAdjustments(
    /** -1.0 (cooler/blue) .. +1.0 (warmer/amber). */
    val whiteBalanceTemp: Float = 0f,
    /** -1.0 (green) .. +1.0 (magenta). */
    val whiteBalanceTint: Float = 0f,
    val exposureEv: Float = 0f,
    val toneCurve: Curve = IDENTITY_CURVE,
    val redCurve: Curve = IDENTITY_CURVE,
    val greenCurve: Curve = IDENTITY_CURVE,
    val blueCurve: Curve = IDENTITY_CURVE,
    val hueShiftDegrees: Float = 0f,
    val saturationScale: Float = 1f,
    val lightnessScale: Float = 1f,
    val colorBalance: ColorBalanceAdjustment = ColorBalanceAdjustment(),
    /** 0.0 (no grain) .. 1.0 (heavy grain). */
    val grainAmount: Float = 0f,
    /** Relative grain particle size; 1.0 is the baseline size. */
    val grainSize: Float = 1f,
) {
    /**
     * Returns a copy linearly blended toward identity by [strength] (0..1).
     * `strength = 1.0` returns an equal copy; `strength = 0.0` returns an
     * adjustment set with no visible effect. Backs the UI's Strength slider.
     */
    fun scaled(strength: Float): ColorAdjustments {
        require(strength in 0f..1f) { "strength must be in [0, 1], got $strength" }

        fun lerp(value: Float, identity: Float) = identity + (value - identity) * strength
        fun lerpCurve(curve: Curve): Curve =
            if (strength >= 1f) curve else curve.map { (x, y) -> x to lerp(y, x) }
        fun lerpRgb(rgb: Triple<Float, Float, Float>) =
            Triple(lerp(rgb.first, 0f), lerp(rgb.second, 0f), lerp(rgb.third, 0f))

        return ColorAdjustments(
            whiteBalanceTemp = lerp(whiteBalanceTemp, 0f),
            whiteBalanceTint = lerp(whiteBalanceTint, 0f),
            exposureEv = lerp(exposureEv, 0f),
            toneCurve = lerpCurve(toneCurve),
            redCurve = lerpCurve(redCurve),
            greenCurve = lerpCurve(greenCurve),
            blueCurve = lerpCurve(blueCurve),
            hueShiftDegrees = lerp(hueShiftDegrees, 0f),
            saturationScale = lerp(saturationScale, 1f),
            lightnessScale = lerp(lightnessScale, 1f),
            colorBalance = ColorBalanceAdjustment(
                shadows = lerpRgb(colorBalance.shadows),
                midtones = lerpRgb(colorBalance.midtones),
                highlights = lerpRgb(colorBalance.highlights),
            ),
            grainAmount = lerp(grainAmount, 0f),
            grainSize = grainSize,
        )
    }
}
