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

## Project Status

Oxytest is in active development. The MVP is functional with:

- ✅ Test discovery (AST-based)
- ✅ Test execution (sequential and parallel)
- ✅ pytest-compatible API (`main`, `approx`, `raises`, `fixture`, `mark`, etc.)
- ✅ CLI with common flags (`-v`, `-x`, `-k`, `--tb`, `-n`, etc.)
- ✅ JUnit XML output
- ✅ Fixtures (`tmp_path`, `capsys`, `monkeypatch` + `conftest.py`)
- ❌ Plugins (coming soon)
