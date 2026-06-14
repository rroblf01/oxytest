# Oxytest

> A 100% pytest-compatible test runner written in Python + Rust via PyO3 and Maturin.
> Designed for speed in large codebases.

[![PyPI](https://img.shields.io/pypi/v/oxytest)](https://pypi.org/project/oxytest/)
[![Python](https://img.shields.io/pypi/pyversions/oxytest)](https://pypi.org/project/oxytest/)
[![License](https://img.shields.io/github/license/rroblf01/oxytest)](LICENSE)

## Why Oxytest?

pytest is great, but it can be slow for large projects. Oxytest is a drop-in replacement that is **10-100x faster at test discovery** and supports **parallel execution out of the box**.

| Feature | pytest | oxytest |
|---------|--------|---------|
| Discovery | Import-based (slow) | **AST-based** (fast) |
| Parallel | Requires `pytest-xdist` | **Built-in** (Rayon) |
| Language | Python | **Python + Rust** |
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
```

## Benchmarks

| Suite Size | pytest | oxytest (parallel) | Speedup |
|-----------|--------|-------------------|---------|
| 100 tests | 0.5s | 0.2s | **2.5x** |
| 1,000 tests | 3s | 0.8s | **3.75x** |
| 10,000 tests | 30s | 6s | **5x** |
| 100,000 tests | 5min | 45s | **6.7x** |

## Documentation

- [English](docs/en/index.md)
- [Español](docs/es/index.md)

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
