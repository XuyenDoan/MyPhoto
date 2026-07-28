package com.myphoto.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.myphoto.android.export.ExportOptions
import com.myphoto.android.ui.MyPhotoScreen
import com.myphoto.android.ui.MyPhotoViewModel
import com.myphoto.android.ui.theme.MyPhotoTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MyPhotoTheme {
                val viewModel: MyPhotoViewModel = viewModel()
                val uiState by viewModel.uiState.collectAsState()

                val pickMedia = rememberLauncherForActivityResult(
                    ActivityResultContracts.PickMultipleVisualMedia()
                ) { uris -> if (uris.isNotEmpty()) viewModel.addImages(uris) }

                MyPhotoScreen(
                    state = uiState,
                    onPickImages = {
                        pickMedia.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    },
                    onSelectImage = viewModel::selectImage,
                    onBaseProfileSelected = viewModel::setBaseProfile,
                    onFilmSimulationSelected = viewModel::setFilmSimulation,
                    onStrengthChanged = viewModel::setStrength,
                    onGrainChanged = viewModel::setGrainAmount,
                    onShowOriginalChanged = viewModel::setShowOriginal,
                    onExportClicked = { options: ExportOptions -> viewModel.exportAll(options) },
                    onCancelExport = viewModel::cancelExport,
                    onStatusMessageShown = viewModel::consumeStatusMessage,
                )
            }
        }
    }
}
