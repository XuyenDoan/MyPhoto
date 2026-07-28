"""A single batch item's load -> render -> export unit of work."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from myphoto.batch.models import BatchItemResult, BatchJob
from myphoto.export_engine.writer import ExportEngine
from myphoto.image_loader.loader import ImageLoader
from myphoto.preset_engine.engine import PresetEngine


class _WorkerSignals(QObject):
    finished = Signal(object)  # BatchItemResult


class BatchItemRunnable(QRunnable):
    """Processes one source image and reports a :class:`BatchItemResult`."""

    def __init__(
        self,
        index: int,
        job: BatchJob,
        image_loader: ImageLoader,
        preset_engine: PresetEngine,
        export_engine: ExportEngine,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._index = index
        self._job = job
        self._image_loader = image_loader
        self._preset_engine = preset_engine
        self._export_engine = export_engine
        self._cancel_event = cancel_event

    def run(self) -> None:
        source_path = self._job.source_paths[self._index]
        if self._cancel_event.is_set():
            self.signals.finished.emit(BatchItemResult(source_path, None, "cancelled"))
            return
        try:
            buffer = self._image_loader.load(source_path)
            rendered = self._preset_engine.render(
                buffer,
                self._job.base_profile_id,
                self._job.film_simulation_id,
                self._job.strength,
                grain_amount=self._job.grain_amount,
            )
            output_path = self._export_engine.export(
                rendered, self._job.export_options, index=self._index
            )
            result = BatchItemResult(source_path, output_path)
        except Exception as exc:  # noqa: BLE001 - any failure becomes a per-item result, not a crash.
            result = BatchItemResult(source_path, None, str(exc))
        self.signals.finished.emit(result)
