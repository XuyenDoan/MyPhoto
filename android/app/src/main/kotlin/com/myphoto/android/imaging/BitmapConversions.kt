package com.myphoto.android.imaging

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import com.myphoto.core.ImageBuffer
import kotlin.math.max

/**
 * Decodes gallery images into [Bitmap]/[ImageBuffer], respecting EXIF
 * orientation. RAW is intentionally not supported on Android (JPEG/PNG/HEIC
 * only) — see docs/Architecture.md.
 */
object BitmapConversions {

    /**
     * Decodes [uri] into a [Bitmap], correctly oriented. If [maxDimension]
     * is set, the image is decoded at (and, if needed, scaled down to) that
     * resolution — used for fast preview rendering; pass `null` for a
     * full-resolution export decode.
     */
    fun decodeBitmap(resolver: ContentResolver, uri: Uri, maxDimension: Int? = null): Bitmap {
        val options = BitmapFactory.Options()
        if (maxDimension != null) {
            options.inJustDecodeBounds = true
            resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
            options.inSampleSize = calculateInSampleSize(options.outWidth, options.outHeight, maxDimension)
            options.inJustDecodeBounds = false
        }

        val bitmap = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, options) }
            ?: throw IllegalArgumentException("Could not decode image: $uri")

        val oriented = applyExifOrientation(resolver, uri, bitmap)
        return if (maxDimension != null) downscaleIfNeeded(oriented, maxDimension) else oriented
    }

    fun bitmapToImageBuffer(bitmap: Bitmap): ImageBuffer {
        val width = bitmap.width
        val height = bitmap.height
        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)

        val data = FloatArray(width * height * 3)
        for (i in pixels.indices) {
            val pixel = pixels[i]
            val base = i * 3
            data[base] = ((pixel shr 16) and 0xFF) / 255f
            data[base + 1] = ((pixel shr 8) and 0xFF) / 255f
            data[base + 2] = (pixel and 0xFF) / 255f
        }
        return ImageBuffer(data, width, height, 3)
    }

    fun imageBufferToBitmap(buffer: ImageBuffer): Bitmap {
        val pixels = IntArray(buffer.width * buffer.height)
        for (i in pixels.indices) {
            val base = i * buffer.channels
            val r = toByte(buffer.data[base])
            val g = toByte(buffer.data[base + 1])
            val b = toByte(buffer.data[base + 2])
            pixels[i] = (0xFF shl 24) or (r shl 16) or (g shl 8) or b
        }
        val bitmap = Bitmap.createBitmap(buffer.width, buffer.height, Bitmap.Config.ARGB_8888)
        bitmap.setPixels(pixels, 0, buffer.width, 0, 0, buffer.width, buffer.height)
        return bitmap
    }

    private fun toByte(value: Float): Int = (value.coerceIn(0f, 1f) * 255f + 0.5f).toInt().coerceIn(0, 255)

    private fun calculateInSampleSize(width: Int, height: Int, maxDimension: Int): Int {
        var sampleSize = 1
        val longerSide = max(width, height)
        while (longerSide / (sampleSize * 2) >= maxDimension) {
            sampleSize *= 2
        }
        return sampleSize
    }

    private fun downscaleIfNeeded(bitmap: Bitmap, maxDimension: Int): Bitmap {
        val longerSide = max(bitmap.width, bitmap.height)
        if (longerSide <= maxDimension) return bitmap
        val scale = maxDimension.toFloat() / longerSide
        val newWidth = max(1, (bitmap.width * scale).toInt())
        val newHeight = max(1, (bitmap.height * scale).toInt())
        return Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
    }

    private fun applyExifOrientation(resolver: ContentResolver, uri: Uri, bitmap: Bitmap): Bitmap {
        val orientation = resolver.openInputStream(uri)?.use { stream ->
            ExifInterface(stream).getAttributeInt(
                ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL
            )
        } ?: ExifInterface.ORIENTATION_NORMAL

        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
            else -> return bitmap
        }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }
}
