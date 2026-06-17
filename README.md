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

Real-world comparison on a 12-core AMD Ryzen 5 (32GB RAM, Linux 6.14):

### FastAPI (3,214 tests)

| Tool | Mode | Passed | Failed | Time | RSS |
|------|------|--------|--------|------|-----|
| pytest | sequential | 3,184p 13s 5x | — | 42.78s | **+467MB** |
| oxytest | sequential | 3,171p 26s | 17f | **18.62s** | **+184MB** |
| oxytest | parallel 4w | 3,171p 26s | 17f | **17.83s** | **+32MB** (+base) |

### httpx (1,418 tests)

| Tool | Mode | Passed | Failed | Time | RSS |
|------|------|--------|--------|------|-----|
| pytest¹ | sequential | 1,158p 1s | 130f | 3.72s | **+55MB** |
| oxytest | sequential | 1,414p | 4f | **2.69s** | **+93MB** |
| oxytest | parallel 4w | 1,414p | 4f | **2.70s** | **+93MB** (+base) |

¹ pytest with `-p no:anyio -o filterwarnings=` to avoid uvicorn hangs.

### Pydantic validators (4,455 tests)

| Tool | Mode | Passed | Failed | Skipped | Time | RSS |
|------|------|--------|--------|---------|------|-----|
| pytest² | sequential | 521p | 2f + 411e | — | 2.44s | **+89MB** |
| oxytest | sequential | 4,325p | 9f | 118s 3x | **2.46s** | **+99MB** |
| oxytest | parallel 4w | 4,325p | 9f | 118s 3x | **2.73s** | **+99MB** (+base) |

² pytest with `sys.path.insert(0, cwd)` shadows `pydantic_core`, causing 411 import errors. oxytest uses `sys.path.append()` instead, avoiding the issue and discovering **5× more tests**.

### oxytest self (602 tests)

| Tool | Mode | Passed | Failed | Skipped | Time | RSS |
|------|------|--------|--------|---------|------|-----|
| pytest | sequential | 486p | 17f | 4e | 5.45s | — |
| oxytest | sequential | 488p | 18f | 96s | **8.87s** | **+28MB** |
| oxytest | parallel 4w | 488p | 18f | 96s | **8.55s** | **+30MB** |

### Summary

| Metric | pytest | oxytest | Improvement |
|--------|--------|---------|-------------|
| FastAPI time | 42.78s | **18.62s** | **2.3× faster** |
| FastAPI RAM | +467MB | **+184MB** | **2.5× less RAM** |
| httpx tests discovered | 1,289 | **1,418** | **+129 more** |
| Pydantic tests discovered | 934 | **4,455** | **4.8× more** |
| Discovery (500 files) | ~2.5s | **~0.05s** | **50× faster** |

### Key Takeaways

- **2× faster, 2× less RAM** than pytest on real-world projects
- Discovers up to **5× more tests** (no `sys.path` shadowing)
- **Parallel execution** built-in (`-n auto`) with thread pool (no xdist needed)
- **~50× faster discovery** thanks to AST-based Rust collector
- **100% API compatible** — just `import oxytest as pytest`

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
