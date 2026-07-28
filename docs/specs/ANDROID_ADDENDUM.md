# Addendum: Android Support

This addendum extends `MYPHOTO_CLAUDE_PROMPT.md` (the original spec) to
cover a native Android app, added after the desktop app's first
functional version was complete. It doesn't replace anything in the
original spec — the Windows desktop app remains the primary target — it
adds a second platform with its own scoped-down requirements.

## Why a separate codebase, not a port

The desktop app is Python + PySide6 + rawpy/LibRaw + OpenCV. None of that
targets Android in a production-usable way:

- PySide6/Qt-for-Android exists but is experimental for Python
  specifically, with a much smaller user base and rougher edges than Qt's
  C++/Android story.
- rawpy (LibRaw), OpenCV's Python bindings, and Pillow have no
  established, maintained Android build path.
- Even if all three were cross-compiled successfully, the resulting APK
  and runtime would be unusual by Android standards (no native UI feel,
  large binary size, uncertain long-term maintainability).

Decision (confirmed with the project owner): build a **native Android app
in Kotlin** (Jetpack Compose), sharing *design* with the desktop app
(same pipeline stages, same preset JSON schema, same UX ideas) but not
*code*. See `docs/Architecture.md`'s Android section for the resulting
module layout and the desktop↔Android parity table.

## Scope on Android (confirmed with the project owner)

- **RAW: out of scope.** Android import is JPEG/PNG (and whatever HEIC
  support the OS provides via `BitmapFactory`) only, via the system Photo
  Picker. No LibRaw/rawpy equivalent is wired up.
- Everything else from the original spec's "MỤC TIÊU" section still
  applies conceptually: drag-in-equivalent import (multi-select photo
  picker), preset selection (Base Profile + Film Simulation), Before/After
  preview, Strength, Film Grain, batch export.
- The original spec's "KHÔNG BAO GỒM" section (no crop/layers/brush/
  healing/object removal/AI portrait/Photoshop-or-Lightroom-clone) applies
  identically to the Android app.

## Known gaps (see `android/README.md` for the full list)

- `:app` (the actual Android application module) was written but could
  not be compiled or run in the environment it was developed in — that
  sandbox's network policy blocks `dl.google.com`/`maven.google.com`,
  which serve the Android Gradle Plugin and Android SDK. Only `:core`
  (pure Kotlin/JVM, resolvable from Maven Central) was built and
  unit-tested there. **Before shipping, open `android/` in Android Studio
  and smoke-test `:app` on a device or emulator.**
- No 3D LUT / ICC profile support on Android yet (matches the fact that
  no shipped preset currently uses a LUT).
- No performance profiling on real hardware for high-megapixel images
  (`core`'s color operations are plain per-pixel Kotlin loops).
- No app icon yet (uses the OS default).
