"""Top-level window: image list (left), preview (center), controls (right),
progress + export bar (bottom).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from myphoto.batch.models import BatchItemResult
from myphoto.core.image import ImageBuffer
from myphoto.gui.controls_panel import ControlsPanel
from myphoto.gui.image_list_panel import ImageListPanel
from myphoto.gui.preview_panel import PreviewPanel
from myphoto.preset_engine.loader import PresetLoader
from myphoto.settings.models import AppSettings
from myphoto.settings.store import SettingsStore
from myphoto.workflow.session import EditSession

_PREVIEW_DEBOUNCE_MS = 150

#: The progress bar's range is fixed at this resolution (not "0 to number
#: of images") so `batch_overall_progress` — updated after every pipeline
#: checkpoint of every in-flight image, not just whole-item completion —
#: can move it in small, frequent steps. `QPropertyAnimation` then eases
#: between those steps instead of snapping, so the bar reads as a smooth
#: crawl rather than a jumpy tick per finished image.
_PROGRESS_RANGE = 1000
_PROGRESS_ANIMATION_MS = 200


class MainWindow(QMainWindow):
    """Wires :class:`EditSession` to the image list, preview, and controls panels."""

    def __init__(
        self,
        preset_loader: PresetLoader,
        settings_store: SettingsStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("MyPhoto")
        self.resize(1280, 800)

        self._settings_store = settings_store
        self._session = EditSession(preset_loader)

        self._image_list_panel = ImageListPanel(self)
        self._preview_panel = PreviewPanel(self)
        self._controls_panel = ControlsPanel(self)
        # The grain checkbox defaults to unchecked; match the session's
        # initial state so the first preview doesn't apply a preset's grain
        # before the user has opted in.
        self._session.grain_amount = self._controls_panel.effective_grain_amount()

        self._export_button = QPushButton("Xuất Ảnh", self)
        self._export_button.setObjectName("primaryButton")
        self._cancel_button = QPushButton("Hủy", self)
        self._cancel_button.setEnabled(False)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setRange(0, _PROGRESS_RANGE)

        self._progress_animation = QPropertyAnimation(self._progress_bar, b"value", self)
        self._progress_animation.setDuration(_PROGRESS_ANIMATION_MS)
        self._progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._tray_icon: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_icon = QSystemTrayIcon(self)
            app = QApplication.instance()
            app_icon = app.windowIcon() if isinstance(app, QApplication) else QIcon()
            fallback_icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self._tray_icon.setIcon(app_icon if not app_icon.isNull() else fallback_icon)

        self._preview_debounce = QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.timeout.connect(self._session.render_preview)

        self._build_layout()
        self._connect_signals()
        self._load_settings()
        self._refresh_preset_lists()

    def _build_layout(self) -> None:
        title_label = QLabel('<span style="color:#F2711C;">My</span>Photo', self)
        title_label.setObjectName("appTitle")
        title_label.setTextFormat(Qt.TextFormat.RichText)

        splitter = QSplitter(self)
        splitter.addWidget(self._image_list_panel)
        splitter.addWidget(self._preview_panel)
        splitter.addWidget(self._controls_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 3)
        splitter.setHandleWidth(2)
        # Give the controls panel a sane minimum width so its two-column
        # correction group and form labels never get squeezed illegibly
        # narrow when the splitter is dragged or the window is resized down.
        self._controls_panel.setMinimumWidth(320)

        bottom_bar = QWidget(self)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.addWidget(self._progress_bar, stretch=1)
        bottom_layout.addWidget(self._cancel_button)
        bottom_layout.addWidget(self._export_button)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        layout.addWidget(title_label)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(bottom_bar)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self._image_list_panel.images_dropped.connect(self._on_images_dropped)
        self._image_list_panel.selection_changed.connect(self._on_selection_changed)

        self._controls_panel.base_profile_changed.connect(self._on_base_profile_changed)
        self._controls_panel.film_simulation_changed.connect(self._on_film_simulation_changed)
        self._controls_panel.strength_changed.connect(self._on_strength_changed)
        self._controls_panel.grain_settings_changed.connect(self._on_grain_changed)
        self._controls_panel.auto_suggest_toggled.connect(self._on_auto_suggest_toggled)
        self._controls_panel.local_balance_toggled.connect(self._on_local_balance_toggled)
        self._controls_panel.auto_level_toggled.connect(self._on_auto_level_toggled)
        self._controls_panel.composition_suggest_toggled.connect(self._on_composition_suggest_toggled)
        self._controls_panel.fix_chromatic_aberration_toggled.connect(
            self._on_fix_chromatic_aberration_toggled
        )
        self._controls_panel.auto_sharpen_toggled.connect(self._on_auto_sharpen_toggled)

        self._session.images_changed.connect(self._on_session_images_changed)
        self._session.preview_ready.connect(self._on_preview_ready)
        self._session.preview_failed.connect(self._on_preview_failed)
        self._session.film_simulation_suggested.connect(
            self._controls_panel.set_current_film_simulation
        )
        self._session.composition_suggested.connect(self._preview_panel.set_composition_suggestion)
        self._session.batch_overall_progress.connect(self._on_batch_overall_progress)
        self._session.batch_finished.connect(self._on_batch_finished)

        self._export_button.clicked.connect(self._on_export_clicked)
        self._cancel_button.clicked.connect(self._session.cancel_export)

    def _load_settings(self) -> None:
        settings = self._settings_store.load() if self._settings_store is not None else AppSettings()
        if settings.last_base_profile_id:
            self._session.base_profile_id = settings.last_base_profile_id
        if settings.last_film_simulation_id:
            self._session.film_simulation_id = settings.last_film_simulation_id
        if settings.export_folder:
            self._controls_panel.set_output_dir(settings.export_folder)

    def _refresh_preset_lists(self) -> None:
        self._controls_panel.set_base_profiles(
            self._session.list_base_profiles(), self._session.base_profile_id
        )
        self._controls_panel.set_film_simulations(
            self._session.list_film_simulations(), self._session.film_simulation_id
        )

    def _on_images_dropped(self, paths: list[Path]) -> None:
        self._session.add_images(paths)

    def _on_session_images_changed(self) -> None:
        self._image_list_panel.set_paths(self._session.image_paths)
        self._schedule_preview()

    def _on_selection_changed(self, index: int) -> None:
        self._session.select(index)
        self._schedule_preview()

    def _on_base_profile_changed(self, preset_id: str) -> None:
        self._session.base_profile_id = preset_id
        self._schedule_preview()

    def _on_film_simulation_changed(self, preset_id: str) -> None:
        self._session.film_simulation_id = preset_id
        self._schedule_preview()

    def _on_strength_changed(self, strength: float) -> None:
        self._session.strength = strength
        self._schedule_preview()

    def _on_grain_changed(self, grain_amount: float) -> None:
        self._session.grain_amount = grain_amount
        self._schedule_preview()

    def _on_auto_suggest_toggled(self, enabled: bool) -> None:
        self._session.auto_suggest_enabled = enabled
        self._schedule_preview()

    def _on_local_balance_toggled(self, enabled: bool) -> None:
        self._session.local_balance_enabled = enabled
        self._schedule_preview()

    def _on_auto_level_toggled(self, enabled: bool) -> None:
        self._session.auto_level_enabled = enabled
        self._schedule_preview()

    def _on_composition_suggest_toggled(self, enabled: bool) -> None:
        self._session.composition_suggest_enabled = enabled
        if not enabled:
            self._preview_panel.set_composition_suggestion(None)
        self._schedule_preview()

    def _on_fix_chromatic_aberration_toggled(self, enabled: bool) -> None:
        self._session.fix_chromatic_aberration_enabled = enabled
        self._schedule_preview()

    def _on_auto_sharpen_toggled(self, enabled: bool) -> None:
        self._session.auto_sharpen_enabled = enabled
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_debounce.start(_PREVIEW_DEBOUNCE_MS)

    def _on_preview_ready(self, original: ImageBuffer, rendered: ImageBuffer) -> None:
        self._preview_panel.set_images(original, rendered)
        self.statusBar().clearMessage()

    def _on_preview_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Xem trước lỗi: {message}", 5000)

    def _on_export_clicked(self) -> None:
        if not self._session.image_paths:
            QMessageBox.information(self, "MyPhoto", "Vui lòng thêm ảnh trước.")
            return
        options = self._controls_panel.export_options()
        if not str(options.output_dir):
            QMessageBox.information(self, "MyPhoto", "Vui lòng chọn thư mục xuất ảnh trước.")
            return

        self._export_button.setEnabled(False)
        self._cancel_button.setEnabled(True)
        self._progress_animation.stop()
        self._progress_bar.setValue(0)

        if self._settings_store is not None:
            self._settings_store.save(
                AppSettings(
                    last_base_profile_id=self._session.base_profile_id,
                    last_film_simulation_id=self._session.film_simulation_id,
                    export_folder=options.output_dir,
                )
            )

        self._session.export_all(options)

    def _on_batch_overall_progress(self, fraction: float) -> None:
        target = round(fraction * _PROGRESS_RANGE)
        self._progress_animation.stop()
        self._progress_animation.setStartValue(self._progress_bar.value())
        self._progress_animation.setEndValue(target)
        self._progress_animation.start()

    def _on_batch_finished(self, results: list[BatchItemResult]) -> None:
        self._export_button.setEnabled(True)
        self._cancel_button.setEnabled(False)
        self._progress_animation.stop()
        self._progress_bar.setValue(_PROGRESS_RANGE)

        failed = [result for result in results if not result.succeeded]
        if failed:
            message = f"Xuất ảnh hoàn tất: {len(results) - len(failed)}/{len(results)} thành công"
            self.statusBar().showMessage(message, 8000)
        else:
            message = f"Xuất ảnh hoàn tất: {len(results)} ảnh"
            self.statusBar().showMessage(message, 5000)

        if self._tray_icon is not None and results:
            self._tray_icon.show()
            self._tray_icon.showMessage("MyPhoto", message, QSystemTrayIcon.MessageIcon.Information, 5000)
