plugins {
    id("com.android.application") version "8.5.2"
    // No explicit version here: root build.gradle.kts's `kotlin("jvm")
    // ... apply false` already resolves the Kotlin Gradle Plugin jar
    // (which also bundles the .android plugin ID) onto the shared
    // classpath at 2.0.21 — redeclaring a version here conflicts with
    // that ("already on the classpath with an unknown version, so
    // compatibility cannot be checked").
    id("org.jetbrains.kotlin.android")
    // Unlike .android, the Compose compiler plugin is NOT bundled into
    // that same jar/classpath entry, so it does need its own version.
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21"
}

android {
    namespace = "com.myphoto.android"
    // 34 (Android 14), not 35: AGP 8.5.2 + Kotlin 2.0.21 hit a plugin-apply
    // failure against compileSdk 35 in CI ("Could not generate a decorated
    // class for type KotlinAndroidTarget > com/android/build/gradle/api/
    // BaseVariant") — a known rough edge in early AGP 8.5.x support for
    // API 35. 34 is unambiguously supported by this AGP/Kotlin pairing.
    // Bump back to 35 once on a newer AGP (8.6+) in Android Studio.
    compileSdk = 34

    defaultConfig {
        applicationId = "com.myphoto.android"
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }
}

// Presets are the single source of truth at repo-root presets/, shared with
// the desktop app (see docs/Architecture.md). Copy them into assets/ at
// build time rather than duplicating the JSON files in this module.
tasks.register<Copy>("copyPresets") {
    from(rootProject.file("../presets"))
    into("src/main/assets/presets")
}

tasks.named("preBuild") {
    dependsOn("copyPresets")
}

dependencies {
    implementation(project(":core"))

    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.core:core-ktx:1.13.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
}

// NOTE: all code in this module touches android.* APIs (Bitmap, MediaStore,
// Compose, ...), so it can't be unit-tested on a plain JVM the way :core is.
// A real device/emulator or Robolectric (itself needing network access this
// sandbox doesn't have to Android's platform jars) is required — see
// android/README.md.
