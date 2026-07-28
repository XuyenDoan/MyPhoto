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

data class UiState(
    val images: List<Uri> = emptyList(),
    val selectedIndex: Int? = null,
    val baseProfiles: List<Preset> = emptyList(),
    val filmSimulations: List<Preset> = emptyList(),
    val baseProfileId: String = "fujifilm",
    val filmSimulationId: String = "provia",
    val strength: Float = 1f,
    val grainAmount: Float = 0.5f,
    val showOriginal: Boolean = false,
    val originalPreview: Bitmap? = null,
    val renderedPreview: Bitmap? = null,
    val isRendering: Boolean = false,
    val isExporting: Boolean = false,
    val exportProgress: Pair<Int, Int>? = null,
    val statusMessage: String? = null,
)

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
        previewJob = viewModelScope.launch {
            delay(PREVIEW_DEBOUNCE_MS) // mirrors the desktop app's 150ms QTimer debounce
            renderPreview()
        }
    }

    private suspend fun renderPreview() {
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
                    buffer, state.baseProfileId, state.filmSimulationId, state.strength, state.grainAmount
                )
                bitmap to BitmapConversions.imageBufferToBitmap(renderedBuffer)
            }
            _uiState.update { it.copy(originalPreview = original, renderedPreview = rendered, isRendering = false) }
        } catch (exc: Exception) {
            _uiState.update { it.copy(isRendering = false, statusMessage = "Preview failed: ${exc.message}") }
        }
    }

    fun exportAll(options: ExportOptions) {
        exportJob?.cancel()
        exportJob = viewModelScope.launch {
            val state = _uiState.value
            val images = state.images
            if (images.isEmpty()) return@launch

            _uiState.update { it.copy(isExporting = true, exportProgress = 0 to images.size) }
            val application = getApplication<Application>()
            var succeeded = 0

            for ((index, uri) in images.withIndex()) {
                if (!isActive) break
                try {
                    withContext(Dispatchers.Default) {
                        val bitmap = BitmapConversions.decodeBitmap(application.contentResolver, uri, maxDimension = null)
                        val buffer = BitmapConversions.bitmapToImageBuffer(bitmap)
                        val rendered = presetEngine.render(
                            buffer, state.baseProfileId, state.filmSimulationId, state.strength, state.grainAmount
                        )
                        val renderedBitmap = BitmapConversions.imageBufferToBitmap(rendered)
                        val name = "myphoto_${System.currentTimeMillis()}_$index"
                        MediaStoreExporter.export(application, renderedBitmap, name, options)
                    }
                    succeeded++
                } catch (exc: Exception) {
                    // A single failed item doesn't abort the batch — mirrors the desktop BatchProcessor.
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

    private companion object {
        const val PREVIEW_MAX_DIMENSION = 1600
        const val PREVIEW_DEBOUNCE_MS = 150L
    }
}
