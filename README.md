# Oxytest

> A 100% pytest-compatible test runner written in Python + Rust via PyO3 and Maturin.
> Designed for speed in large codebases.

[![PyPI](https://img.shields.io/pypi/v/oxytest?cacheSeconds=300)](https://pypi.org/project/oxytest/)
[![Python](https://img.shields.io/pypi/pyversions/oxytest?cacheSeconds=300)](https://pypi.org/project/oxytest/)
[![License](https://img.shields.io/github/license/rroblf01/oxytest)](https://github.com/rroblf01/oxytest/blob/main/LICENSE)

## Why Oxytest?

pytest is great, but it can be slow for large projects. Oxytest is a drop-in replacement that is **10-100x faster at test discovery** and supports **parallel execution out of the box**.

| Feature | pytest | oxytest |
|---------|--------|---------|
| Discovery | Import-based (slow) | **AST-based** (fast) |
| Parallel | Requires `pytest-xdist` | **Built-in** (Rayon) |
| Language | Python | **Python + Rust** |
| Assert rewriting | Built-in | **Built-in** (comparison diffs) |
| Plugin system | Built-in | **Built-in** (pluggy) |
| Drop-in compatible | — | **100%** |

## Quick Start

```bash
# Install
pip install oxytest

# Run tests (no changes needed!)
oxytest

# Use as pytest replacement
python -c "import oxytest as pytest; pytest.main()"
```

## Usage

```bash
# Run all tests in current directory
oxytest

# Run with parallel execution (auto-detect CPU count)
oxytest -n auto

# Verbose output
oxytest -v

# Stop on first failure
oxytest -x

# Filter by keyword
oxytest -k "user or math"

# Show local variables on failure
oxytest --showlocals

# Trace fixture setup/teardown
oxytest --setup-show

# Run only previously failed tests
oxytest --lf

# Show slowest tests
oxytest --durations 5

# Full summary
oxytest -rA

# Migrate imports from pytest to oxytest
oxytest migrate src/ --dry-run
```

## Python API

```python
import oxytest as pytest

# All standard pytest API is available
pytest.main(["-v", "tests/"])

assert 0.1 + 0.2 == pytest.approx(0.3)

with pytest.raises(ValueError):
    int("not a number")

@pytest.fixture
def data():
    return {"key": "value"}

@pytest.mark.parametrize("x,expected", [(1, 2), (3, 6)])
def test_double(x, expected):
    assert x * 2 == expected

# Plugin API
from oxytest import hookimpl
@hookimpl
def pytest_addoption(parser):
    parser.addoption("--my-flag", action="store_true")
```

## Benchmarks

Reproduce with the built-in generator for a fair comparison (sequential only, no `-n` flag):

```bash
# Generate 500 files with 10 tests each, 1ms sleep per test
python benchmarks/generate.py --num-files 500 --tests-per-file 10 --sleep-ms 1

# Sequential comparison (fair: no -n flag for either)
time python -m oxytest benchmark_tests/ --tb=no -q
time python -m pytest benchmark_tests/ --tb=no -q

# Parallel comparison
time python -m oxytest benchmark_tests/ --tb=no -q -n auto
time python -m pytest benchmark_tests/ --tb=no -q -n auto   # requires pytest-xdist
```

Results for 5000 tests with 1ms sleep each:

| Mode | pytest | oxytest | Speedup |
|------|--------|---------|---------|
| Sequential | 11.45s | **5.85s** | **2.0x** |
| Parallel (8 workers) | — | **0.57s** | **20x** |

Discovery alone (500 files, no sleep):

| Tool | Time |
|------|------|
| pytest | ~2.5s |
| oxytest | **~0.05s** |

## Documentation

- [English](https://github.com/rroblf01/oxytest/blob/main/docs/en/index.md)
- [Español](https://github.com/rroblf01/oxytest/blob/main/docs/es/index.md)

## Development

```bash
# Clone
git clone https://github.com/rroblf01/oxytest
cd oxytest

# Install dependencies
uv sync

# Build the Rust extension
uv pip install -e .

# Run tests
oxytest tests/
```

## License

MIT
