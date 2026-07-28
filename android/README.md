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

## Getting an APK without installing anything locally

`.github/workflows/android-build.yml` builds `:app`'s debug APK on GitHub
Actions (which has normal internet access, unlike the sandbox this module
was originally developed in) on every push to `main` that touches
`android/**`, and can also be triggered manually from the Actions tab
("Run workflow"). Download the `myphoto-debug-apk` artifact from a
finished run, transfer it to an Android phone, and install it (enable
"install unknown apps" for whichever app you use to open the file).

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

This module was written in a sandboxed environment whose outbound proxy
blocks `dl.google.com` / `maven.google.com` (verified: the CONNECT tunnel
returns 403) — the hosts that serve the Android Gradle Plugin and Android
SDK, so `:app` could not be compiled there. `:core` was built and
unit-tested locally (44 JUnit tests, all passing); `root build.gradle.kts`
and `gradle.properties` (`org.gradle.configureondemand=true`) are
deliberately structured so `:core` builds cleanly on its own despite
`:app` declaring Android-only plugins.

`:app` itself is built and verified by
[`.github/workflows/android-build.yml`](../.github/workflows/android-build.yml)
on GitHub Actions (which has normal internet access) — `./gradlew
:app:assembleDebug` succeeds there and produces an installable debug APK
on every push to `main` that touches `android/**`. That confirms the
module *compiles and packages* correctly; it has **not** been smoke-tested
on a real device or emulator (import photos, switch presets, check
Strength/Grain, export, confirm files land in the gallery) — do that
before relying on it for real use.

## Known follow-ups

- Performance: `core`'s pixel operations are plain per-pixel Kotlin loops
  (no SIMD/GPU). Fine for a phone-camera-resolution JPEG in testing: not
  yet profiled on a real device at 12–48MP; may need chunking, downscaled
  intermediate buffers, or an `Renderscript`/`GPU`-based path if it's too
  slow in practice.
- No app icon/launch splash yet (uses the OS default).
- No instrumented UI tests (Compose UI testing) — only `:core` has
  automated tests today.
