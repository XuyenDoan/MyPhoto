"""Center panel: Before/After preview with zoom.

The image is displayed "fit to view" by default: it's scaled down (or up)
to fill the available viewport while preserving its own aspect ratio, so a
portrait photo renders tall-and-narrow and a landscape photo renders
wide-and-short — the panel adapts to the photo's real orientation instead
of always showing a fixed-shape, landscape-biased crop. Ctrl+wheel zooms
further in/out from that fitted baseline.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QCheckBox, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from myphoto.color_engine.composition_suggest import CropSuggestion
from myphoto.core.image import ImageBuffer
from myphoto.gui.image_conversion import to_qpixmap

_ZOOM_STEP = 1.15
_MIN_ZOOM = 0.1
_MAX_ZOOM = 8.0

_GRID_COLOR = QColor(255, 255, 255, 110)
_SUGGESTION_COLOR = QColor(0xF2, 0x71, 0x1C)


class PreviewPanel(QWidget):
    """Displays either the original or the rendered image, zoomable with the mouse wheel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._original_pixmap: QPixmap | None = None
        self._rendered_pixmap: QPixmap | None = None
        #: Multiplier the user applies (via Ctrl+wheel) on top of the
        #: automatic fit-to-view scale; 1.0 means "exactly fitted".
        self._user_zoom = 1.0
        #: A suggested crop to draw as a guide over the *rendered* view only
        #: — never applied to the actual pixels. See
        #: color_engine.composition_suggest.
        self._composition_suggestion: CropSuggestion | None = None

        self._show_original_checkbox = QCheckBox("Hiện Ảnh Gốc (Trước)", self)
        self._show_original_checkbox.toggled.connect(self._update_display)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidget(self._image_label)
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll_area.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._show_original_checkbox)
        layout.addWidget(self._scroll_area)

    def set_images(self, original: ImageBuffer, rendered: ImageBuffer) -> None:
        self._original_pixmap = to_qpixmap(original)
        self._rendered_pixmap = to_qpixmap(rendered)
        self._user_zoom = 1.0
        self._update_display()

    def set_composition_suggestion(self, suggestion: CropSuggestion | None) -> None:
        """Set (or clear) the composition-crop overlay drawn over the *rendered* preview.

        A proposal only — never applied to the actual rendered/exported pixels.
        """
        self._composition_suggestion = suggestion
        self._update_display()

    def _current_pixmap(self) -> QPixmap | None:
        return self._original_pixmap if self._show_original_checkbox.isChecked() else self._rendered_pixmap

    def _fit_scale(self, pixmap: QPixmap) -> float:
        viewport_size = self._scroll_area.viewport().size()
        if pixmap.isNull() or viewport_size.width() <= 0 or viewport_size.height() <= 0:
            return 1.0
        return min(
            viewport_size.width() / pixmap.width(),
            viewport_size.height() / pixmap.height(),
        )

    def _update_display(self) -> None:
        pixmap = self._current_pixmap()
        if pixmap is None:
            return
        effective_scale = self._fit_scale(pixmap) * self._user_zoom
        scaled_size = pixmap.size() * effective_scale
        scaled = pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if self._composition_suggestion is not None and not self._show_original_checkbox.isChecked():
            scaled = self._with_composition_overlay(scaled, effective_scale)
        self._image_label.setPixmap(scaled)
        self._image_label.resize(self._image_label.pixmap().size())

    def _with_composition_overlay(self, pixmap: QPixmap, scale: float) -> QPixmap:
        suggestion = self._composition_suggestion
        if suggestion is None:
            return pixmap

        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width, height = result.width(), result.height()
        grid_pen = QPen(_GRID_COLOR)
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in (1, 2):
            x = round(width * i / 3)
            painter.drawLine(x, 0, x, height)
            y = round(height * i / 3)
            painter.drawLine(0, y, width, y)

        box_pen = QPen(_SUGGESTION_COLOR)
        box_pen.setWidth(3)
        painter.setPen(box_pen)
        painter.drawRect(
            QRectF(
                suggestion.x * scale,
                suggestion.y * scale,
                suggestion.width * scale,
                suggestion.height * scale,
            ).toRect()
        )
        painter.end()
        return result

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self._update_display()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_display()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
            self._user_zoom = max(_MIN_ZOOM, min(_MAX_ZOOM, self._user_zoom * factor))
            self._update_display()
            event.accept()
        else:
            super().wheelEvent(event)
