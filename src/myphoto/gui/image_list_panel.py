"""Left panel: the imported image list, supporting drag & drop import."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from myphoto.image_loader.formats import is_supported


class ImageListPanel(QWidget):
    """Shows imported image filenames; accepts dropped files/folders."""

    images_dropped = Signal(list)  # list[Path]
    selection_changed = Signal(int)  # index

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._list = QListWidget(self)
        self._list.currentRowChanged.connect(self._on_current_row_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

    def set_paths(self, paths: list[Path]) -> None:
        current = self._list.currentRow()
        self._list.blockSignals(True)
        self._list.clear()
        for path in paths:
            self._list.addItem(QListWidgetItem(path.name))
        if 0 <= current < len(paths):
            self._list.setCurrentRow(current)
        elif paths:
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)

    def _on_current_row_changed(self, row: int) -> None:
        if row >= 0:
            self.selection_changed.emit(row)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        supported = [path for path in paths if is_supported(path)]
        if supported:
            self.images_dropped.emit(supported)
        event.acceptProposedAction()
