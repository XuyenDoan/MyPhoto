from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QThreadPool

from myphoto.batch.models import BatchJob
from myphoto.batch.processor import BatchProcessor
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
