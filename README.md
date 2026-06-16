# Oxytest

> A 100% pytest-compatible test runner written in Python + Rust via PyO3 and Maturin.
> Designed for speed in large codebases.

[![PyPI](https://img.shields.io/pypi/v/oxytest?cacheSeconds=300)](https://pypi.org/project/oxytest/)
[![Python](https://img.shields.io/pypi/pyversions/oxytest?cacheSeconds=300)](https://pypi.org/project/oxytest/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/rroblf01/oxytest/blob/main/LICENSE)

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

# Filter with keyword expressions
oxytest -k "not slow and (math or user)"

# Show slowest tests
oxytest --durations 5

# Full summary
oxytest -rA

# Measure coverage
oxytest --cov=src/ --cov-report=html

# Drop into debugger on failure
oxytest --pdb

# Trace execution (pdb on every test)
oxytest --trace

# Configure via pyproject.toml
cat pyproject.toml
# [tool.oxytest]
# addopts = "-v --tb=short"
# testpaths = ["tests/"]

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

## Coverage

oxytest integrates with [coverage.py](https://coverage.readthedocs.io/) for code coverage measurement.

### Zero-config approach

```bash
pip install coverage
coverage run --source=. -m oxytest
coverage report -m
coverage html  # open htmlcov/index.html
```

### Built-in `--cov` flag

```bash
pip install oxytest[cov]   # or: pip install coverage

oxytest --cov=src/                  # terminal report
oxytest --cov=src/ --cov-report=html  # HTML report
oxytest --cov=src/ --cov-branch      # branch coverage
oxytest --cov=src/ --cov-fail-under=80  # enforce min coverage
```

Flags: `--cov[=SOURCE]`, `--cov-report=term|html|xml`, `--cov-config=FILE`, `--cov-branch`, `--cov-fail-under=N`, `--cov-append`.

## VSCode Compatibility

oxytest includes a built-in plugin that speaks the VSCode Python extension's test protocol via JSON-RPC 2.0. When VSCode runs `-p vscode_pytest`, oxytest auto-loads its own implementation — no extra dependencies needed.

**Supported features:**
- Test discovery (tree with folder/file/class/test nodes)
- Real-time execution results (pass/fail/skip/error)
- Per-test tracebacks and messages
- Parametrized test support
- Coverage integration (if `COVERAGE_ENABLED=True`)

No configuration needed — just set `"python.testing.pytestEnabled": true` in VSCode and install oxytest in your environment.

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
