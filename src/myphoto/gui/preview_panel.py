"""Center panel: Before/After preview with zoom."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QCheckBox, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from myphoto.core.image import ImageBuffer
from myphoto.gui.image_conversion import to_qpixmap

_ZOOM_STEP = 1.15
_MIN_ZOOM = 0.1
_MAX_ZOOM = 8.0


class PreviewPanel(QWidget):
    """Displays either the original or the rendered image, zoomable with the mouse wheel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._original_pixmap: QPixmap | None = None
        self._rendered_pixmap: QPixmap | None = None
        self._zoom = 1.0

        self._show_original_checkbox = QCheckBox("Show Original (Before)", self)
        self._show_original_checkbox.toggled.connect(self._update_display)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidget(self._image_label)
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._show_original_checkbox)
        layout.addWidget(self._scroll_area)

    def set_images(self, original: ImageBuffer, rendered: ImageBuffer) -> None:
        self._original_pixmap = to_qpixmap(original)
        self._rendered_pixmap = to_qpixmap(rendered)
        self._update_display()

    def _update_display(self) -> None:
        pixmap = (
            self._original_pixmap
            if self._show_original_checkbox.isChecked()
            else self._rendered_pixmap
        )
        if pixmap is None:
            return
        scaled_size = pixmap.size() * self._zoom
        self._image_label.setPixmap(pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self._image_label.resize(self._image_label.pixmap().size())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
            self._zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._zoom * factor))
            self._update_display()
            event.accept()
        else:
            super().wheelEvent(event)
