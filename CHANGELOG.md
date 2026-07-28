# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project scaffolding: `src/myphoto` package layout (gui, workflow,
  preset_engine, color_engine + adapters, export_engine, image_loader,
  batch, settings, core), `tests/`, `presets/`.
- Project docs: README, LICENSE (MIT), CONTRIBUTING, Architecture,
  DeveloperGuide.
- Product specification committed at `docs/specs/MYPHOTO_CLAUDE_PROMPT.md`.
- Packaging config: `pyproject.toml`, `requirements.txt`, `.gitignore`.
- `myphoto.core.ImageBuffer`: the internal normalized-float32 image
  representation shared by every pipeline stage, plus `MyPhotoError`,
  `UnsupportedFormatError`, and `ImageDecodeError`.
- `myphoto.image_loader.ImageLoader`: decodes JPEG/PNG/TIFF/BMP via Pillow
  and RAW formats (CR2/CR3/NEF/ARW/RAF/ORF/RW2/DNG/...) via rawpy/LibRaw
  into `ImageBuffer`, preserving source bit depth, ICC profile (raster),
  and best-effort EXIF metadata.
- Unit tests for `core.ImageBuffer` and `image_loader` (format detection,
  8-bit/16-bit decoding, missing/unsupported/corrupt file handling).
