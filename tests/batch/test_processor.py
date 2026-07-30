from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QThreadPool

from myphoto.batch.models import BatchJob
from myphoto.batch.processor import _MAX_EXPORT_THREADS, BatchProcessor
from myphoto.export_engine.models import ExportOptions
from myphoto.preset_engine.engine import PresetEngine
from myphoto.preset_engine.loader import PresetLoader

REPO_PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"


@pytest.fixture
def preset_engine() -> PresetEngine:
    loader = PresetLoader(
        REPO_PRESETS_DIR / "base_profiles", REPO_PRESETS_DIR / "film_simulations"
    )
    return PresetEngine(loader)


def _make_image(path: Path) -> None:
    array = (np.random.default_rng(0).random((6, 6, 3)) * 255).astype(np.uint8)
    Image.fromarray(array).save(path)


def _make_off_center_face_image(path: Path, size: int = 480, offset_x: int = -100) -> None:
    """A real-enough facial structure, off-center, so a crop suggestion is meaningful."""
    cx, cy = size // 2 + offset_x, size // 2
    img = np.full((size, size, 3), (235, 220, 200), dtype=np.uint8)
    cv2.ellipse(img, (cx, cy), (90, 120), 0, 0, 360, (200, 175, 150), -1)
    for ex in (cx - 38, cx + 38):
        ey = cy - 18
        cv2.ellipse(img, (ex, ey), (18, 11), 0, 0, 360, (255, 255, 255), -1)
        cv2.circle(img, (ex, ey), 7, (120, 90, 60), -1)
        cv2.circle(img, (ex, ey), 3, (10, 10, 10), -1)
    cv2.ellipse(img, (cx, cy + 80), (30, 10), 0, 0, 180, (100, 60, 60), -1)
    Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(path)


def test_default_thread_pool_is_capped_regardless_of_core_count(
    preset_engine: PresetEngine,
) -> None:
    # Bounds worst-case concurrent memory/CPU use on high-core-count
    # machines instead of scaling the thread pool with every available
    # core (see BatchProcessor's docstring/module comment for the
    # measured RAM-vs-throughput tradeoff this cap is based on).
    processor = BatchProcessor(preset_engine)
    assert processor._thread_pool.maxThreadCount() <= _MAX_EXPORT_THREADS


def test_processes_all_items_and_reports_progress(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    sources = []
    for i in range(3):
        path = tmp_path / f"img{i}.png"
        _make_image(path)
        sources.append(path)

    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob(tuple(sources), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    progress_calls: list[tuple[int, int]] = []
    processor.progress.connect(lambda done, total: progress_calls.append((done, total)))

    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 3
    assert all(result.succeeded for result in results)
    assert progress_calls[-1] == (3, 3)
    for result in results:
        assert result.output_path is not None
        assert result.output_path.exists()


def test_overall_progress_emits_many_small_monotonic_steps(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    # A progress bar should crawl forward in frequent small steps (one per
    # pipeline checkpoint of every in-flight image), not jump only once
    # per whole (possibly slow) image completion.
    sources = []
    for i in range(2):
        path = tmp_path / f"img{i}.png"
        _make_image(path)
        sources.append(path)

    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob(tuple(sources), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    fractions: list[float] = []
    processor.overall_progress.connect(fractions.append)

    with qtbot.waitSignal(processor.finished, timeout=5000):
        processor.run(job)

    # 2 images x 10 pipeline checkpoints each = 20 stage ticks, plus each
    # item's own completion re-emits once more.
    assert len(fractions) >= 20
    assert all(a <= b + 1e-9 for a, b in pairwise(fractions))
    assert fractions[-1] == pytest.approx(1.0)


def test_overall_progress_on_empty_job_completes_immediately(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    options = ExportOptions(format="png", output_dir=tmp_path / "out")
    job = BatchJob((), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    fractions: list[float] = []
    processor.overall_progress.connect(fractions.append)

    with qtbot.waitSignal(processor.finished, timeout=1000):
        processor.run(job)

    assert fractions == [1.0]


def test_local_balance_enabled_still_succeeds(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options, local_balance_enabled=True)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 1
    assert results[0].succeeded
    assert results[0].output_path is not None
    assert results[0].output_path.exists()


def test_auto_level_enabled_still_succeeds(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options, auto_level_enabled=True)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 1
    assert results[0].succeeded
    assert results[0].output_path is not None
    assert results[0].output_path.exists()


def test_chromatic_aberration_fix_enabled_still_succeeds(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob(
        (path,), "fujifilm", "provia", 1.0, options, fix_chromatic_aberration_enabled=True
    )

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 1
    assert results[0].succeeded
    assert results[0].output_path is not None
    assert results[0].output_path.exists()


def test_auto_sharpen_enabled_still_succeeds(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options, auto_sharpen_enabled=True)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 1
    assert results[0].succeeded
    assert results[0].output_path is not None
    assert results[0].output_path.exists()


def test_auto_suggest_enabled_picks_film_simulation_per_item(
    qtbot, tmp_path: Path, preset_engine: PresetEngine, monkeypatch
) -> None:
    import myphoto.batch.worker as worker_module

    seen_ids: list[str] = []

    def _fake_suggest(buffer, available_ids):
        seen_ids.append("sepia")
        return "sepia"

    monkeypatch.setattr(worker_module, "suggest_film_simulation_id", _fake_suggest)

    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    # film_simulation_id is deliberately "provia" so a differing exported
    # result can only be explained by the per-item auto-suggested override.
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options, auto_suggest_enabled=True)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert results[0].succeeded
    assert seen_ids == ["sepia"]


def test_composition_suggest_enabled_actually_crops_the_export(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_off_center_face_image(path)
    options = ExportOptions(format="png", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options, composition_suggest_enabled=True)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert results[0].succeeded
    with Image.open(results[0].output_path) as exported:
        assert exported.size != (480, 480)


def test_composition_suggest_disabled_exports_full_frame(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_off_center_face_image(path)
    options = ExportOptions(format="png", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert results[0].succeeded
    with Image.open(results[0].output_path) as exported:
        assert exported.size == (480, 480)


def test_missing_source_file_produces_failed_result(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    missing = tmp_path / "missing.png"
    options = ExportOptions(format="png", output_dir=tmp_path / "out")
    job = BatchJob((missing,), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    results = blocker.args[0]
    assert len(results) == 1
    assert not results[0].succeeded
    assert results[0].output_path is None
    assert results[0].error is not None


def test_empty_job_finishes_immediately(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    options = ExportOptions(format="png", output_dir=tmp_path / "out")
    job = BatchJob((), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=1000) as blocker:
        processor.run(job)

    assert blocker.args[0] == []


def test_run_again_after_previous_batch_finished_succeeds(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    with qtbot.waitSignal(processor.finished, timeout=5000):
        processor.run(job)

    # A second, independent batch after the first has fully finished must
    # not be blocked by the re-entrancy guard.
    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)

    assert len(blocker.args[0]) == 1


def test_run_while_previous_batch_in_flight_raises(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    path = tmp_path / "img.png"
    _make_image(path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob((path,), "fujifilm", "provia", 1.0, options)

    processor = BatchProcessor(preset_engine)
    processor.run(job)
    with pytest.raises(RuntimeError):
        processor.run(job)

    with qtbot.waitSignal(processor.finished, timeout=5000):
        pass  # drain the first batch so it doesn't leak into other tests


def test_cancel_marks_not_yet_started_items_as_cancelled(
    qtbot, tmp_path: Path, preset_engine: PresetEngine
) -> None:
    sources = []
    for i in range(5):
        path = tmp_path / f"img{i}.png"
        _make_image(path)
        sources.append(path)

    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")
    job = BatchJob(tuple(sources), "fujifilm", "provia", 1.0, options)

    thread_pool = QThreadPool()
    thread_pool.setMaxThreadCount(1)
    processor = BatchProcessor(preset_engine, thread_pool=thread_pool)

    with qtbot.waitSignal(processor.finished, timeout=5000) as blocker:
        processor.run(job)
        processor.cancel()

    results = blocker.args[0]
    assert len(results) == 5
    assert any(not result.succeeded for result in results)
