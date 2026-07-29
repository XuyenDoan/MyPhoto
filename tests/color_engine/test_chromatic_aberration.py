from pathlib import Path

import numpy as np

from myphoto.color_engine.chromatic_aberration import (
    correct_chromatic_aberration,
    correct_chromatic_aberration_to_buffer,
)
from myphoto.core.image import ImageBuffer


def _fringed_edge_image(size: int = 64) -> np.ndarray:
    """A strong luminance edge with a purple fringe right on the boundary,
    like lateral chromatic aberration along a dark-branch-against-sky edge.
    """
    rgb = np.full((size, size, 3), 0.85, dtype=np.float32)  # bright "sky"
    rgb[:, size // 2 :] = 0.1  # dark "branch"
    # A thin purple fringe column straddling the edge: R and B boosted, G left low.
    fringe_col = size // 2 - 1
    rgb[:, fringe_col] = (0.6, 0.15, 0.55)
    return rgb


def test_purple_fringe_at_a_strong_edge_is_reduced() -> None:
    rgb = _fringed_edge_image()
    fringe_col = rgb.shape[1] // 2 - 1

    result = correct_chromatic_aberration(rgb, amount=1.0)

    def chroma(pixel_row: np.ndarray) -> float:
        return float(pixel_row.max() - pixel_row.min())

    before = chroma(rgb[0, fringe_col])
    after = chroma(result[0, fringe_col])
    assert after < before


def test_flat_region_purple_is_left_alone() -> None:
    # A uniform purple/magenta region with no edge nearby must not be
    # touched — this could be a real purple flower or fabric, not a lens
    # artifact.
    rgb = np.full((64, 64, 3), (0.6, 0.15, 0.55), dtype=np.float32)

    result = correct_chromatic_aberration(rgb, amount=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_zero_amount_is_a_no_op() -> None:
    rgb = _fringed_edge_image()

    result = correct_chromatic_aberration(rgb, amount=0.0)

    assert np.allclose(result, rgb, atol=1e-4)


def test_apply_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [_fringed_edge_image(), np.full((64, 64, 1), 0.4, dtype=np.float32)], axis=-1
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = correct_chromatic_aberration_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.4)
    assert result.source_path == buffer.source_path
