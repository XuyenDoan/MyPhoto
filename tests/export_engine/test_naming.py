from pathlib import Path

from myphoto.export_engine.naming import build_output_path, extension_for_format


def test_extension_for_format() -> None:
    assert extension_for_format("jpeg") == ".jpg"
    assert extension_for_format("png") == ".png"
    assert extension_for_format("tiff") == ".tif"


def test_default_pattern_keeps_stem() -> None:
    path = build_output_path(Path("/src/IMG_0001.CR2"), Path("/out"), "{stem}", 0, "jpeg")
    assert path == Path("/out/IMG_0001.jpg")


def test_pattern_with_index() -> None:
    path = build_output_path(Path("/src/IMG_0001.CR2"), Path("/out"), "MyPhoto_{index:04d}", 7, "png")
    assert path == Path("/out/MyPhoto_0007.png")


def test_pattern_with_original_name() -> None:
    path = build_output_path(Path("/src/photo.jpg"), Path("/out"), "{name}_edit", 0, "tiff")
    assert path == Path("/out/photo.jpg_edit.tif")
