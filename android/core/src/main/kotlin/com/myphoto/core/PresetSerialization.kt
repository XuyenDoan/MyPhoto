package com.myphoto.core

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Parses preset JSON documents into [Preset]/[ColorAdjustments].
 *
 * This is the Kotlin twin of `myphoto.preset_engine.serialization` on the
 * desktop side — both read the exact same JSON files from `presets/`, so
 * the schema (documented there and in `presets/README.md`) must stay in
 * sync between the two. Every field is optional and defaults to a neutral
 * (no-op) value.
 */
private val json = Json { ignoreUnknownKeys = true }

@Serializable
data class PresetDocument(
    val id: String,
    val name: String,
    val kind: String,
    val lut: String? = null,
    val adjustments: AdjustmentsDto = AdjustmentsDto(),
)

@Serializable
data class AdjustmentsDto(
    @SerialName("white_balance") val whiteBalance: WhiteBalanceDto = WhiteBalanceDto(),
    @SerialName("exposure_ev") val exposureEv: Float = 0f,
    @SerialName("tone_curve") val toneCurve: List<List<Float>>? = null,
    @SerialName("red_curve") val redCurve: List<List<Float>>? = null,
    @SerialName("green_curve") val greenCurve: List<List<Float>>? = null,
    @SerialName("blue_curve") val blueCurve: List<List<Float>>? = null,
    val hsl: HslDto = HslDto(),
    @SerialName("color_balance") val colorBalance: ColorBalanceDto = ColorBalanceDto(),
    val grain: GrainDto = GrainDto(),
)

@Serializable
data class WhiteBalanceDto(val temp: Float = 0f, val tint: Float = 0f)

@Serializable
data class HslDto(
    @SerialName("hue_shift_degrees") val hueShiftDegrees: Float = 0f,
    @SerialName("saturation_scale") val saturationScale: Float = 1f,
    @SerialName("lightness_scale") val lightnessScale: Float = 1f,
)

@Serializable
data class ColorBalanceDto(
    val shadows: List<Float>? = null,
    val midtones: List<Float>? = null,
    val highlights: List<Float>? = null,
)

@Serializable
data class GrainDto(val amount: Float = 0f, val size: Float = 1f)

fun parsePresetDocument(text: String): PresetDocument = json.decodeFromString(PresetDocument.serializer(), text)

fun curveFrom(points: List<List<Float>>?): Curve {
    if (points == null) return IDENTITY_CURVE
    require(points.size >= 2) { "curve must be a list of at least 2 [x, y] points" }
    return points.map { point ->
        require(point.size == 2) { "curve point must be [x, y]" }
        point[0] to point[1]
    }
}

fun rgbFrom(components: List<Float>?): Triple<Float, Float, Float> {
    if (components == null) return Triple(0f, 0f, 0f)
    require(components.size == 3) { "expected a 3-element [r, g, b] list" }
    return Triple(components[0], components[1], components[2])
}

fun presetKindFrom(raw: String): PresetKind = when (raw) {
    "base_profile" -> PresetKind.BASE_PROFILE
    "film_simulation" -> PresetKind.FILM_SIMULATION
    else -> throw IllegalArgumentException("Unknown preset kind: $raw")
}

fun adjustmentsFrom(dto: AdjustmentsDto): ColorAdjustments = ColorAdjustments(
    whiteBalanceTemp = dto.whiteBalance.temp,
    whiteBalanceTint = dto.whiteBalance.tint,
    exposureEv = dto.exposureEv,
    toneCurve = curveFrom(dto.toneCurve),
    redCurve = curveFrom(dto.redCurve),
    greenCurve = curveFrom(dto.greenCurve),
    blueCurve = curveFrom(dto.blueCurve),
    hueShiftDegrees = dto.hsl.hueShiftDegrees,
    saturationScale = dto.hsl.saturationScale,
    lightnessScale = dto.hsl.lightnessScale,
    colorBalance = ColorBalanceAdjustment(
        shadows = rgbFrom(dto.colorBalance.shadows),
        midtones = rgbFrom(dto.colorBalance.midtones),
        highlights = rgbFrom(dto.colorBalance.highlights),
    ),
    grainAmount = dto.grain.amount,
    grainSize = dto.grain.size,
)

fun presetFrom(document: PresetDocument): Preset = Preset(
    id = document.id,
    name = document.name,
    kind = presetKindFrom(document.kind),
    adjustments = adjustmentsFrom(document.adjustments),
)
