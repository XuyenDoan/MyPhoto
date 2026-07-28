# MyPhoto for Android

A native Android companion to the Windows desktop app, covering the same
core idea — pick photos, apply a Fujifilm-style Film Simulation, adjust
Strength/Grain, export — built as a **separate Kotlin codebase**, not a
port of the Python/PySide6 app. See
[`docs/Architecture.md`](../docs/Architecture.md) for how this fits into
the overall project and why a native rewrite (rather than trying to run
the Python app on Android) was the right call.

## Scope differences from the desktop app

- **No RAW support.** Android import is JPEG/PNG (and whatever
  `BitmapFactory`/HEIC codec the OS provides) via the system Photo Picker.
  RAW decode (LibRaw/rawpy) has no practical Android equivalent and was
  explicitly descoped for this platform.
- **No ICC/3D LUT support yet.** Presets are applied as parametric
  adjustments only (matches the desktop app's default presets, none of
  which currently ship a LUT).
- Export always goes through `MediaStore` into a `Pictures/MyPhoto`
  gallery album — every export is a new gallery item, so like the desktop
  Export Engine, it never touches the original file.

## Module layout

```
android/
  core/   Pure Kotlin/JVM library — ImageBuffer, ColorAdjustments,
          ColorOperations, ColorPipeline, Preset(Loader/Engine),
          preset JSON (de)serialization. No Android dependency at all,
          so it builds and unit-tests with a plain JDK + Gradle.
  app/    The Android application — Jetpack Compose UI, MediaStore export,
          Photo Picker import, DataStore-backed settings, and an
          AssetManager-backed PresetSource that reads the presets JSON
          copied from the repo-root `presets/` at build time.
```

`core`'s design mirrors `src/myphoto/color_engine` and
`src/myphoto/preset_engine` on the desktop side operation-for-operation
(same pipeline order, same `ColorAdjustments` fields, same JSON schema) —
see `docs/Architecture.md` for the parity table. It intentionally does not
share code with the Python package (different language, different
runtime); keeping the two pipelines structurally identical is what keeps
them easy to compare and keep in sync by hand.

## Building

```bash
cd android
./gradlew :core:test      # pure Kotlin/JVM — no Android SDK required
```

Opening `android/` in **Android Studio** (Koala or newer) is the
supported way to build/run `:app` — it will provision the Android SDK,
resolve the Android Gradle Plugin, and let you deploy to a device or
emulator. From the command line, once you have the Android SDK set up
(`ANDROID_HOME`/`local.properties`):

```bash
./gradlew :app:assembleDebug
./gradlew :app:installDebug   # with a device/emulator attached
```

### A note on how this was developed

This module was written and, for `:core`, built and unit-tested (44
JUnit tests, all passing) in a sandboxed environment whose outbound proxy
blocks `dl.google.com` / `maven.google.com` (verified: the CONNECT tunnel
returns 403). Those hosts serve the Android Gradle Plugin and Android SDK
components, so **`:app` was written but could not be compiled or run
here** — no emulator, no real device, no AGP resolution. `root
build.gradle.kts` and `gradle.properties`
(`org.gradle.configureondemand=true`) are deliberately structured so that
`:core` still builds and tests cleanly despite `:app` declaring
Android-only plugins. Treat `:app` as reviewed-but-unverified: open it in
Android Studio and do a real device/emulator smoke test (import photos,
switch presets, check Strength/Grain, export, confirm the files land in
the gallery) before relying on it.

## Known follow-ups

- Performance: `core`'s pixel operations are plain per-pixel Kotlin loops
  (no SIMD/GPU). Fine for a phone-camera-resolution JPEG in testing: not
  yet profiled on a real device at 12–48MP; may need chunking, downscaled
  intermediate buffers, or an `Renderscript`/`GPU`-based path if it's too
  slow in practice.
- No app icon/launch splash yet (uses the OS default).
- No instrumented UI tests (Compose UI testing) — only `:core` has
  automated tests today.
