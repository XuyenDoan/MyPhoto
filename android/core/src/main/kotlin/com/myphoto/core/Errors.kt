package com.myphoto.core

class PresetNotFoundException(presetId: String) : NoSuchElementException("Preset not found: $presetId")

class PresetValidationException(sourceName: String, reason: String) :
    IllegalArgumentException("Invalid preset $sourceName: $reason")
