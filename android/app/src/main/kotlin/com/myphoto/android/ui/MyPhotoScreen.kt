package com.myphoto.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import com.myphoto.android.export.ExportFormat
import com.myphoto.android.export.ExportOptions
import com.myphoto.core.Preset

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MyPhotoScreen(
    state: UiState,
    onPickImages: () -> Unit,
    onSelectImage: (Int) -> Unit,
    onBaseProfileSelected: (String) -> Unit,
    onFilmSimulationSelected: (String) -> Unit,
    onStrengthChanged: (Float) -> Unit,
    onGrainChanged: (Float) -> Unit,
    onShowOriginalChanged: (Boolean) -> Unit,
    onExportClicked: (ExportOptions) -> Unit,
    onCancelExport: () -> Unit,
    onStatusMessageShown: () -> Unit,
) {
    val snackbarHostState = remember { SnackbarHostState() }
    var exportFormat by remember { mutableStateOf(ExportFormat.JPEG) }
    var quality by remember { mutableStateOf(95f) }

    LaunchedEffect(state.statusMessage) {
        val message = state.statusMessage
        if (message != null) {
            snackbarHostState.showSnackbar(message)
            onStatusMessageShown()
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("MyPhoto") }) },
        snackbarHost = { SnackbarHost(snackbarHostState) { Snackbar(it) } },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onPickImages) { Text("Chọn ảnh") }
                Text("${state.images.size} ảnh đã chọn")
            }

            if (state.images.isNotEmpty()) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.images.size) { index ->
                        FilterChip(
                            selected = index == state.selectedIndex,
                            onClick = { onSelectImage(index) },
                            label = { Text("Ảnh ${index + 1}") },
                        )
                    }
                }
            }

            PreviewArea(state)

            Row(verticalAlignment = Alignment.CenterVertically) {
                Switch(checked = state.showOriginal, onCheckedChange = onShowOriginalChanged)
                Text("Xem ảnh gốc (Before)")
            }

            PresetDropdown(
                label = "Base Profile",
                presets = state.baseProfiles,
                selectedId = state.baseProfileId,
                onSelected = onBaseProfileSelected,
            )
            PresetDropdown(
                label = "Film Simulation",
                presets = state.filmSimulations,
                selectedId = state.filmSimulationId,
                onSelected = onFilmSimulationSelected,
            )

            LabeledSlider(
                label = "Strength",
                value = state.strength,
                onValueChange = onStrengthChanged,
                valueLabel = "${(state.strength * 100).toInt()}%",
            )
            LabeledSlider(
                label = "Film Grain",
                value = state.grainAmount,
                onValueChange = onGrainChanged,
                valueLabel = "${(state.grainAmount * 100).toInt()}%",
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { exportFormat = ExportFormat.JPEG }) { Text("JPEG") }
                OutlinedButton(onClick = { exportFormat = ExportFormat.PNG }) { Text("PNG") }
                Text("Đang chọn: ${exportFormat.name}", modifier = Modifier.padding(top = 12.dp))
            }
            LabeledSlider(
                label = "Quality",
                value = quality / 100f,
                onValueChange = { quality = it * 100f },
                valueLabel = quality.toInt().toString(),
            )

            if (state.exportProgress != null) {
                val (done, total) = state.exportProgress
                LinearProgressIndicator(
                    progress = { if (total > 0) done.toFloat() / total else 0f },
                    modifier = Modifier.fillMaxWidth(),
                )
                Text("Đang export: $done/$total")
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = {
                        onExportClicked(ExportOptions(format = exportFormat, quality = quality.toInt()))
                    },
                    enabled = state.images.isNotEmpty() && !state.isExporting,
                ) {
                    Text("Export")
                }
                OutlinedButton(onClick = onCancelExport, enabled = state.isExporting) {
                    Text("Hủy")
                }
            }
        }
    }
}

@Composable
private fun PreviewArea(state: UiState) {
    val bitmap = if (state.showOriginal) state.originalPreview else state.renderedPreview
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(320.dp),
        contentAlignment = Alignment.Center,
    ) {
        if (bitmap != null) {
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.fillMaxSize(),
            )
        } else {
            Text(if (state.isRendering) "Đang xử lý..." else "Chọn ảnh để xem trước")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PresetDropdown(
    label: String,
    presets: List<Preset>,
    selectedId: String,
    onSelected: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val selectedName = presets.firstOrNull { it.id == selectedId }?.name ?: selectedId

    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = selectedName,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(),
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            presets.forEach { preset ->
                DropdownMenuItem(
                    text = { Text(preset.name) },
                    onClick = {
                        onSelected(preset.id)
                        expanded = false
                    },
                )
            }
        }
    }
}

@Composable
private fun LabeledSlider(
    label: String,
    value: Float,
    onValueChange: (Float) -> Unit,
    valueLabel: String,
) {
    Column {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(label, style = MaterialTheme.typography.labelLarge)
            Text(valueLabel, style = MaterialTheme.typography.labelLarge)
        }
        Slider(value = value, onValueChange = onValueChange, valueRange = 0f..1f)
    }
}
