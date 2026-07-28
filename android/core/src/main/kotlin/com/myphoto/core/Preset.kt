package com.myphoto.core

/** Which layer of the Two-Layer Preset System a preset belongs to. */
enum class PresetKind {
    BASE_PROFILE,
    FILM_SIMULATION,
}

/** One loaded preset: identity plus the color adjustments it applies. */
data class Preset(
    val id: String,
    val name: String,
    val kind: PresetKind,
    val adjustments: ColorAdjustments,
)
