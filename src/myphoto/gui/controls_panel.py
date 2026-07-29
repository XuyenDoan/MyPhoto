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
    fix_chromatic_aberration_toggled = Signal(bool)
    auto_sharpen_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Off by default. Runs twice — before the Base Profile/Film
        # Simulation (on the source photo) and again, more gently, after it
        # (as a safety net against clipping the preset's own tone curve/LUT
        # can reintroduce) — see color_engine.local_adjust. Deterministic
        # image processing; the white-balance step also uses the same small
        # local face-detection model as Auto-suggest, only to keep skin
        # tone from being misread as a color cast.
        self._local_balance_checkbox = QCheckBox("Tự Động Cân Bằng Sáng && Màu (beta)", self)
        self._local_balance_checkbox.setChecked(False)
        self._local_balance_checkbox.setToolTip(
            "Tự động chỉnh từng vùng của ảnh riêng biệt: giảm sáng vùng bị "
            "cháy sáng, tăng sáng vùng quá tối, và giảm bớt các mảng màu "
            "quá bão hòa — thay vì dùng một thanh trượt chung ảnh hưởng "
            "toàn bộ ảnh. Chạy trước khi áp preset màu (trên ảnh gốc), và "
            "chạy nhẹ thêm một lần nữa sau khi áp preset để khắc phục hiện "
            "tượng cháy sáng/cháy màu mà chính preset có thể gây ra. Xử lý "
            "ảnh theo thuật toán; riêng bước cân bằng trắng có nhận diện "
            "khuôn mặt (offline, cục bộ) để không hiểu nhầm màu da là ám "
            "màu cần chỉnh."
        )
        self._local_balance_checkbox.toggled.connect(self.local_balance_toggled.emit)

        # Off by default. Can crop the photo slightly (rotating a rectangle
        # to level it leaves corner gaps that must be cropped out) — see
        # color_engine.auto_level. Classical edge/line detection, not a
        # trained model.
        self._auto_level_checkbox = QCheckBox("Tự Động Làm Thẳng Chân Trời (beta)", self)
        self._auto_level_checkbox.setChecked(False)
        self._auto_level_checkbox.setToolTip(
            "Phát hiện chân trời bị nghiêng (hoặc đường thẳng chủ đạo khác) "
            "và xoay ảnh để làm thẳng lại. Việc xoay ảnh sẽ cắt bớt một "
            "phần nhỏ ở mỗi cạnh. Chỉ tác động khi phát hiện độ nghiêng rõ "
            "ràng, có thể sửa được — ảnh chụp nghiêng có chủ đích hoặc "
            "không tìm thấy đường thẳng rõ ràng sẽ được giữ nguyên."
        )
        self._auto_level_checkbox.toggled.connect(self.auto_level_toggled.emit)

        # Off by default. Runs first, on the source photo — a lens defect,
        # not a creative correction — see color_engine.chromatic_aberration.
        # Classical edge detection + color-based defringing, not a trained
        # model.
        self._chromatic_aberration_checkbox = QCheckBox("Khử Viền Màu / Quang Sai (beta)", self)
        self._chromatic_aberration_checkbox.setChecked(False)
        self._chromatic_aberration_checkbox.setToolTip(
            "Khử viền màu tím/xanh mỏng xuất hiện dọc theo các cạnh tương "
            "phản mạnh (lỗi quang học của ống kính, thường nặng hơn ở rìa "
            "ảnh) — ví dụ điển hình là cành cây tối trên nền trời sáng. "
            "Chỉ tác động ngay tại các cạnh tương phản mạnh, nên chủ thể có "
            "màu tím/xanh thật ở vùng không phải cạnh sẽ không bị ảnh "
            "hưởng."
        )
        self._chromatic_aberration_checkbox.toggled.connect(
            self.fix_chromatic_aberration_toggled.emit
        )

        # Off by default. Runs last, after the preset and its grain — see
        # color_engine.sharpen. Deterministic image processing (unsharp
        # masking with a noise threshold), not a trained model.
        self._auto_sharpen_checkbox = QCheckBox("Tự Động Làm Nét (beta)", self)
        self._auto_sharpen_checkbox.setChecked(False)
        self._auto_sharpen_checkbox.setToolTip(
            "Áp dụng một lớp làm nét nhẹ cho ảnh sau khi xử lý xong. Nhờ có "
            "ngưỡng lọc nhiễu, các chi tiết biên độ thấp (nhiễu cảm biến, "
            "hạt phim của preset) sẽ không bị khuếch đại theo cạnh thật, "
            "nên ảnh được làm nét mà không bị nhiễu/hạt nhiều hơn."
        )
        self._auto_sharpen_checkbox.toggled.connect(self.auto_sharpen_toggled.emit)

        correction_group = QGroupBox("Hiệu Chỉnh Thông Minh", self)
        correction_form = QFormLayout(correction_group)
        correction_form.setVerticalSpacing(10)
        correction_form.addRow(self._local_balance_checkbox)
        correction_form.addRow(self._auto_level_checkbox)
        correction_form.addRow(self._chromatic_aberration_checkbox)
        correction_form.addRow(self._auto_sharpen_checkbox)

        # Off by default. Unlike everything else in this panel, this never
        # touches the rendered/exported photo — it only draws a rule-of-
        # thirds grid + a suggested crop rectangle on the preview, for the
        # user to accept (crop it themselves), adjust, or ignore. Uses the
        # same face detector as Auto-suggest, falling back to classical
        # saliency detection when no face is found — see
        # color_engine.composition_suggest.
        self._composition_suggest_checkbox = QCheckBox("Gợi Ý Bố Cục Cắt Ảnh (AI, beta)", self)
        self._composition_suggest_checkbox.setChecked(False)
        self._composition_suggest_checkbox.setToolTip(
            "Vẽ lưới bố cục 1/3 và khung crop gợi ý lên ảnh xem trước — "
            "chỉ là gợi ý, không bao giờ tự động áp dụng lên ảnh xuất ra. "
            "Xác định chủ thể chính bằng mô hình nhận diện khuôn mặt nhỏ, "
            "nếu không thấy khuôn mặt sẽ chuyển sang phát hiện vùng nổi "
            "bật (saliency) của ảnh."
        )
        self._composition_suggest_checkbox.toggled.connect(self.composition_suggest_toggled.emit)

        composition_group = QGroupBox("Bố Cục (chỉ gợi ý)", self)
        composition_form = QFormLayout(composition_group)
        composition_form.setVerticalSpacing(10)
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
        self._auto_suggest_checkbox = QCheckBox("Tự Động Gợi Ý Mô Phỏng Phim (beta)", self)
        self._auto_suggest_checkbox.setChecked(False)
        self._auto_suggest_checkbox.setToolTip(
            "Chọn Mô Phỏng Phim dựa trên thống kê màu sắc của ảnh (độ ấm, "
            "độ bão hòa, độ tương phản, tỉ lệ da/cây lá/bầu trời) — không "
            "phải AI/machine learning, chỉ là một gợi ý khởi điểm nhanh."
        )
        self._auto_suggest_checkbox.toggled.connect(self._on_auto_suggest_toggled)

        self._strength_slider = self._percent_slider(default=100)
        self._strength_slider.valueChanged.connect(
            lambda value: self.strength_changed.emit(value / 100.0)
        )

        # Grain is off by default: a preset's own grain amount only applies
        # once the user explicitly opts in via this checkbox.
        self._grain_checkbox = QCheckBox("Thêm Hạt Phim", self)
        self._grain_checkbox.setChecked(False)
        self._grain_checkbox.toggled.connect(self._on_grain_checkbox_toggled)

        self._grain_slider = self._percent_slider(default=50)
        self._grain_slider.setEnabled(False)
        self._grain_slider.valueChanged.connect(self._emit_grain_settings_changed)

        preset_group = QGroupBox("Mô Phỏng Phim", self)
        preset_form = QFormLayout(preset_group)
        preset_form.setVerticalSpacing(10)
        preset_form.addRow("Máy ảnh gốc", self._base_profile_combo)
        preset_form.addRow("Mô phỏng phim", self._film_simulation_combo)
        preset_form.addRow(self._auto_suggest_checkbox)
        preset_form.addRow("Cường độ", self._strength_slider)
        preset_form.addRow(self._grain_checkbox)
        preset_form.addRow("Độ hạt phim", self._grain_slider)

        self._format_combo = QComboBox(self)
        self._format_combo.addItems(_EXPORT_FORMATS)

        self._quality_spin = QSpinBox(self)
        self._quality_spin.setRange(1, 100)
        self._quality_spin.setValue(95)

        self._output_dir_edit = QLineEdit(self)
        browse_button = QPushButton("Chọn...", self)
        browse_button.clicked.connect(self._browse_output_dir)

        naming_note = QLabel(
            f'Ảnh xuất ra được lưu với tên "&lt;tên&gt;{EXPORT_SUFFIX}" — ảnh gốc không bao giờ bị ghi đè.',
            self,
        )
        naming_note.setObjectName("hintLabel")
        naming_note.setWordWrap(True)

        export_group = QGroupBox("Xuất Ảnh", self)
        export_form = QFormLayout(export_group)
        export_form.setVerticalSpacing(10)
        export_form.addRow("Định dạng", self._format_combo)
        export_form.addRow("Chất lượng", self._quality_spin)
        export_form.addRow("Thư mục xuất", self._output_dir_edit)
        export_form.addRow("", browse_button)
        export_form.addRow(naming_note)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
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
        directory = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất Ảnh")
        if directory:
            self.set_output_dir(Path(directory))
