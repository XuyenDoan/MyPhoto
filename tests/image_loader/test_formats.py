from myphoto.image_loader.formats import is_raster, is_raw, is_supported


def test_common_raster_extensions_recognized() -> None:
    for ext in (".jpg", ".JPEG", ".png", ".tiff", ".bmp"):
        assert is_raster(f"photo{ext}")
        assert is_supported(f"photo{ext}")
        assert not is_raw(f"photo{ext}")


def test_common_raw_extensions_recognized() -> None:
    for ext in (".cr2", ".NEF", ".arw", ".raf", ".dng"):
        assert is_raw(f"photo{ext}")
        assert is_supported(f"photo{ext}")
        assert not is_raster(f"photo{ext}")


def test_unknown_extension_is_unsupported() -> None:
    assert not is_supported("document.pdf")
    assert not is_raster("document.pdf")
    assert not is_raw("document.pdf")
