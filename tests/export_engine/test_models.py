from pathlib import Path

import pytest

from myphoto.export_engine.models import ExportOptions


def test_valid_options_construct() -> None:
    options = ExportOptions(format="jpeg", output_dir=Path("/out"), quality=90)
    assert options.quality == 90


def test_rejects_unsupported_format() -> None:
    with pytest.raises(ValueError, match="format"):
        ExportOptions(format="gif", output_dir=Path("/out"))  # type: ignore[arg-type]


@pytest.mark.parametrize("quality", [0, 101, -5])
def test_rejects_out_of_range_quality(quality: int) -> None:
    with pytest.raises(ValueError, match="quality"):
        ExportOptions(format="jpeg", output_dir=Path("/out"), quality=quality)
