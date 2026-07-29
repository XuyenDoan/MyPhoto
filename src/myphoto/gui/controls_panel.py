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
    auto_suggest_toggled = Signal(bool)
    local_balance_toggled = Signal(bool)
    auto_level_toggled = Signal(bool)
    composition_suggest_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Off by default. Runs before the Base Profile/Film Simulation, on
        # the source photo — see color_engine.local_adjust. Deterministic
        # image processing, not a trained model.
        self._local_balance_checkbox = QCheckBox("Auto-Balance Light & Color (beta)", self)
        self._local_balance_checkbox.setChecked(False)
        self._local_balance_checkbox.setToolTip(
            "Corrects each region of the photo on its own: dims blown-out "
            "highlights, lifts overly dark shadows, and tames patches of "
            "extreme saturation — instead of one global slider that "
            "compromises across the whole image. Runs before the preset, "
            "on the source photo. Deterministic image processing, not a "
            "trained model."
        )
        self._local_balance_checkbox.toggled.connect(self.local_balance_toggled.emit)

        # Off by default. Can crop the photo slightly (rotating a rectangle
        # to level it leaves corner gaps that must be cropped out) — see
        # color_engine.auto_level. Classical edge/line detection, not a
        # trained model.
        self._auto_level_checkbox = QCheckBox("Auto-Level Horizon (beta)", self)
        self._auto_level_checkbox.setChecked(False)
        self._auto_level_checkbox.setToolTip(
            "Detects a tilted horizon or other dominant straight line and "
            "rotates the photo to level it. Rotating necessarily crops a "
            "small amount off each edge. Only acts on a clear, correctable "
            "tilt — a deliberately dramatic angled shot, or a photo with no "
            "confident line, is left untouched."
        )
        self._auto_level_checkbox.toggled.connect(self.auto_level_toggled.emit)

        correction_group = QGroupBox("Smart Correction", self)
        correction_form = QFormLayout(correction_group)
        correction_form.addRow(self._local_balance_checkbox)
        correction_form.addRow(self._auto_level_checkbox)

        # Off by default. Unlike everything else in this panel, this never
        # touches the rendered/exported photo — it only draws a rule-of-
        # thirds grid + a suggested crop rectangle on the preview, for the
        # user to accept (crop it themselves), adjust, or ignore. Uses the
        # same face detector as Auto-suggest, falling back to classical
        # saliency detection when no face is found — see
        # color_engine.composition_suggest.
        self._composition_suggest_checkbox = QCheckBox("Suggest Composition Crop (AI, beta)", self)
        self._composition_suggest_checkbox.setChecked(False)
        self._composition_suggest_checkbox.setToolTip(
            "Draws a rule-of-thirds grid and a suggested crop as a guide "
            "over the preview — a proposal only, never applied to the "
            "exported photo. Finds the main subject via a small face-"
            "detection model, falling back to general visual-saliency "
            "detection when no face is found."
        )
        self._composition_suggest_checkbox.toggled.connect(self.composition_suggest_toggled.emit)

        composition_group = QGroupBox("Composition (suggestion only)", self)
        composition_form = QFormLayout(composition_group)
        composition_form.addRow(self._composition_suggest_checkbox)

        self._base_profile_combo = QComboBox(self)
        self._base_profile_combo.currentIndexChanged.connect(self._emit_base_profile_changed)

        self._film_simulation_combo = QComboBox(self)
        self._film_simulation_combo.currentIndexChanged.connect(
            self._emit_film_simulation_changed
        )

        # Off by default: manual preset selection stays the norm. This is a
        # heuristic (color statistics), not a trained model — see
        # preset_engine.auto_suggest.
        self._auto_suggest_checkbox = QCheckBox("Auto-suggest Film Simulation (beta)", self)
        self._auto_suggest_checkbox.setChecked(False)
        self._auto_suggest_checkbox.setToolTip(
            "Picks a Film Simulation from the photo's color statistics "
            "(warmth, saturation, contrast, skin/foliage/sky content) — "
            "not AI/machine learning, just a fast starting guess."
        )
        self._auto_suggest_checkbox.toggled.connect(self._on_auto_suggest_toggled)

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
        preset_form.addRow(self._auto_suggest_checkbox)
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
        layout.addWidget(correction_group)
        layout.addWidget(composition_group)
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

    def set_current_film_simulation(self, preset_id: str) -> None:
        """Programmatically move the dropdown (e.g. from auto-suggest) without re-emitting the change."""
        self._film_simulation_combo.blockSignals(True)
        self._select_combo_data(self._film_simulation_combo, preset_id)
        self._film_simulation_combo.blockSignals(False)

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

    def _on_auto_suggest_toggled(self, checked: bool) -> None:
        self._film_simulation_combo.setEnabled(not checked)
        self.auto_suggest_toggled.emit(checked)

    def _on_grain_checkbox_toggled(self, checked: bool) -> None:
        self._grain_slider.setEnabled(checked)
        self._emit_grain_settings_changed()

    def _emit_grain_settings_changed(self) -> None:
        self.grain_settings_changed.emit(self.effective_grain_amount())

    def _browse_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose Export Folder")
        if directory:
            self.set_output_dir(Path(directory))
