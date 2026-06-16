# Changelog

## [2.0.0] - 2026-06-16

### Added
- **Coverage support**: `--cov[=SOURCE]`, `--cov-report`, `--cov-config`, `--cov-branch`, `--cov-fail-under`, `--cov-append`. Coverage.py is an optional dependency (`pip install oxytest[cov]`). Also documented `coverage run -m oxytest` for zero-config usage.
- **VSCode compatibility**: Built-in `_vscode.py` plugin that implements the JSON-RPC 2.0 protocol over named pipes. Activated automatically when VSCode runs `-p vscode_pytest`. Supports test discovery (tree with folder/file/class/test nodes) and real-time execution results.
- **Boolean keyword expressions**: `-k "not slow and (test_user or test_api)"` now works with `and`, `or`, `not`, and parentheses. Evaluates against test name and markers.
- **pyproject.toml configuration**: oxytest reads `[tool.oxytest]` section for `addopts`, `testpaths`, `ignore`, and `markers`. CLI flags take precedence.
- **`--pdb` / `--trace`**: Drop into the debugger on test failure (`--pdb`) or before each test (`--trace`).
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
- **Rust optimizations**: Parallel test file discovery (Rayon par_iter), reusable global thread pool, reduced TestItem cloning in runner, lazy file filtering in walkdir.
- **Rust tests**: 22 unit tests across types.rs, discovery.rs, runner.rs.
- **Rust benchmarks**: criterion benchmarks for TestItem/TestResult creation, cloning, grouping, and is_test_file.
- **Python test suite**: expanded from 347 to 432 tests (+85), raising coverage from 62% to 80%.

### Fixed
- Walkdir root filtering bug (`e.depth() == 0` guard).
- `ApproxDecimal.__eq__` implementation.
- `Cargo.lock` gitignored.
- Test commands: `python -m` instead of `uv run` for Windows compatibility.
- Windows glob in CI: uses explicit `--ignore` instead of shell glob.
- `_CaptureFixture.readouterr()` now returns an object with `.out`/`.err` attributes (also supports tuple unpacking for backward compatibility).
- `_fixture_capsys` auto-starts on fixture resolution (was requiring manual `.start()` call).
- `MonkeyPatch.setattr` saves after successful `setattr`, not before (prevents stale undo records on failure).
- `register_from_module` unwraps bound methods from `__wrapped__` before setting `_oxytest_fixture`.
- `_filter_keyword_expression` handles missing/None file paths gracefully.
- `_write_junitxml` now includes all test results (not only failures/skips).
- `hookspec()` no longer passes unsupported kwargs to HookspecMarker.
- `PluginManager.register()` now tracks plugins in `_plugins` list.
- `migrate()` returns exit code 1 when changes are made (not only in `--check` mode).
- `_build_test_tree` in `_vscode.py` correctly assigns class name (`parts[0]`) instead of method name.
- `--coverage` documented as `--cov` in migration docs (inaccurate reference).

### Changed
- Version bumped from `1.0.0` → `2.0.0`.
- `pyproject.toml`: Development Status → Production/Stable. Added `Typing :: Typed` classifier.
- CI: docs deploy chains after publish via `workflow_run`.
- `uv pip install --system` (no venv) for test jobs.
- Rust runner uses global Rayon thread pool instead of creating a new pool per `run_tests` call.
- Rust discovery now processes test files in parallel using Rayon.
- `.gitignore` updated to exclude coverage artifacts (`.coverage`, `htmlcov/`, `coverage/`).

### Removed
- `UV_PYTHON_PREFERENCE` env var from CI.
