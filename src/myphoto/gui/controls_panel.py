"""Right panel: preset selection, strength, grain, and export settings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from myphoto.export_engine.models import ExportFormat, ExportOptions
from myphoto.export_engine.naming import EXPORT_SUFFIX
from myphoto.preset_engine.models import Preset

_EXPORT_FORMATS: tuple[ExportFormat, ...] = ("jpeg", "png", "tiff")


class ControlsPanel(QWidget):
    """Preset/Strength/Grain controls plus the export destination settings."""

    base_profile_changed = Signal(str)
    film_simulation_changed = Signal(str)
    strength_changed = Signal(float)
    #: Emits the *effective* grain amount: 0.0 whenever the grain checkbox
    #: is unchecked, regardless of the slider's saved position.
    grain_settings_changed = Signal(float)

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

        # Grain is off by default: a preset's own grain amount only applies
        # once the user explicitly opts in via this checkbox.
        self._grain_checkbox = QCheckBox("Add Film Grain", self)
        self._grain_checkbox.setChecked(False)
        self._grain_checkbox.toggled.connect(self._on_grain_checkbox_toggled)

        self._grain_slider = self._percent_slider(default=50)
        self._grain_slider.setEnabled(False)
        self._grain_slider.valueChanged.connect(self._emit_grain_settings_changed)

        preset_group = QGroupBox("Film Simulation", self)
        preset_form = QFormLayout(preset_group)
        preset_form.addRow("Base Profile", self._base_profile_combo)
        preset_form.addRow("Film Simulation", self._film_simulation_combo)
        preset_form.addRow("Strength", self._strength_slider)
        preset_form.addRow(self._grain_checkbox)
        preset_form.addRow("Film Grain", self._grain_slider)

        self._format_combo = QComboBox(self)
        self._format_combo.addItems(_EXPORT_FORMATS)

        self._quality_spin = QSpinBox(self)
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(95)

        self._output_dir_edit = QLineEdit(self)
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self._browse_output_dir)

        naming_note = QLabel(
            f'Exported files are saved as "&lt;name&gt;{EXPORT_SUFFIX}" — the original is never overwritten.',
            self,
        )
        naming_note.setObjectName("hintLabel")
        naming_note.setWordWrap(True)

        export_group = QGroupBox("Export", self)
        export_form = QFormLayout(export_group)
        export_form.addRow("Format", self._format_combo)
        export_form.addRow("Quality", self._quality_spin)
        export_form.addRow("Output Folder", self._output_dir_edit)
        export_form.addRow("", browse_button)
        export_form.addRow(naming_note)

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

    def set_base_profiles(self, presets: list[Preset], selected_id: str | None = None) -> None:
        self._base_profile_combo.blockSignals(True)
        self._base_profile_combo.clear()
        for preset in presets:
            self._base_profile_combo.addItem(preset.name, preset.id)
        self._select_combo_data(self._base_profile_combo, selected_id)
        self._base_profile_combo.blockSignals(False)

    def set_film_simulations(self, presets: list[Preset], selected_id: str | None = None) -> None:
        self._film_simulation_combo.blockSignals(True)
        self._film_simulation_combo.clear()
        for preset in presets:
            self._film_simulation_combo.addItem(preset.name, preset.id)
        self._select_combo_data(self._film_simulation_combo, selected_id)
        self._film_simulation_combo.blockSignals(False)

    @staticmethod
    def _select_combo_data(combo: QComboBox, data: str | None) -> None:
        if data is None:
            return
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def selected_base_profile_id(self) -> str | None:
        data: str | None = self._base_profile_combo.currentData()
        return data

    def selected_film_simulation_id(self) -> str | None:
        data: str | None = self._film_simulation_combo.currentData()
        return data

    def effective_grain_amount(self) -> float:
        """0.0 when the grain checkbox is unchecked, else the slider's value."""
        return self._grain_slider.value() / 100.0 if self._grain_checkbox.isChecked() else 0.0

    def output_dir(self) -> Path:
        return Path(self._output_dir_edit.text())

    def set_output_dir(self, path: Path) -> None:
        self._output_dir_edit.setText(str(path))

    def export_options(self) -> ExportOptions:
        return ExportOptions(
            format=self._format_combo.currentText(),  # type: ignore[arg-type]
            output_dir=self.output_dir(),
            quality=self._quality_spin.value(),
        )

    def _emit_base_profile_changed(self) -> None:
        preset_id = self.selected_base_profile_id()
        if preset_id:
            self.base_profile_changed.emit(preset_id)

    def _emit_film_simulation_changed(self) -> None:
        preset_id = self.selected_film_simulation_id()
        if preset_id:
            self.film_simulation_changed.emit(preset_id)

    def _on_grain_checkbox_toggled(self, checked: bool) -> None:
        self._grain_slider.setEnabled(checked)
        self._emit_grain_settings_changed()

    def _emit_grain_settings_changed(self) -> None:
        self.grain_settings_changed.emit(self.effective_grain_amount())

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose Export Folder")
        if directory:
            self.set_output_dir(Path(directory))
