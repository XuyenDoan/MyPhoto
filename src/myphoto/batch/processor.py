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
        overall_progress(fraction): emitted after every pipeline checkpoint
            of every in-flight item (not just whole-item completion), so a
            progress bar can move in small, frequent steps instead of
            jumping only once per (possibly slow) full image. ``fraction``
            is the batch's total completion, 0.0-1.0.
        item_finished(BatchItemResult): emitted after each item finishes.
        finished(list[BatchItemResult]): emitted once every item has finished
            (in source order), whether it succeeded, failed, or was cancelled.
    """

    progress = Signal(int, int)
    overall_progress = Signal(float)
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
        #: Each item's own progress through its pipeline, 0.0-1.0 — averaged
        #: across all items for ``overall_progress``.
        self._item_fractions: list[float] = []

    def run(self, job: BatchJob) -> None:
        """Queue every item in ``job`` for background processing.

        Raises ``RuntimeError`` if a previous batch is still in flight:
        calling ``run()`` again before ``finished`` fires would replace
        ``self._active_runnables`` out from under the still-running
        ``QRunnable``s from the first batch, letting PySide6 garbage-collect
        their Python wrappers mid-execution. The UI already prevents this
        (the Export button is disabled for the duration of a batch); this
        guard protects any other caller from the same footgun.
        """
        if self._active_runnables:
            raise RuntimeError("BatchProcessor.run() called while a previous batch is still running")

        self._cancel_event = threading.Event()
        self._results = [None] * len(job.source_paths)
        self._active_runnables = []
        self._item_fractions = [0.0] * len(job.source_paths)

        if not job.source_paths:
            self.overall_progress.emit(1.0)
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
            runnable.signals.stage_progress.connect(self._on_stage_progress)
            self._active_runnables.append(runnable)
            self._thread_pool.start(runnable)

    def cancel(self) -> None:
        """Signal in-flight and not-yet-started items to skip processing."""
        self._cancel_event.set()

    def _on_stage_progress(self, index: int, fraction: float) -> None:
        if index < len(self._item_fractions):
            self._item_fractions[index] = fraction
            self.overall_progress.emit(sum(self._item_fractions) / len(self._item_fractions))

    def _make_on_item_finished(self, index: int) -> Callable[[BatchItemResult], None]:
        def _on_item_finished(result: BatchItemResult) -> None:
            self._results[index] = result
            if index < len(self._item_fractions):
                self._item_fractions[index] = 1.0
            completed = [r for r in self._results if r is not None]
            self.item_finished.emit(result)
            self.progress.emit(len(completed), len(self._results))
            self.overall_progress.emit(sum(self._item_fractions) / len(self._item_fractions))
            if len(completed) == len(self._results):
                self._active_runnables = []
                self.finished.emit(completed)

        return _on_item_finished
