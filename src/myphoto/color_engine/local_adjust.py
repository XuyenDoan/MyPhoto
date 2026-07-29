"""Auto white balance, plus local (per-region) exposure and saturation balancing.

Runs in two stages, both gated by the same "Auto-Balance Light & Color"
checkbox: ``apply_local_balance`` (white balance + exposure + saturation)
runs *before* the Film Simulation preset, on the un-styled source photo;
``apply_post_preset_guard_to_buffer`` (exposure guard + saturation guard)
runs *after* it. The preset's own tone curve and hue-selective 3D LUT can
reintroduce clipping/oversaturation that the pre-preset pass had no way to
anticipate, so a single pre-preset-only pass isn't enough to guarantee the
*exported* photo stays within bounds — the post-preset stage is a gentler,
one-directional safety net tuned not to fight each preset's intended
contrast/vividness (see ``apply_exposure_guard`` and
``apply_saturation_guard`` below for how the two differ from their
pre-preset counterparts).

White balance technique: the classic "gray-world" assumption — averaged
over a whole photo, the scene's true colors should roughly cancel out to
neutral gray, so any consistent per-channel bias in the actual average is
treated as a color cast (warm indoor lighting, a cool shade cast, ...) and
scaled back out. This is global (one gain per channel for the whole
photo), unlike the exposure/saturation steps below — a color cast is
normally a property of the light source, not of one region of the frame.

Unlike the rest of the Color Pipeline — one global exposure/tone-curve/HSL
adjustment applied uniformly to the whole image — the exposure/saturation
steps below look at *where* a photo is over/under-exposed or
over-saturated and correct each region on its own. A bright sky and a
shaded foreground in the same frame get pulled toward balanced exposure
independently, instead of one global slider that can only compromise
between the two.

Exposure technique: blur the luminance channel with a large-radius
Gaussian to estimate each region's *local* exposure level (the detail/
texture stays in the un-blurred original), then apply a per-pixel
multiplicative RGB gain to any region whose local luminance strays outside
a safe band (`_EXPOSURE_SAFE_LOW`/`_EXPOSURE_SAFE_HIGH`), pulling it back
toward the nearer edge of that band — not toward a single fixed target.
An earlier version targeted one fixed mid-gray luminance for every region,
the same kind of operation the pipeline's global `apply_exposure()` uses
(`rgb * 2**ev`), just spatially varying; that was discarded after a
statistical test across a batch of synthetic photos showed it also
"corrected" perfectly normal scene contrast along with genuine
over/under-exposure — a naturally bright sky next to a shaded foreground
both get pulled toward the same brightness, flattening real dynamic
range, which a competition judge would read as a worse photo, not a
better one. The band leaves anything that's merely *different*, not
actually blown/blocked, alone. Scaling R/G/B together (rather than
shifting HLS lightness while holding saturation fixed) preserves hue
ratios exactly — HLS saturation is lightness-relative, so pulling a
near-white or near-black pixel toward mid-gray while holding its HLS-S
constant actually *increases* its real chroma, which showed up as a
visible, unwanted color cast on supposedly neutral bright/dark regions
during earlier testing.

Saturation technique: pull down (never up) any region whose *local*
saturation is unusually high, in HLS space, after the exposure pass.
One-directional deliberately: a region that's genuinely gray/neutral (a
wall, an overcast sky) isn't "under-saturated" in need of rescue — forcing
color into it would introduce a false tint, not fix anything.

This is a from-scratch, deterministic image-processing technique — not a
trained model, no network call, no cost.
"""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from myphoto.core.image import ImageBuffer

#: Gray-world white balance gain is clamped to this range so a photo that's
#: legitimately dominated by one color (a sunset, a red wall) doesn't get
#: forced toward an incorrect neutral gray.
_MIN_WHITE_BALANCE_GAIN = 0.75
_MAX_WHITE_BALANCE_GAIN = 1.35

#: Regions whose local luminance strays outside this band are pulled back
#: toward the nearer edge of it — *not* toward a fixed mid-gray target.
#: An earlier version targeted a single 0.5 luminance for every region,
#: which "corrected" perfectly normal scene contrast along with genuine
#: defects (a naturally bright sky next to a shaded foreground would both
#: get pulled toward the same brightness, flattening real dynamic range —
#: found via statistical testing across a batch of synthetic photos).
#: A band leaves any region that's merely *different*, not actually
#: over/under-exposed, alone.
_EXPOSURE_SAFE_HIGH = 0.85
_EXPOSURE_SAFE_LOW = 0.15

#: Regions whose local saturation exceeds this are pulled back down toward
#: it; regions below it are left alone (see module docstring).
_MAX_TARGET_SATURATION = 0.55

#: Gaussian blur radius as a fraction of the image's longer side — large
#: enough to capture "this whole area is blown out", not per-pixel noise.
_BLUR_SIGMA_FRACTION = 0.08

#: Multiplicative exposure gain is clamped to this range (~-1/+1.1 stops)
#: so this stays a corrective nudge rather than a heavy-handed rewrite.
_MIN_EXPOSURE_GAIN = 0.5
_MAX_EXPOSURE_GAIN = 2.2

#: Floor for local luminance before computing a gain ratio, so a
#: near-black region doesn't produce a runaway gain.
_MIN_LUMINANCE_FOR_GAIN = 0.03

_MAX_SATURATION_SHIFT = 0.4

#: A separate, gentler saturation ceiling applied *after* the Film
#: Simulation preset (see ``apply_saturation_guard``). Deliberately higher
#: than ``_MAX_TARGET_SATURATION``: a vivid preset like Velvia is
#: *supposed* to sit well above typical saturation, so this only steps in
#: for a genuinely blown-out region — one a preset's own hue-selective LUT
#: pushed further than the pre-preset pass (which ran on the un-styled
#: source) could have anticipated.
_POST_PRESET_MAX_SATURATION = 0.9
_POST_PRESET_MAX_SATURATION_SHIFT = 1.0

#: The saturation guard uses a *tighter* blur radius than the pre-preset
#: pass: a preset's hue-selective LUT can introduce thin, sharply-defined
#: bands of blown chroma (e.g. right along a strong color-boundary edge)
#: that a wide blur averages away, under-correcting the actual peak pixel
#: values even though the blurred estimate looks fine.
_POST_PRESET_SATURATION_BLUR_FRACTION = 0.02

#: Post-preset exposure safety net: only pixels whose *local* luminance
#: sits outside this band get pulled back toward the nearer edge of it —
#: a preset's own tone curve (e.g. Acros' punchy contrast, Eterna's flat
#: low-contrast look) is otherwise left alone. Much tighter than the
#: pre-preset pass's 0.5 target: this isn't re-exposing the photo, just
#: recovering genuine full clipping the preset's tone curve introduced.
_POST_PRESET_HIGHLIGHT_CEILING = 0.95
_POST_PRESET_SHADOW_FLOOR = 0.04
_POST_PRESET_EXPOSURE_MIN_GAIN = 0.6
_POST_PRESET_EXPOSURE_MAX_GAIN = 1.8

#: These blurs only need to capture "roughly how bright/saturated is this
#: broad area", not per-pixel resolution — so on a large photo (a modern
#: camera easily produces 12+ megapixels), blurring at full resolution
#: wastes most of its time on precision the result doesn't use. Above this
#: size, the map is downsampled before blurring and the result upsampled
#: back, which is dramatically faster for a large-radius blur without a
#: visible difference (a 12MP photo's local-exposure map doesn't need
#: 12 million samples to describe "the sky is bright, the ground is dark").
_BLUR_DOWNSAMPLE_MAX_DIM = 768


def _large_blur(single_channel: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian-blur a single-channel float32 map, downsampling first if the
    image is larger than ``_BLUR_DOWNSAMPLE_MAX_DIM`` on its longer side.
    """
    height, width = single_channel.shape[:2]
    longer_side = max(height, width)
    if longer_side <= _BLUR_DOWNSAMPLE_MAX_DIM:
        result: np.ndarray = cv2.GaussianBlur(single_channel, (0, 0), sigma)
        return result

    scale = _BLUR_DOWNSAMPLE_MAX_DIM / longer_side
    small_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    small = cv2.resize(single_channel, small_size, interpolation=cv2.INTER_AREA)
    blurred_small = cv2.GaussianBlur(small, (0, 0), max(sigma * scale, 1e-3))
    upsampled: np.ndarray = cv2.resize(blurred_small, (width, height), interpolation=cv2.INTER_LINEAR)
    return upsampled


def _auto_white_balance(rgb: np.ndarray, strength: float) -> np.ndarray:
    """Gray-world white balance: scale channels so their averages match."""
    channel_means = rgb.reshape(-1, 3).mean(axis=0)
    gray_mean = float(channel_means.mean())
    if gray_mean < 1e-4:
        return rgb
    raw_gains = gray_mean / np.maximum(channel_means, 1e-4)
    gains = 1.0 + (raw_gains - 1.0) * strength
    gains = np.clip(gains, _MIN_WHITE_BALANCE_GAIN, _MAX_WHITE_BALANCE_GAIN)
    result: np.ndarray = np.clip(rgb * gains, 0.0, 1.0)
    return result


def _pull_down_saturation(
    rgb: np.ndarray, sigma: float, target: float, max_shift: float, strength: float
) -> np.ndarray:
    """One-directional local saturation clamp: never raises saturation, only
    pulls a region's HLS saturation back toward ``target`` once it exceeds it.
    """
    hls = cv2.cvtColor(rgb, cv2.COLOR_RGB2HLS)
    saturation = hls[..., 2]
    local_saturation = _large_blur(saturation, sigma)
    excess = np.clip(local_saturation - target, 0.0, None)
    saturation_shift = np.clip(excess * strength, 0.0, max_shift)
    hls[..., 2] = np.clip(saturation - saturation_shift, 0.0, 1.0)
    result: np.ndarray = cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)
    return result


def apply_saturation_guard(rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """A gentler, higher-ceiling version of the saturation clamp in
    :func:`apply_local_balance`, meant to run *after* the Film Simulation
    preset rather than before it.

    ``apply_local_balance`` runs on the un-styled source photo, before the
    preset's own hue-selective grading (3D LUT) is applied — so a region
    that was reasonably saturated pre-preset can still come out of a vivid
    preset (Velvia, Classic Chrome, ...) blown out. This is a final safety
    net for that case: it only intervenes on genuinely oversaturated
    regions (``_POST_PRESET_MAX_SATURATION`` sits well above a vivid
    preset's normal range), so it doesn't fight the preset's intended look.
    """
    if strength <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op
    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    sigma = max(rgb.shape[0], rgb.shape[1]) * _POST_PRESET_SATURATION_BLUR_FRACTION
    return _pull_down_saturation(
        clipped, sigma, _POST_PRESET_MAX_SATURATION, _POST_PRESET_MAX_SATURATION_SHIFT, strength
    )


def apply_saturation_guard_to_buffer(buffer: ImageBuffer, strength: float = 1.0) -> ImageBuffer:
    """Apply :func:`apply_saturation_guard` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = apply_saturation_guard(buffer.data[..., :3], strength)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))


def apply_exposure_guard(rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """A one-directional, tight-band exposure safety net meant to run
    *after* the Film Simulation preset rather than before it.

    ``apply_local_balance``'s exposure pass runs on the un-styled source,
    before the preset's own tone curve — so a region that read fine
    pre-preset can still clip after a preset's contrast/tone-curve pass.
    This only recovers pixels whose local luminance has drifted outside
    ``[_POST_PRESET_SHADOW_FLOOR, _POST_PRESET_HIGHLIGHT_CEILING]``,
    pulling them back to that edge — not toward mid-gray — so a preset's
    intended contrast (a punchy Acros black, a soft Eterna highlight)
    isn't flattened.
    """
    if strength <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op
    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    sigma = max(rgb.shape[0], rgb.shape[1]) * _BLUR_SIGMA_FRACTION

    luminance = clipped[..., 0] * 0.2126 + clipped[..., 1] * 0.7152 + clipped[..., 2] * 0.0722
    local_luminance = _large_blur(luminance, sigma)

    highlight_gain = np.where(
        local_luminance > _POST_PRESET_HIGHLIGHT_CEILING,
        _POST_PRESET_HIGHLIGHT_CEILING / np.maximum(local_luminance, 1e-4),
        1.0,
    )
    shadow_gain = np.where(
        local_luminance < _POST_PRESET_SHADOW_FLOOR,
        _POST_PRESET_SHADOW_FLOOR / np.maximum(local_luminance, 1e-4),
        1.0,
    )
    raw_gain = highlight_gain * shadow_gain
    gain = 1.0 + (raw_gain - 1.0) * strength
    gain = np.clip(gain, _POST_PRESET_EXPOSURE_MIN_GAIN, _POST_PRESET_EXPOSURE_MAX_GAIN)
    result: np.ndarray = np.clip(clipped * gain[..., np.newaxis], 0.0, 1.0)
    return result


def apply_exposure_guard_to_buffer(buffer: ImageBuffer, strength: float = 1.0) -> ImageBuffer:
    """Apply :func:`apply_exposure_guard` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = apply_exposure_guard(buffer.data[..., :3], strength)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))


def apply_post_preset_guard_to_buffer(buffer: ImageBuffer, strength: float = 1.0) -> ImageBuffer:
    """Run the full post-preset safety net: exposure guard, then saturation
    guard. This is the counterpart to ``apply_local_balance_to_buffer``
    (which runs *before* the preset) — together they let "Auto-Balance
    Light & Color" catch defects the preset's own tone curve / LUT can
    introduce, not just ones already present in the source photo.
    """
    guarded = apply_exposure_guard_to_buffer(buffer, strength)
    return apply_saturation_guard_to_buffer(guarded, strength)


def apply_local_balance(rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Return a corrected copy of ``rgb`` (``(H, W, 3)`` float32, values in ``[0, 1]``).

    ``strength`` scales the correction linearly; ``0.0`` returns ``rgb``
    unchanged (aside from a clip to ``[0, 1]``), ``1.0`` is the full effect.
    """
    if strength <= 0.0:
        no_op: np.ndarray = np.clip(rgb, 0.0, 1.0).astype(np.float32)
        return no_op

    clipped = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    clipped = _auto_white_balance(clipped, strength)
    sigma = max(rgb.shape[0], rgb.shape[1]) * _BLUR_SIGMA_FRACTION

    luminance = clipped[..., 0] * 0.2126 + clipped[..., 1] * 0.7152 + clipped[..., 2] * 0.0722
    local_luminance = _large_blur(luminance, sigma)

    highlight_gain = np.where(
        local_luminance > _EXPOSURE_SAFE_HIGH,
        _EXPOSURE_SAFE_HIGH / np.maximum(local_luminance, _MIN_LUMINANCE_FOR_GAIN),
        1.0,
    )
    shadow_gain = np.where(
        local_luminance < _EXPOSURE_SAFE_LOW,
        _EXPOSURE_SAFE_LOW / np.maximum(local_luminance, _MIN_LUMINANCE_FOR_GAIN),
        1.0,
    )
    raw_gain = highlight_gain * shadow_gain
    gain = 1.0 + (raw_gain - 1.0) * strength
    gain = np.clip(gain, _MIN_EXPOSURE_GAIN, _MAX_EXPOSURE_GAIN)
    exposed = np.clip(clipped * gain[..., np.newaxis], 0.0, 1.0)

    result = _pull_down_saturation(exposed, sigma, _MAX_TARGET_SATURATION, _MAX_SATURATION_SHIFT, strength)
    return result


def apply_local_balance_to_buffer(buffer: ImageBuffer, strength: float = 1.0) -> ImageBuffer:
    """Apply :func:`apply_local_balance` to ``buffer``'s RGB channels, alpha untouched."""
    rgb = apply_local_balance(buffer.data[..., :3], strength)
    if buffer.channels == 4:
        data = np.concatenate([rgb, buffer.data[..., 3:]], axis=-1)
    else:
        data = rgb
    return replace(buffer, data=data.astype(np.float32))
