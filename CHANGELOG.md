# Changelog

## [1.0.0] - 2026-06-14

### Added
- **Phase 1 - Bug fixes**: `-n auto`, `--tb=value` parsing, yield fixture teardown, `autouse=True`, `usefixtures` on classes, `capsys.stop()` on cleanup.
- **Phase 2 - Plugin system**: pluggy-based plugin system with `hookimpl`/`hookspec`, `Config`, `Parser`, `PluginManager`, conftest plugin loading, entry point plugins (`pytest11`), `-p PLUGIN` flag.
- **Phase 3 - Core features**:
  - `--ignore`, `--collect-only`/`--co`, `--durations`, `-r`, `--showlocals`, `--strict-markers`, `--rootdir`, `--fixtures`, `--markers`, `--setup-show`, `--cache-clear`, `--lf`/`--last-failed`, `--ff`/`--failed-first`.
  - Assert rewriting with comparison diffs.
  - JUnit XML: `<system-out>`, `<system-err>`, `timestamp`.
  - `--setup-show`: fixture setup/teardown tracing.
  - `--showlocals`: local variable display on failure.
  - Cache system with `.pytest_cache/oxytest/lastfailed`.
  - `-rA` now lists individual test names.
- **Migration tool**: `oxytest migrate [PATH]` with `--dry-run`, `--check`, `--reverse`. Handles multi-module imports, aliases, comments.
- **CI**: Windows + macOS matrix (3.11, 3.13, 3.14). Linux matrix (3.10–3.14). Lint job with ruff + ty.
- **Docs**: Complete English and Spanish documentation on mkdocs.

### Fixed
- Walkdir root filtering bug (`e.depth() == 0` guard).
- `ApproxDecimal.__eq__` implementation.
- `Cargo.lock` gitignored.
- Test commands: `python -m` instead of `uv run` for Windows compatibility.
- Windows glob in CI: uses explicit `--ignore` instead of shell glob.

### Changed
- Version bumped from `0.1.0` → `1.0.0`.
- `pyproject.toml`: Development Status → Production/Stable. Added `Typing :: Typed` classifier.
- CI: docs deploy chains after publish via `workflow_run`.
- `uv pip install --system` (no venv) for test jobs.

### Removed
- `UV_PYTHON_PREFERENCE` env var from CI.
