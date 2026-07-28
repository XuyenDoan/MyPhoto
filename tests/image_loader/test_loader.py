from pathlib import Path

import numpy as np
import piexif
import pytest
from PIL import Image

from myphoto.core.errors import ImageDecodeError, UnsupportedFormatError
from myphoto.image_loader.loader import ImageLoader


def _write_raster(path: Path, mode: str, size: tuple[int, int] = (12, 8)) -> None:
    if mode == "I;16":
        array = np.random.randint(0, 65536, size=(size[1], size[0]), dtype=np.uint16)
        Image.fromarray(array).save(path)
    else:
        array = np.random.randint(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
        Image.fromarray(array, mode="RGB").save(path)


@pytest.mark.parametrize("ext", [".png", ".jpg", ".bmp", ".tif"])
def test_loads_8bit_raster_formats(tmp_path: Path, ext: str) -> None:
    path = tmp_path / f"photo{ext}"
    _write_raster(path, mode="RGB")

    buffer = ImageLoader().load(path)

    assert buffer.is_raw is False
    assert buffer.bit_depth == 8
    assert buffer.color_space == "sRGB"
    assert buffer.data.dtype == np.float32
    assert buffer.data.shape == (8, 12, 3)
    assert buffer.data.min() >= 0.0
    assert buffer.data.max() <= 1.0


def test_loads_16bit_tiff(tmp_path: Path) -> None:
    path = tmp_path / "photo16.tif"
    _write_raster(path, mode="I;16")

    buffer = ImageLoader().load(path)

    assert buffer.bit_depth == 16
    assert buffer.data.max() <= 1.0
    assert buffer.data.min() >= 0.0


def test_applies_exif_orientation_for_portrait_phone_photos(tmp_path: Path) -> None:
    # Sensor-orientation pixels: a wide (landscape) array, exactly what a
    # phone held in portrait writes to disk, tagged with the EXIF
    # Orientation the phone also writes so viewers rotate it 90 degrees CW.
    path = tmp_path / "portrait.jpg"
    array = np.zeros((8, 12, 3), dtype=np.uint8)
    array[:, :6] = (255, 0, 0)  # left half red, right half black
    exif_bytes = piexif.dump({"0th": {piexif.ImageIFD.Orientation: 6}, "Exif": {}, "GPS": {}, "1st": {}})
    Image.fromarray(array, mode="RGB").save(path, exif=exif_bytes)

    buffer = ImageLoader().load(path)

    # Rotating a 12x8 (wide) image 90 degrees CW yields an 8x12 (tall) one.
    assert buffer.data.shape == (12, 8, 3)
    assert buffer.exif["0th"][piexif.ImageIFD.Orientation] == 1


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ImageLoader().load(tmp_path / "missing.png")


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    path = tmp_path / "document.pdf"
    path.write_bytes(b"not an image")

    with pytest.raises(UnsupportedFormatError):
        ImageLoader().load(path)


def test_corrupt_raster_file_raises_decode_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"not actually a png")

    with pytest.raises(ImageDecodeError):
        ImageLoader().load(path)


def test_corrupt_raw_file_raises_decode_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.cr2"
    path.write_bytes(b"not actually a raw file")

    with pytest.raises(ImageDecodeError):
        ImageLoader().load(path)
