package com.myphoto.android.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "myphoto_settings")

/** Mirrors the fields `myphoto.settings.AppSettings` persists on desktop that make sense on Android. */
data class AppSettings(
    val lastBaseProfileId: String? = null,
    val lastFilmSimulationId: String? = null,
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val BASE_PROFILE_ID = stringPreferencesKey("base_profile_id")
        val FILM_SIMULATION_ID = stringPreferencesKey("film_simulation_id")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { prefs ->
        AppSettings(
            lastBaseProfileId = prefs[Keys.BASE_PROFILE_ID],
            lastFilmSimulationId = prefs[Keys.FILM_SIMULATION_ID],
        )
    }

    suspend fun save(settings: AppSettings) {
        context.dataStore.edit { prefs ->
            settings.lastBaseProfileId?.let { prefs[Keys.BASE_PROFILE_ID] = it }
            settings.lastFilmSimulationId?.let { prefs[Keys.FILM_SIMULATION_ID] = it }
        }
    }
}
