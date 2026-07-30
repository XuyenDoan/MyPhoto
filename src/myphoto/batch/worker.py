"""A single batch item's load -> render -> export unit of work."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from myphoto.batch.models import BatchItemResult, BatchJob
from myphoto.color_engine.auto_level import apply_auto_level_to_buffer
from myphoto.color_engine.chromatic_aberration import correct_chromatic_aberration_to_buffer
from myphoto.color_engine.composition_suggest import apply_composition_crop_to_buffer
from myphoto.color_engine.local_adjust import (
    apply_local_balance_to_buffer,
    apply_post_preset_guard_to_buffer,
)
from myphoto.color_engine.sharpen import apply_sharpen_to_buffer
from myphoto.export_engine.writer import ExportEngine
from myphoto.image_loader.loader import ImageLoader
from myphoto.preset_engine.auto_suggest import suggest_film_simulation_id
from myphoto.preset_engine.engine import PresetEngine

#: Fixed pipeline checkpoints, always emitted in this order regardless of
#: which optional corrections are enabled for the job (a skipped stage
#: still advances the count) — this gives a steady, evenly-spaced stream
#: of progress ticks per item instead of the bar only moving once a whole
#: (possibly slow, multi-second) image finishes end to end.
_STAGE_COUNT = 10


class _WorkerSignals(QObject):
    finished = Signal(object)  # BatchItemResult
    #: (item_index, fraction 0.0-1.0 through this item's own pipeline)
    stage_progress = Signal(int, float)


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
        stage = 0

        def _tick() -> None:
            nonlocal stage
            stage += 1
            self.signals.stage_progress.emit(self._index, stage / _STAGE_COUNT)

        try:
            buffer = self._image_loader.load(source_path)
            _tick()
            if self._job.fix_chromatic_aberration_enabled:
                buffer = correct_chromatic_aberration_to_buffer(buffer)
            _tick()
            if self._job.auto_level_enabled:
                buffer = apply_auto_level_to_buffer(buffer)
            _tick()
            if self._job.local_balance_enabled:
                buffer = apply_local_balance_to_buffer(buffer)
            _tick()
            film_simulation_id = self._job.film_simulation_id
            if self._job.auto_suggest_enabled:
                available_ids = {preset.id for preset in self._preset_engine.loader.list_film_simulations()}
                film_simulation_id = suggest_film_simulation_id(buffer, available_ids)
            _tick()
            if self._job.composition_suggest_enabled:
                buffer = apply_composition_crop_to_buffer(buffer)
            _tick()
            rendered = self._preset_engine.render(
                buffer,
                self._job.base_profile_id,
                film_simulation_id,
                self._job.strength,
                grain_amount=self._job.grain_amount,
            )
            _tick()
            if self._job.local_balance_enabled:
                rendered = apply_post_preset_guard_to_buffer(rendered)
            _tick()
            if self._job.auto_sharpen_enabled:
                rendered = apply_sharpen_to_buffer(rendered)
            _tick()
            output_path = self._export_engine.export(rendered, self._job.export_options)
            _tick()
            result = BatchItemResult(source_path, output_path)
        except Exception as exc:  # noqa: BLE001 - any failure becomes a per-item result, not a crash.
            result = BatchItemResult(source_path, None, str(exc))
        self.signals.finished.emit(result)
