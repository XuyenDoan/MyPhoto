from pathlib import Path

from myphoto.export_engine.naming import build_output_path, extension_for_format


def test_extension_for_format() -> None:
    assert extension_for_format("jpeg") == ".jpg"
    assert extension_for_format("png") == ".png"
    assert extension_for_format("tiff") == ".tif"


def test_appends_myphoto_suffix() -> None:
    path = build_output_path(Path("/src/IMG_0001.CR2"), Path("/out"), "jpeg")
    assert path == Path("/out/IMG_0001_myphoto.jpg")


def test_uses_output_dir_and_format_extension() -> None:
    path = build_output_path(Path("/src/photo.jpg"), Path("/out"), "png")
    assert path == Path("/out/photo_myphoto.png")
