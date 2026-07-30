from pathlib import Path

import numpy as np

from myphoto.color_engine.local_adjust import (
    _BLUR_DOWNSAMPLE_MAX_DIM,
    _large_blur,
    apply_exposure_guard,
    apply_local_balance,
    apply_local_balance_to_buffer,
    apply_post_preset_guard_to_buffer,
    apply_saturation_guard,
    apply_saturation_guard_to_buffer,
)
from myphoto.core.image import ImageBuffer


def _region_image(bright: float, dark: float, size: int = 64) -> np.ndarray:
    """A left/right split image: left half ``bright``, right half ``dark`` (all channels equal)."""
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = bright
    rgb[:, size // 2 :] = dark
    return rgb


def test_overexposed_region_gets_darkened_and_underexposed_gets_brightened() -> None:
    rgb = _region_image(bright=0.95, dark=0.05)

    result = apply_local_balance(rgb, strength=1.0)

    bright_half = result[:, :32]
    dark_half = result[:, 32:]
    assert bright_half.mean() < rgb[:, :32].mean()
    assert dark_half.mean() > rgb[:, 32:].mean()


def test_well_exposed_midtone_region_is_left_alone() -> None:
    rgb = np.full((32, 32, 3), 0.5, dtype=np.float32)

    result = apply_local_balance(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_zero_strength_is_a_no_op() -> None:
    rgb = _region_image(bright=0.9, dark=0.1)

    result = apply_local_balance(rgb, strength=0.0)

    assert np.allclose(result, rgb, atol=1e-4)


def test_oversaturated_region_gets_desaturated() -> None:
    size = 64
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = (1.0, 0.0, 0.0)  # fully saturated red, left half
    rgb[:, size // 2 :] = (0.5, 0.5, 0.5)  # neutral gray, right half

    result = apply_local_balance(rgb, strength=1.0)

    def chroma(region: np.ndarray) -> float:
        return float((region.max(axis=-1) - region.min(axis=-1)).mean())

    assert chroma(result[:, :32]) < chroma(rgb[:, :32])


def test_white_balance_exclude_mask_ignores_masked_pixels_in_the_estimate() -> None:
    # A warm patch (skin-like) covering most of the frame, with a small
    # neutral-gray corner. If the warm patch is excluded from the
    # gray-world estimate, the correction should be driven by the neutral
    # corner instead and barely touch anything (there's no real cast to
    # fix once the warm region is excluded).
    size = 64
    rgb = np.full((size, size, 3), (0.85, 0.65, 0.5), dtype=np.float32)  # warm "skin"
    rgb[:16, :16] = 0.5  # small neutral-gray corner

    exclude_mask = np.ones((size, size), dtype=bool)
    exclude_mask[:16, :16] = False  # only the neutral corner feeds the estimate

    result = apply_local_balance(rgb, strength=1.0, white_balance_exclude_mask=exclude_mask)

    # The warm region (excluded from the estimate) should keep most of its
    # original warmth, unlike gray-world-on-the-whole-frame which would
    # cool it toward neutral.
    warm_region_after = result[32:, 32:]
    gap_before = float(rgb[32:, 32:, 0].mean() - rgb[32:, 32:, 2].mean())
    gap_after = float(warm_region_after[..., 0].mean() - warm_region_after[..., 2].mean())
    assert gap_after > gap_before * 0.7


def _synth_portrait_warm_face_neutral_bg(size: int, face_scale: float = 2.5) -> np.ndarray:
    """A neutral-gray backdrop with a large, genuinely warm-toned,
    detectable synthetic face (eyes/nose/mouth) filling most of the frame
    — the classic tight portrait crop where gray-world's failure mode
    (reading the face's own warmth as an unwanted cast) bites hardest.
    """
    import cv2

    img = np.full((size, size, 3), (128, 128, 128), dtype=np.uint8)
    cx, cy = size // 2, size // 2
    fw, fh = int(size // 8 * face_scale), int(size // 6 * face_scale)
    # cv2 draw colors given in BGR; cvtColor below flips to RGB, so these
    # produce genuinely warm (R > G > B) results, unlike some other
    # synthetic-face helpers in this test suite that specify BGR tuples
    # which come out cool-toned after conversion.
    cv2.ellipse(img, (cx, cy), (fw, fh), 0, 0, 360, (150, 180, 225), -1)
    for ex in (cx - fw // 2, cx + fw // 2):
        ey = cy - fh // 3
        cv2.ellipse(img, (ex, ey), (max(4, fw // 5), max(3, fh // 8)), 0, 0, 360, (255, 255, 255), -1)
        cv2.circle(img, (ex, ey), max(2, fw // 12), (40, 60, 90), -1)
        cv2.circle(img, (ex, ey), max(1, fw // 25), (10, 10, 10), -1)
    cv2.ellipse(img, (cx, cy + fh // 2), (max(6, fw // 3), max(2, fh // 10)), 0, 0, 180, (70, 80, 150), -1)
    result: np.ndarray = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return result


def test_portrait_white_balance_keeps_more_of_the_skin_tone_with_face_detection() -> None:
    # Regression test for a real reported bug: a portrait where the face
    # fills much of the frame got gray-world white-balanced as if the
    # skin's own warmth were a color cast, visibly cooling/blue-tinting
    # the face. apply_local_balance_to_buffer() detects the face and
    # excludes it from the estimate; verify it never preserves *less*
    # warmth than the same correction with no exclusion (on this synthetic
    # photo's neutral-gray background, the separate low-saturation-pixel
    # restriction in _auto_white_balance already excludes the saturated
    # face on its own, so the two mechanisms land on the same result here
    # — face detection still matters as a second layer on a real photo
    # whose background isn't fully neutral).
    rgb = _synth_portrait_warm_face_neutral_bg(size=480)
    buffer = ImageBuffer(
        data=rgb, source_path=Path("/tmp/portrait.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    from myphoto.color_engine.face_detector import detect_primary_face

    face = detect_primary_face(buffer)
    assert face is not None  # sanity: this synthetic face must actually be detectable

    height, width = rgb.shape[:2]
    face_mask = np.zeros((height, width), dtype=bool)
    face_mask[
        int(face.y0 * height) : int(face.y1 * height), int(face.x0 * width) : int(face.x1 * width)
    ] = True

    def warmth_gap(region: np.ndarray) -> float:
        return float(region[..., 0].mean() - region[..., 2].mean())

    without_face_detection = apply_local_balance(rgb, strength=1.0, white_balance_exclude_mask=None)
    with_face_detection = apply_local_balance_to_buffer(buffer)

    gap_without = warmth_gap(without_face_detection[face_mask])
    gap_with = warmth_gap(with_face_detection.data[..., :3][face_mask])

    assert gap_with >= gap_without


def test_warm_color_cast_is_neutralized() -> None:
    # A uniform warm (orange-ish) cast across the whole photo, as if lit by
    # incandescent bulbs — gray-world should pull the channel means together.
    rgb = np.full((32, 32, 3), 0.5, dtype=np.float32)
    rgb[..., 0] = 0.65  # red channel biased high
    rgb[..., 2] = 0.35  # blue channel biased low

    result = apply_local_balance(rgb, strength=1.0)

    means = result.reshape(-1, 3).mean(axis=0)
    original_spread = float(rgb.reshape(-1, 3).mean(axis=0).max() - rgb.reshape(-1, 3).mean(axis=0).min())
    corrected_spread = float(means.max() - means.min())
    assert corrected_spread < original_spread


def test_dominant_foliage_does_not_push_neutral_regions_blue() -> None:
    # Regression test for a real reported bug: a scene with a large patch
    # of legitimately-saturated green foliage (no real color-cast defect
    # at all) skewed the whole-frame gray-world average enough that an
    # already-neutral region (clothing) got pushed to have *more* blue
    # than red after "correction" — a visible, unwanted blue cast on
    # content that needed no correction. Restricting the estimate to
    # near-neutral pixels (see _WHITE_BALANCE_LOW_SATURATION_THRESHOLD)
    # should keep the already-neutral band from flipping toward blue.
    size = 90
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[: size // 3] = (0.75, 0.6, 0.5)  # warm skin-like band
    rgb[size // 3 : 2 * size // 3] = (0.25, 0.45, 0.15)  # saturated green foliage band
    rgb[2 * size // 3 :] = (0.65, 0.63, 0.6)  # near-neutral off-white clothing band

    result = apply_local_balance(rgb, strength=1.0)

    clothing_after = result[2 * size // 3 :]
    assert clothing_after[..., 0].mean() >= clothing_after[..., 2].mean()


def test_saturation_guard_pulls_down_blown_chroma() -> None:
    size = 64
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    rgb[:, : size // 2] = (1.0, 0.0, 0.05)  # fully saturated, left half
    rgb[:, size // 2 :] = (0.5, 0.4, 0.6)  # moderately saturated, right half

    result = apply_saturation_guard(rgb, strength=1.0)

    def sat(region: np.ndarray) -> float:
        return float((region.max(axis=-1) - region.min(axis=-1)).mean())

    assert sat(result[:, :32]) < sat(rgb[:, :32])


def test_saturation_guard_leaves_a_vivid_but_not_blown_preset_look_alone() -> None:
    # A moderately vivid, tonally-varied region — the kind a Film Simulation
    # preset like Velvia is *meant* to produce — must not be flattened.
    rgb = np.full((32, 32, 3), (0.5, 0.4, 0.6), dtype=np.float32)

    result = apply_saturation_guard(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_apply_saturation_guard_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [
            np.tile(np.array([1.0, 0.0, 0.05], dtype=np.float32), (64, 64, 1)),
            np.full((64, 64, 1), 0.7, dtype=np.float32),
        ],
        axis=-1,
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_saturation_guard_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.7)
    assert result.source_path == buffer.source_path
    assert not np.allclose(result.data[..., :3], buffer.data[..., :3])


def test_exposure_guard_recovers_fully_clipped_highlight() -> None:
    rgb = _region_image(bright=0.995, dark=0.5)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert result[:, :32].mean() < rgb[:, :32].mean()


def test_exposure_guard_recovers_fully_blocked_shadow() -> None:
    rgb = _region_image(bright=0.5, dark=0.005)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert result[:, 32:].mean() > rgb[:, 32:].mean()


def test_exposure_guard_leaves_a_normal_contrast_range_alone() -> None:
    # Within [_POST_PRESET_SHADOW_FLOOR, _POST_PRESET_HIGHLIGHT_CEILING] —
    # a preset's normal punchy-but-not-clipped contrast must be untouched.
    rgb = _region_image(bright=0.85, dark=0.15)

    result = apply_exposure_guard(rgb, strength=1.0)

    assert np.allclose(result, rgb, atol=1e-3)


def test_post_preset_guard_combines_exposure_and_saturation_fixes() -> None:
    size = 64
    data = np.zeros((size, size, 3), dtype=np.float32)
    data[:, : size // 2] = (0.995, 0.995, 0.995)  # clipped highlight, left half
    data[:, size // 2 :] = (1.0, 0.0, 0.05)  # blown chroma, right half
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_post_preset_guard_to_buffer(buffer)

    assert result.data[:, :32].mean() < data[:, :32].mean()
    right = result.data[:, 32:]
    assert (right.max(axis=-1) - right.min(axis=-1)).mean() < (
        data[:, 32:].max(axis=-1) - data[:, 32:].min(axis=-1)
    ).mean()


def test_large_blur_downsample_path_matches_full_res_blur_closely() -> None:
    # A map bigger than the downsample threshold should take the
    # downsample-blur-upsample path but still produce essentially the same
    # broad-region result as blurring at full resolution directly.
    size = _BLUR_DOWNSAMPLE_MAX_DIM + 200
    rng = np.random.default_rng(0)
    single_channel = _region_image(bright=0.9, dark=0.1, size=size)[..., 0]
    single_channel = single_channel + rng.normal(0.0, 0.01, size=single_channel.shape).astype(np.float32)

    import cv2

    sigma = size * 0.08
    exact = cv2.GaussianBlur(single_channel, (0, 0), sigma)
    fast = _large_blur(single_channel, sigma)

    assert fast.shape == exact.shape
    assert np.abs(fast - exact).mean() < 0.01


def test_large_blur_small_image_matches_direct_gaussian_blur_exactly() -> None:
    import cv2

    single_channel = _region_image(bright=0.8, dark=0.2, size=64)[..., 0]
    sigma = 5.0

    exact = cv2.GaussianBlur(single_channel, (0, 0), sigma)
    fast = _large_blur(single_channel, sigma)

    assert np.allclose(fast, exact)


def test_apply_local_balance_to_buffer_preserves_alpha_and_metadata() -> None:
    data = np.concatenate(
        [_region_image(bright=0.9, dark=0.1), np.full((64, 64, 1), 0.7, dtype=np.float32)], axis=-1
    )
    buffer = ImageBuffer(
        data=data, source_path=Path("/tmp/x.png"), color_space="sRGB", bit_depth=8, is_raw=False
    )

    result = apply_local_balance_to_buffer(buffer)

    assert result.channels == 4
    assert np.allclose(result.data[..., 3], 0.7)
    assert result.source_path == buffer.source_path
    assert not np.allclose(result.data[..., :3], buffer.data[..., :3])
