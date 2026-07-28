"""Right panel: preset selection, strength, grain, and export settings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from myphoto.export_engine.models import ExportFormat, ExportOptions
from myphoto.preset_engine.models import Preset

_EXPORT_FORMATS: tuple[ExportFormat, ...] = ("jpeg", "png", "tiff")


class ControlsPanel(QWidget):
    """Preset/Strength/Grain controls plus the export destination settings."""

    base_profile_changed = Signal(str)
    film_simulation_changed = Signal(str)
    strength_changed = Signal(float)
    grain_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._base_profile_combo = QComboBox(self)
        self._base_profile_combo.currentIndexChanged.connect(self._emit_base_profile_changed)

        self._film_simulation_combo = QComboBox(self)
        self._film_simulation_combo.currentIndexChanged.connect(
            self._emit_film_simulation_changed
        )

        self._strength_slider = self._percent_slider(default=100)
        self._strength_slider.valueChanged.connect(
            lambda value: self.strength_changed.emit(value / 100.0)
        )

        self._grain_slider = self._percent_slider(default=50)
        self._grain_slider.valueChanged.connect(
            lambda value: self.grain_changed.emit(value / 100.0)
        )

        preset_group = QGroupBox("Film Simulation", self)
        preset_form = QFormLayout(preset_group)
        preset_form.addRow("Base Profile", self._base_profile_combo)
        preset_form.addRow("Film Simulation", self._film_simulation_combo)
        preset_form.addRow("Strength", self._strength_slider)
        preset_form.addRow("Film Grain", self._grain_slider)

        self._format_combo = QComboBox(self)
        self._format_combo.addItems(_EXPORT_FORMATS)

        self._quality_spin = QSpinBox(self)
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(95)

        self._output_dir_edit = QLineEdit(self)
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self._browse_output_dir)

        self._rename_pattern_edit = QLineEdit("{stem}", self)

        export_group = QGroupBox("Export", self)
        export_form = QFormLayout(export_group)
        export_form.addRow("Format", self._format_combo)
        export_form.addRow("Quality", self._quality_spin)
        export_form.addRow("Output Folder", self._output_dir_edit)
        export_form.addRow("", browse_button)
        export_form.addRow("Rename Pattern", self._rename_pattern_edit)

        layout = QVBoxLayout(self)
        layout.addWidget(preset_group)
        layout.addWidget(export_group)
        layout.addStretch(1)

    @staticmethod
    def _percent_slider(default: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(default)
        return slider

    def set_base_profiles(self, presets: list[Preset]) -> None:
        self._base_profile_combo.blockSignals(True)
        self._base_profile_combo.clear()
        for preset in presets:
            self._base_profile_combo.addItem(preset.name, preset.id)
        self._base_profile_combo.blockSignals(False)

    def set_film_simulations(self, presets: list[Preset]) -> None:
        self._film_simulation_combo.blockSignals(True)
        self._film_simulation_combo.clear()
        for preset in presets:
            self._film_simulation_combo.addItem(preset.name, preset.id)
        self._film_simulation_combo.blockSignals(False)

    def selected_base_profile_id(self) -> str | None:
        data: str | None = self._base_profile_combo.currentData()
        return data

    def selected_film_simulation_id(self) -> str | None:
        data: str | None = self._film_simulation_combo.currentData()
        return data

    def output_dir(self) -> Path:
        return Path(self._output_dir_edit.text())

    def set_output_dir(self, path: Path) -> None:
        self._output_dir_edit.setText(str(path))

    def export_options(self) -> ExportOptions:
        return ExportOptions(
            format=self._format_combo.currentText(),  # type: ignore[arg-type]
            output_dir=self.output_dir(),
            quality=self._quality_spin.value(),
            rename_pattern=self._rename_pattern_edit.text() or "{stem}",
        )

    def _emit_base_profile_changed(self) -> None:
        preset_id = self.selected_base_profile_id()
        if preset_id:
            self.base_profile_changed.emit(preset_id)

    def _emit_film_simulation_changed(self) -> None:
        preset_id = self.selected_film_simulation_id()
        if preset_id:
            self.film_simulation_changed.emit(preset_id)

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose Export Folder")
        if directory:
            self.set_output_dir(Path(directory))
