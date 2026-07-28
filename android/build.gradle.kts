// Deliberately declares only the plugins :core needs (resolved from Maven
// Central). :app declares its own (Android Gradle Plugin, Kotlin Android,
// Compose compiler) directly in app/build.gradle.kts, with explicit
// versions, so that a root-level `plugins {}` entry for them never forces
// Gradle to resolve the Android Gradle Plugin just to build :core.
//
// That split matters here specifically: this sandbox's outbound proxy
// blocks dl.google.com / maven.google.com (verified: 403 on CONNECT), so
// the Android Gradle Plugin and Android SDK components cannot be fetched
// in this environment — only :core was actually built and tested here.
// Open this project in Android Studio (or any machine with normal internet
// access) to build and run :app. See docs/Architecture.md and
// android/README.md.
plugins {
    kotlin("jvm") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "2.0.21" apply false
}
