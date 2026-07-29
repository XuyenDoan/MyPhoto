"""Orchestrates the GUI's image list, current preset/strength/grain state,
preview rendering, and batch export.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from myphoto.batch.models import BatchJob
from myphoto.batch.processor import BatchProcessor
from myphoto.color_engine.local_adjust import apply_local_balance_to_buffer
from myphoto.export_engine.models import ExportOptions
from myphoto.export_engine.writer import ExportEngine
from myphoto.image_loader.loader import ImageLoader
from myphoto.preset_engine.auto_suggest import suggest_film_simulation_id
from myphoto.preset_engine.engine import PresetEngine
from myphoto.preset_engine.loader import PresetLoader
from myphoto.preset_engine.models import Preset
from myphoto.workflow.preview import downscaled


class EditSession(QObject):
    """The single source of truth the GUI reads from and calls into."""

    images_changed = Signal()
    preview_ready = Signal(object, object)  # (original: ImageBuffer, rendered: ImageBuffer)
    preview_failed = Signal(str)
    #: Emitted when auto-suggest picks a different Film Simulation than the
    #: one currently set, so the UI's dropdown can reflect it.
    film_simulation_suggested = Signal(str)
    batch_progress = Signal(int, int)
    batch_item_finished = Signal(object)
    batch_finished = Signal(list)

    PREVIEW_MAX_DIMENSION = 1600

    def __init__(
        self,
        preset_loader: PresetLoader,
        image_loader: ImageLoader | None = None,
        preset_engine: PresetEngine | None = None,
        export_engine: ExportEngine | None = None,
        batch_processor: BatchProcessor | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._preset_loader = preset_loader
        self._image_loader = image_loader if image_loader is not None else ImageLoader()
        self._preset_engine = (
            preset_engine if preset_engine is not None else PresetEngine(preset_loader)
        )
        self._export_engine = export_engine if export_engine is not None else ExportEngine()
        self._batch_processor = (
            batch_processor
            if batch_processor is not None
            else BatchProcessor(
                self._preset_engine,
                image_loader=self._image_loader,
                export_engine=self._export_engine,
            )
        )
        self._batch_processor.progress.connect(self.batch_progress)
        self._batch_processor.item_finished.connect(self.batch_item_finished)
        self._batch_processor.finished.connect(self.batch_finished)

        self.image_paths: list[Path] = []
        self.current_index: int | None = None
        self.base_profile_id = "fujifilm"
        self.film_simulation_id = "provia"
        self.strength = 1.0
        self.grain_amount: float | None = None
        #: When enabled, each `render_preview()` re-picks `film_simulation_id`
        #: via a heuristic (not ML) scene analysis of the loaded image —
        #: see `preset_engine.auto_suggest`.
        self.auto_suggest_enabled = False
        #: When enabled, over/under-exposed and over-saturated regions are
        #: corrected (see `color_engine.local_adjust`) before the Base
        #: Profile/Film Simulation are applied — never touches the
        #: "Show Original" preview, which always stays the true source.
        self.local_balance_enabled = False

    def list_base_profiles(self) -> list[Preset]:
        return self._preset_loader.list_base_profiles()

    def list_film_simulations(self) -> list[Preset]:
        return self._preset_loader.list_film_simulations()

    def add_images(self, paths: list[Path]) -> None:
        """Add newly dropped/opened images, ignoring ones already in the list."""
        for path in paths:
            if path not in self.image_paths:
                self.image_paths.append(path)
        if self.current_index is None and self.image_paths:
            self.current_index = 0
        self.images_changed.emit()

    def remove_image(self, index: int) -> None:
        del self.image_paths[index]
        if not self.image_paths:
            self.current_index = None
        elif self.current_index is not None and self.current_index >= len(self.image_paths):
            self.current_index = len(self.image_paths) - 1
        self.images_changed.emit()

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.image_paths):
            raise IndexError(index)
        self.current_index = index

    def render_preview(self) -> None:
        """Load and render the currently selected image at preview resolution.

        Emits ``preview_ready(original, rendered)`` on success or
        ``preview_failed(message)`` on failure; does nothing if no image is
        selected.
        """
        if self.current_index is None:
            return
        source_path = self.image_paths[self.current_index]
        try:
            original = downscaled(self._image_loader.load(source_path), self.PREVIEW_MAX_DIMENSION)
            working = apply_local_balance_to_buffer(original) if self.local_balance_enabled else original
            if self.auto_suggest_enabled:
                available_ids = {preset.id for preset in self._preset_loader.list_film_simulations()}
                suggested_id = suggest_film_simulation_id(working, available_ids)
                if suggested_id != self.film_simulation_id:
                    self.film_simulation_id = suggested_id
                    self.film_simulation_suggested.emit(suggested_id)
            rendered = self._preset_engine.render(
                working,
                self.base_profile_id,
                self.film_simulation_id,
                self.strength,
                grain_amount=self.grain_amount,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, never fatal.
            self.preview_failed.emit(str(exc))
            return
        self.preview_ready.emit(original, rendered)

    def export_all(self, export_options: ExportOptions) -> None:
        """Batch-export every imported image at full resolution."""
        job = BatchJob(
            source_paths=tuple(self.image_paths),
            base_profile_id=self.base_profile_id,
            film_simulation_id=self.film_simulation_id,
            strength=self.strength,
            export_options=export_options,
            grain_amount=self.grain_amount,
            local_balance_enabled=self.local_balance_enabled,
        )
        self._batch_processor.run(job)

    def cancel_export(self) -> None:
        self._batch_processor.cancel()
