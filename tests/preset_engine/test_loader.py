import json
from pathlib import Path

import pytest

from myphoto.core.errors import PresetNotFoundError, PresetValidationError
from myphoto.preset_engine.loader import PresetLoader

REPO_PRESETS_DIR = Path(__file__).resolve().parents[2] / "presets"


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_loads_base_profiles_and_film_simulations(tmp_path: Path) -> None:
    base_dir = tmp_path / "base_profiles"
    sim_dir = tmp_path / "film_simulations"
    _write(base_dir / "sony.json", {"id": "sony", "name": "Sony", "kind": "base_profile"})
    _write(
        sim_dir / "provia.json",
        {"id": "provia", "name": "Provia", "kind": "film_simulation"},
    )

    loader = PresetLoader(base_dir, sim_dir)

    assert [p.id for p in loader.list_base_profiles()] == ["sony"]
    assert [p.id for p in loader.list_film_simulations()] == ["provia"]
    assert loader.get_base_profile("sony").name == "Sony"
    assert loader.get_film_simulation("provia").name == "Provia"


def test_missing_directories_yield_empty_lists(tmp_path: Path) -> None:
    loader = PresetLoader(tmp_path / "missing_base", tmp_path / "missing_sim")
    assert loader.list_base_profiles() == []
    assert loader.list_film_simulations() == []


def test_unknown_preset_id_raises(tmp_path: Path) -> None:
    loader = PresetLoader(tmp_path / "base_profiles", tmp_path / "film_simulations")
    with pytest.raises(PresetNotFoundError):
        loader.get_base_profile("does-not-exist")


def test_malformed_json_raises_validation_error(tmp_path: Path) -> None:
    base_dir = tmp_path / "base_profiles"
    base_dir.mkdir()
    (base_dir / "broken.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(PresetValidationError):
        PresetLoader(base_dir, tmp_path / "film_simulations")


def test_wrong_kind_for_directory_raises_validation_error(tmp_path: Path) -> None:
    base_dir = tmp_path / "base_profiles"
    _write(base_dir / "oops.json", {"id": "oops", "name": "Oops", "kind": "film_simulation"})

    with pytest.raises(PresetValidationError, match="expected kind"):
        PresetLoader(base_dir, tmp_path / "film_simulations")


def test_lut_path_resolved_relative_to_preset_file(tmp_path: Path) -> None:
    sim_dir = tmp_path / "film_simulations"
    _write(
        sim_dir / "custom.json",
        {"id": "custom", "name": "Custom", "kind": "film_simulation", "lut": "custom.npy"},
    )

    loader = PresetLoader(tmp_path / "base_profiles", sim_dir)

    assert loader.get_film_simulation("custom").lut_path == sim_dir / "custom.npy"


def test_shipped_repository_presets_all_load() -> None:
    """The presets actually committed under presets/ must be valid and complete."""
    loader = PresetLoader(
        REPO_PRESETS_DIR / "base_profiles", REPO_PRESETS_DIR / "film_simulations"
    )

    base_ids = {p.id for p in loader.list_base_profiles()}
    sim_ids = {p.id for p in loader.list_film_simulations()}

    assert base_ids == {
        "sony", "canon", "nikon", "fujifilm", "om_system", "panasonic", "leica", "iphone",
    }
    assert sim_ids == {
        "provia", "velvia", "astia", "classic_chrome", "classic_neg",
        "eterna", "acros", "nostalgic_neg", "reala_ace",
    }
