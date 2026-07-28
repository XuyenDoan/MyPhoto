package com.myphoto.core

import java.util.Random

/**
 * Orchestrates the Color Pipeline stages in the order defined by the spec:
 * White Balance -> Exposure -> Tone Curve -> RGB Curve -> HSL ->
 * Color Balance -> Film Grain. Mirrors `myphoto.color_engine.pipeline.ColorPipeline`.
 */
class ColorPipeline {

    fun process(
        buffer: ImageBuffer,
        adjustments: ColorAdjustments,
        random: Random = Random(),
    ): ImageBuffer {
        var result = buffer
        result = ColorOperations.applyWhiteBalance(result, adjustments.whiteBalanceTemp, adjustments.whiteBalanceTint)
        result = ColorOperations.applyExposure(result, adjustments.exposureEv)
        result = ColorOperations.applyToneCurve(result, adjustments.toneCurve)
        result = ColorOperations.applyRgbCurves(
            result, adjustments.redCurve, adjustments.greenCurve, adjustments.blueCurve
        )
        result = ColorOperations.applyHsl(
            result, adjustments.hueShiftDegrees, adjustments.saturationScale, adjustments.lightnessScale
        )
        result = ColorOperations.applyColorBalance(result, adjustments.colorBalance)
        result = ColorOperations.applyFilmGrain(result, adjustments.grainAmount, random)
        return ColorOperations.clampToUnitRange(result)
    }
}
