# Oxytest

**Oxytest** is a 100% pytest-compatible test runner written in Python and Rust via PyO3 and Maturin. It is designed to be faster than pytest for large codebases by leveraging:

- **AST-based test discovery** — finds tests without importing modules (10-100x faster discovery)
- **Parallel execution** — runs tests concurrently using a Rust thread pool (Rayon)
- **Same-process execution** — minimal overhead, no subprocess spawn

## Why Oxytest?

If you have a large test suite and pytest is becoming slow, oxytest offers:

| Feature | Oxytest | pytest |
|---------|---------|--------|
| Discovery method | AST (no imports) | Import-based |
| Parallel execution | Built-in (Rayon) | Via `pytest-xdist` plugin |
| Language | Python + Rust | Python |
| Compatibility | 100% API compatible | — |

## Quick Start

```bash
# Install oxytest
pip install oxytest

# Run your existing tests (no changes needed!)
oxytest

# Or use as pytest drop-in
python -c "import oxytest as pytest; pytest.main()"
```

## Features

- ✅ AST-based test discovery (10-100x faster than pytest)
- ✅ Sequential and parallel execution (built-in Rayon thread pool)
- ✅ pytest-compatible API (`main`, `approx`, `raises`, `fixture`, `mark`, etc.)
- ✅ Fixtures (`tmp_path`, `capsys`, `monkeypatch`, `capfd` + `conftest.py`)
- ✅ Yield fixtures with automatic teardown
- ✅ `autouse=True` fixtures
- ✅ `usefixtures` marker on classes
- ✅ JUnit XML output with `<system-out>`, `<system-err>`, `timestamp`
- ✅ Assert rewriting with comparison diffs
- ✅ `--showlocals` — show local variables on failure
- ✅ `--setup-show` — trace fixture setup/teardown
- ✅ Plugin system (pluggy-based, supports `pytest_addoption`, `pytest_configure`, conftest plugins, entry point plugins)
- ✅ Migration tool (`oxytest migrate`) — automatic import migration between pytest and oxytest
- ✅ Cache system (`--lf`/`--last-failed`, `--ff`/`--failed-first`, `--cache-clear`)
- ✅ Keyword expressions (`-k "not slow and (math or api)"`)
- ✅ Built-in coverage (`--cov`, `--cov-report`, `--cov-branch`, `--cov-fail-under`)
- ✅ Post-mortem debugger (`--pdb`) and trace execution (`--trace`)
- ✅ VSCode integration (JSON-RPC 2.0 over named pipe, auto-detected)
- ✅ `pyproject.toml` configuration (`[tool.oxytest]` section)
- ✅ CLI: `-v`, `-q`, `-x`, `-k`, `--tb`, `-n`, `--junitxml`, `-s`, `--maxfail`, `--ignore`, `--collect-only`, `--durations`, `-r`, `--showlocals`, `--strict-markers`, `--rootdir`, `--fixtures`, `--markers`, `--setup-show`, `--cache-clear`, `--lf`, `--ff`, `-p`, `--cov`, `--cov-report`, `--cov-branch`, `--cov-fail-under`, `--cov-append`, `--pdb`, `--trace`
