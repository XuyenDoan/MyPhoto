// Deliberately empty: :core and :app each declare their own plugins, with
// their own explicit versions, in their own build.gradle.kts.
//
// An earlier version of this file declared `kotlin("jvm") ... apply false`
// here so :core's plugin could be reused without a version in :app too.
// That caused CI to fail applying org.jetbrains.kotlin.android:
// "Could not generate a decorated class for type KotlinAndroidTarget >
// com/android/build/gradle/api/BaseVariant" — sharing one Kotlin Gradle
// Plugin classpath entry across a module that never applies the Android
// Gradle Plugin (:core) and one that does (:app) put the Kotlin plugin's
// classes in a state where they couldn't see AGP's classes. Giving every
// module its own fully-versioned `plugins {}` block avoids that entirely.
//
// This also means `:core` never touches the Android Gradle Plugin at all
// — useful in sandboxes without access to dl.google.com/maven.google.com
// (this project's original CI attempt hit exactly that). See
// android/README.md.
