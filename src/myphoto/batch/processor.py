"""Runs a :class:`BatchJob` across a ``QThreadPool`` without blocking the UI thread."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, QThreadPool, Signal

from myphoto.batch.models import BatchItemResult, BatchJob
from myphoto.batch.worker import BatchItemRunnable
from myphoto.export_engine.writer import ExportEngine
from myphoto.image_loader.loader import ImageLoader
from myphoto.preset_engine.engine import PresetEngine

#: One less than the number of logical CPUs (minimum 1): each batch item is
#: CPU-bound (decode + full color pipeline + encode), so saturating every
#: core starves the Qt event loop and the UI visibly stutters/lags. Leaving
#: one core headroom keeps the app responsive while still scaling export
#: throughput with the machine's core count.
_EXPORT_THREAD_COUNT = max(1, QThread.idealThreadCount() - 1)


class BatchProcessor(QObject):
    """Fans a :class:`BatchJob` out across a thread pool and reports progress.

    Signals:
        progress(completed, total): emitted after each item finishes.
        item_finished(BatchItemResult): emitted after each item finishes.
        finished(list[BatchItemResult]): emitted once every item has finished
            (in source order), whether it succeeded, failed, or was cancelled.
    """

    progress = Signal(int, int)
    item_finished = Signal(object)
    finished = Signal(list)

    def __init__(
        self,
        preset_engine: PresetEngine,
        thread_pool: QThreadPool | None = None,
        image_loader: ImageLoader | None = None,
        export_engine: ExportEngine | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._preset_engine = preset_engine
        if thread_pool is not None:
            self._thread_pool = thread_pool
        else:
            self._thread_pool = QThreadPool(self)
            self._thread_pool.setMaxThreadCount(_EXPORT_THREAD_COUNT)
        self._image_loader = image_loader if image_loader is not None else ImageLoader()
        self._export_engine = export_engine if export_engine is not None else ExportEngine()
        self._cancel_event = threading.Event()
        self._results: list[BatchItemResult | None] = []
        #: Keeps runnables (and their signal objects) alive until they finish;
        #: without this, PySide6 can garbage-collect a QRunnable mid-emit.
        self._active_runnables: list[BatchItemRunnable] = []

    def run(self, job: BatchJob) -> None:
        """Queue every item in ``job`` for background processing."""
        self._cancel_event = threading.Event()
        self._results = [None] * len(job.source_paths)
        self._active_runnables = []

        if not job.source_paths:
            self.finished.emit([])
            return

        for index in range(len(job.source_paths)):
            runnable = BatchItemRunnable(
                index,
                job,
                self._image_loader,
                self._preset_engine,
                self._export_engine,
                self._cancel_event,
            )
            runnable.setAutoDelete(False)
            runnable.signals.finished.connect(self._make_on_item_finished(index))
            self._active_runnables.append(runnable)
            self._thread_pool.start(runnable)

    def cancel(self) -> None:
        """Signal in-flight and not-yet-started items to skip processing."""
        self._cancel_event.set()

    def _make_on_item_finished(self, index: int) -> Callable[[BatchItemResult], None]:
        def _on_item_finished(result: BatchItemResult) -> None:
            self._results[index] = result
            completed = [r for r in self._results if r is not None]
            self.item_finished.emit(result)
            self.progress.emit(len(completed), len(self._results))
            if len(completed) == len(self._results):
                self.finished.emit(completed)

        return _on_item_finished
