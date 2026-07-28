package com.myphoto.android.export

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore

enum class ExportFormat(val mimeType: String, val compressFormat: Bitmap.CompressFormat, val extension: String) {
    JPEG("image/jpeg", Bitmap.CompressFormat.JPEG, "jpg"),
    PNG("image/png", Bitmap.CompressFormat.PNG, "png"),
}

data class ExportOptions(
    val format: ExportFormat = ExportFormat.JPEG,
    val quality: Int = 95,
    /** Sub-folder of Pictures/ that exports are saved into. */
    val albumName: String = "MyPhoto",
)

/**
 * Writes rendered images into the device gallery via MediaStore. Every
 * export creates a brand-new gallery entry — MediaStore has no notion of
 * "overwrite" here, so the original photo (whichever Uri it came from) is
 * never touched, satisfying the "never overwrite the original" rule the
 * desktop Export Engine also follows.
 */
object MediaStoreExporter {

    fun export(context: Context, bitmap: Bitmap, displayName: String, options: ExportOptions): Uri {
        val resolver = context.contentResolver
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "$displayName.${options.format.extension}")
            put(MediaStore.Images.Media.MIME_TYPE, options.format.mimeType)
            put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/${options.albumName}")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }

        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: throw IllegalStateException("MediaStore rejected the insert for $displayName")

        resolver.openOutputStream(uri)?.use { out ->
            bitmap.compress(options.format.compressFormat, options.quality, out)
        } ?: throw IllegalStateException("Could not open an output stream for $uri")

        values.clear()
        values.put(MediaStore.Images.Media.IS_PENDING, 0)
        resolver.update(uri, values, null, null)

        return uri
    }
}
