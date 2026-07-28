package com.myphoto.android.ui

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.myphoto.android.data.AppSettings
import com.myphoto.android.data.SettingsRepository
import com.myphoto.android.export.ExportOptions
import com.myphoto.android.export.MediaStoreExporter
import com.myphoto.android.imaging.BitmapConversions
import com.myphoto.android.presets.AssetPresetSource
import com.myphoto.core.Preset
import com.myphoto.core.PresetEngine
import com.myphoto.core.PresetLoader
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicLong

data class UiState(
    val images: List<Uri> = emptyList(),
    val selectedIndex: Int? = null,
    val baseProfiles: List<Preset> = emptyList(),
    val filmSimulations: List<Preset> = emptyList(),
    val baseProfileId: String = "fujifilm",
    val filmSimulationId: String = "provia",
    val strength: Float = 1f,
    val grainAmount: Float = 0.5f,
    val grainEnabled: Boolean = true,
    val showOriginal: Boolean = false,
    val originalPreview: Bitmap? = null,
    val renderedPreview: Bitmap? = null,
    val isRendering: Boolean = false,
    val isExporting: Boolean = false,
    val exportProgress: Pair<Int, Int>? = null,
    val statusMessage: String? = null,
) {
    /** The grain amount actually applied — 0 when the grain checkbox is off, regardless of the slider. */
    val effectiveGrainAmount: Float get() = if (grainEnabled) grainAmount else 0f
}

/**
 * The GUI-facing orchestrator for the Android app — the equivalent of
 * `myphoto.workflow.EditSession` on desktop. Owns the imported image list,
 * current selection, current preset/strength/grain state, drives preview
 * rendering (downsampled, debounced) and full-resolution batch export.
 */
class MyPhotoViewModel(application: Application) : AndroidViewModel(application) {

    private val presetLoader = PresetLoader(AssetPresetSource(application.assets))
    private val presetEngine = PresetEngine(presetLoader)
    private val settingsRepository = SettingsRepository(application)

    private val _uiState = MutableStateFlow(
        UiState(
            baseProfiles = presetLoader.listBaseProfiles(),
            filmSimulations = presetLoader.listFilmSimulations(),
        )
    )
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private var previewJob: Job? = null
    private var exportJob: Job? = null

    /**
     * Bumped on every [schedulePreview] call. [renderPreview] only applies its
     * result if it's still the most recent request when it finishes — plain
     * `Job.cancel()` doesn't stop the non-suspending, CPU-bound decode/render
     * work already in flight, so without this check a slow, stale render
     * (e.g. from a preset picked a moment ago) could finish *after* a newer
     * one and clobber the state with the wrong image — the most likely cause
     * of "picking a new preset doesn't visibly re-color the photo" when
     * switching quickly.
     */
    private val previewRequestId = AtomicLong(0)

    init {
        viewModelScope.launch {
            val saved = settingsRepository.settings.first()
            _uiState.update { state ->
                state.copy(
                    baseProfileId = saved.lastBaseProfileId ?: state.baseProfileId,
                    filmSimulationId = saved.lastFilmSimulationId ?: state.filmSimulationId,
                )
            }
        }
    }

    fun addImages(uris: List<Uri>) {
        _uiState.update { state ->
            val merged = (state.images + uris).distinct()
            val selectedIndex = state.selectedIndex ?: if (merged.isNotEmpty()) 0 else null
            state.copy(images = merged, selectedIndex = selectedIndex)
        }
        schedulePreview()
    }

    fun selectImage(index: Int) {
        _uiState.update { it.copy(selectedIndex = index) }
        schedulePreview()
    }

    fun setBaseProfile(id: String) {
        _uiState.update { it.copy(baseProfileId = id) }
        persistPresetSelection()
        schedulePreview()
    }

    fun setFilmSimulation(id: String) {
        _uiState.update { it.copy(filmSimulationId = id) }
        persistPresetSelection()
        schedulePreview()
    }

    fun setStrength(value: Float) {
        _uiState.update { it.copy(strength = value) }
        schedulePreview()
    }

    fun setGrainAmount(value: Float) {
        _uiState.update { it.copy(grainAmount = value) }
        schedulePreview()
    }

    fun setGrainEnabled(enabled: Boolean) {
        _uiState.update { it.copy(grainEnabled = enabled) }
        schedulePreview()
    }

    fun setShowOriginal(show: Boolean) {
        _uiState.update { it.copy(showOriginal = show) }
    }

    fun consumeStatusMessage() {
        _uiState.update { it.copy(statusMessage = null) }
    }

    private fun persistPresetSelection() {
        viewModelScope.launch {
            val state = _uiState.value
            settingsRepository.save(AppSettings(state.baseProfileId, state.filmSimulationId))
        }
    }

    private fun schedulePreview() {
        previewJob?.cancel()
        val requestId = previewRequestId.incrementAndGet()
        previewJob = viewModelScope.launch {
            delay(PREVIEW_DEBOUNCE_MS) // mirrors the desktop app's 150ms QTimer debounce
            renderPreview(requestId)
        }
    }

    private suspend fun renderPreview(requestId: Long) {
        val state = _uiState.value
        val index = state.selectedIndex ?: return
        val uri = state.images.getOrNull(index) ?: return

        _uiState.update { it.copy(isRendering = true) }
        try {
            val resolver = getApplication<Application>().contentResolver
            val (original, rendered) = withContext(Dispatchers.Default) {
                val bitmap = BitmapConversions.decodeBitmap(resolver, uri, maxDimension = PREVIEW_MAX_DIMENSION)
                val buffer = BitmapConversions.bitmapToImageBuffer(bitmap)
                val renderedBuffer = presetEngine.render(
                    buffer, state.baseProfileId, state.filmSimulationId, state.strength, state.effectiveGrainAmount
                )
                bitmap to BitmapConversions.imageBufferToBitmap(renderedBuffer)
            }

            if (requestId != previewRequestId.get()) {
                // A newer preview was requested while this one was rendering —
                // discard this stale result instead of overwriting a fresher one.
                original.recycle()
                rendered.recycle()
                return
            }
            _uiState.update { it.copy(originalPreview = original, renderedPreview = rendered, isRendering = false) }
        } catch (ce: CancellationException) {
            throw ce
        } catch (t: Throwable) {
            // Catching Throwable (not just Exception) matters here: an
            // OutOfMemoryError from decoding a large bitmap is an Error, not
            // an Exception, and an uncaught one inside a coroutine crashes
            // the whole app rather than just failing this one preview.
            _uiState.update { it.copy(isRendering = false, statusMessage = "Preview failed: ${t.message}") }
        }
    }

    fun exportAll(options: ExportOptions) {
        exportJob?.cancel()
        exportJob = viewModelScope.launch {
            val state = _uiState.value
            val images = state.images
            if (images.isEmpty()) return@launch

            _uiState.update { it.copy(isExporting = true, exportProgress = 0 to images.size) }
            var succeeded = 0

            for ((index, uri) in images.withIndex()) {
                if (!isActive) break
                if (renderAndSave(uri, state, options, "myphoto_${System.currentTimeMillis()}_$index")) {
                    succeeded++
                }
                _uiState.update { it.copy(exportProgress = (index + 1) to images.size) }
            }

            _uiState.update {
                it.copy(
                    isExporting = false,
                    exportProgress = null,
                    statusMessage = "Export finished: $succeeded/${images.size} succeeded",
                )
            }
        }
    }

    fun cancelExport() {
        exportJob?.cancel()
        _uiState.update {
            it.copy(isExporting = false, exportProgress = null, statusMessage = "Export cancelled")
        }
    }

    /** Renders the currently selected photo at full resolution and saves just that one. */
    fun saveCurrentPreview(options: ExportOptions) {
        val state = _uiState.value
        val index = state.selectedIndex
        val uri = index?.let { state.images.getOrNull(it) }
        if (uri == null) {
            _uiState.update { it.copy(statusMessage = "Chưa chọn ảnh nào") }
            return
        }

        exportJob?.cancel()
        exportJob = viewModelScope.launch {
            _uiState.update { it.copy(isExporting = true) }
            val succeeded = renderAndSave(uri, state, options, "myphoto_${System.currentTimeMillis()}")
            _uiState.update {
                it.copy(
                    isExporting = false,
                    statusMessage = if (succeeded) "Đã lưu ảnh vào thư viện" else "Lưu ảnh thất bại",
                )
            }
        }
    }

    /** Decodes [uri] at full resolution, renders it with [state]'s current preset, and saves it. */
    private suspend fun renderAndSave(
        uri: Uri,
        state: UiState,
        options: ExportOptions,
        displayName: String,
    ): Boolean {
        val application = getApplication<Application>()
        return try {
            withContext(Dispatchers.Default) {
                val bitmap = BitmapConversions.decodeBitmap(application.contentResolver, uri, maxDimension = EXPORT_MAX_DIMENSION)
                val buffer = BitmapConversions.bitmapToImageBuffer(bitmap)
                bitmap.recycle() // free the full-resolution source before rendering allocates more
                val rendered = presetEngine.render(
                    buffer, state.baseProfileId, state.filmSimulationId, state.strength, state.effectiveGrainAmount
                )
                val renderedBitmap = BitmapConversions.imageBufferToBitmap(rendered)
                MediaStoreExporter.export(application, renderedBitmap, displayName, options)
                renderedBitmap.recycle()
            }
            true
        } catch (ce: CancellationException) {
            throw ce
        } catch (t: Throwable) {
            // A failed item (including an OutOfMemoryError on a huge photo)
            // doesn't crash the app — mirrors the desktop BatchProcessor.
            false
        }
    }

    private companion object {
        // Smaller than a typical phone screen's width, deliberately: keeps
        // each preview render's transient memory use low (this pipeline
        // allocates a fresh buffer per color stage) so repeated fast preset/
        // photo switching doesn't run the app out of heap.
        const val PREVIEW_MAX_DIMENSION = 1024

        // The color pipeline runs two full passes (base profile + film
        // simulation) of up to 7 stages each, and every non-neutral stage
        // allocates a fresh float32 3-channel buffer the size of the image.
        // Decoding a modern phone photo (12-108MP) at full resolution for
        // export could transiently need several hundred MB to a few GB of
        // buffers, which is why "save"/"export" were silently failing
        // (OutOfMemoryError, caught and reported as failure) on real photos.
        // Capping the export decode at this size keeps peak memory bounded
        // while still being far higher fidelity than the on-screen preview.
        const val EXPORT_MAX_DIMENSION = 2560
        const val PREVIEW_DEBOUNCE_MS = 150L
    }
}
