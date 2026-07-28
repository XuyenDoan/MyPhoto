package com.myphoto.core

/**
 * Internal image representation shared by every pipeline stage: a flat,
 * row-major, channel-interleaved [FloatArray] with values normalized to
 * `[0, 1]`, mirroring `myphoto.core.ImageBuffer` on the desktop side.
 */
class ImageBuffer(
    val data: FloatArray,
    val width: Int,
    val height: Int,
    val channels: Int,
) {
    init {
        require(channels == 3 || channels == 4) {
            "ImageBuffer requires 3 (RGB) or 4 (RGBA) channels, got $channels"
        }
        require(width > 0 && height > 0) { "width and height must be positive" }
        require(data.size == width * height * channels) {
            "data size ${data.size} does not match width*height*channels " +
                "(${width * height * channels})"
        }
    }

    fun copyWithData(newData: FloatArray): ImageBuffer = ImageBuffer(newData, width, height, channels)
}
