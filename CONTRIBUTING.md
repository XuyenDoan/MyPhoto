# Contributing to MyPhoto

Thanks for your interest in MyPhoto. This project intentionally stays small
in scope — see the [product spec](docs/specs/MYPHOTO_CLAUDE_PROMPT.md) before
proposing a feature that isn't film simulation, preview, or export related.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
```

See [`docs/DeveloperGuide.md`](docs/DeveloperGuide.md) for the full guide.

## Workflow

1. Open an issue describing the change before starting non-trivial work.
2. Create a branch off `main`: `feat/...`, `fix/...`, `docs/...`, `chore/...`.
3. Keep commits small and use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add Classic Chrome film simulation preset`
   - `fix: correct white balance adapter rounding`
   - `docs: update architecture diagram`
   - `test: add preset engine JSON schema tests`
   - `refactor`, `chore`, `perf`, `build`, `ci` as appropriate.
4. Run linting, type checking, and tests before opening a PR:
   ```bash
   ruff check .
   mypy src
   pytest --cov
   ```
5. Open a PR against `main` describing the change and referencing the issue.

## Code standards

- Clean Architecture, SOLID, DRY, KISS.
- Type hints and docstrings on all public APIs.
- PEP 8 style, enforced by `ruff`.
- Prefer real implementations over placeholders; if something must be
  stubbed, say so explicitly and track it in `CHANGELOG.md`.
- Third-party color libraries (LibRaw/rawpy, OpenColorIO, LittleCMS,
  OpenImageIO, OpenCV) are wrapped behind adapters in
  `src/myphoto/color_engine/adapters/` — application code depends on the
  adapter interface, not the library directly.

## Reporting issues

Please include: OS/Windows version, Python version, MyPhoto version, the
image format/camera involved, and steps to reproduce.
