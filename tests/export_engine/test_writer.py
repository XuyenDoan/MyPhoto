from pathlib import Path

import cv2
import numpy as np
import piexif
import pytest
from PIL import Image

from myphoto.core.errors import ExportError
from myphoto.core.image import ImageBuffer
from myphoto.export_engine.models import ExportOptions
from myphoto.export_engine.writer import ExportEngine


def _buffer(tmp_path: Path, bit_depth: int = 8, exif: dict | None = None) -> ImageBuffer:
    data = np.random.default_rng(0).random((8, 10, 3)).astype(np.float32)
    return ImageBuffer(
        data=data,
        source_path=tmp_path / "source.png",
        color_space="sRGB",
        bit_depth=bit_depth,
        is_raw=False,
        exif=exif or {},
    )


def test_exports_jpeg_readable_by_pillow(tmp_path: Path) -> None:
    buffer = _buffer(tmp_path)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out", quality=90)

    output_path = ExportEngine().export(buffer, options)

    assert output_path == tmp_path / "out" / "source_myphoto.jpg"
    with Image.open(output_path) as img:
        assert img.mode == "RGB"
        assert img.size == (10, 8)


def test_exports_16bit_png_via_opencv(tmp_path: Path) -> None:
    buffer = _buffer(tmp_path, bit_depth=16)
    options = ExportOptions(format="png", output_dir=tmp_path / "out")

    output_path = ExportEngine().export(buffer, options)

    loaded = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    assert loaded.dtype == np.uint16
    assert loaded.shape == (8, 10, 3)


def test_exports_8bit_tiff_when_source_is_8bit(tmp_path: Path) -> None:
    buffer = _buffer(tmp_path, bit_depth=8)
    options = ExportOptions(format="tiff", output_dir=tmp_path / "out")

    output_path = ExportEngine().export(buffer, options)

    loaded = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    assert loaded.dtype == np.uint8


def test_refuses_to_overwrite_source_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The "_myphoto" suffix makes a real collision with the source filename
    # unreachable through normal use; force one to verify the safety check
    # (defense-in-depth against a future naming change) still fires.
    source = tmp_path / "source.jpg"
    data = np.zeros((4, 4, 3), dtype=np.float32)
    buffer = ImageBuffer(
        data=data, source_path=source, color_space="sRGB", bit_depth=8, is_raw=False
    )
    options = ExportOptions(format="jpeg", output_dir=tmp_path)
    monkeypatch.setattr("myphoto.export_engine.writer.build_output_path", lambda *a, **k: source)

    with pytest.raises(ExportError, match="overwrite"):
        ExportEngine().export(buffer, options)


def test_preserves_exif_on_jpeg_export(tmp_path: Path) -> None:
    exif = {
        "0th": {piexif.ImageIFD.Make: b"MyPhotoTest"},
        "Exif": {},
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }
    buffer = _buffer(tmp_path, exif=exif)
    options = ExportOptions(format="jpeg", output_dir=tmp_path / "out")

    output_path = ExportEngine().export(buffer, options)

    reloaded = piexif.load(str(output_path))
    assert reloaded["0th"][piexif.ImageIFD.Make] == b"MyPhotoTest"


def test_creates_output_directory(tmp_path: Path) -> None:
    buffer = _buffer(tmp_path)
    options = ExportOptions(format="png", output_dir=tmp_path / "nested" / "out")

    output_path = ExportEngine().export(buffer, options)

    assert output_path.exists()
