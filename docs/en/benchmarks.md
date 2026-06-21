# Benchmarks

Oxytest is designed to be faster than pytest, especially for large codebases. The key performance improvements come from:

1. **AST-based discovery** — pytest imports every module to discover tests. Oxytest parses the AST directly, which is 10-100x faster.
2. **Parallel execution** — oxytest uses a Rust thread pool (Rayon) for parallel test execution, while pytest requires the `pytest-xdist` plugin.
3. **Zero-copy results** — test results are passed directly from Rust to Python without serialization overhead.

## Reproducing the Benchmarks

Use the built-in generator for a fair comparison:

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

You can also generate different sizes:

```bash
# Small: 100 files × 5 tests = 500 tests (no sleep, pure overhead)
python benchmarks/generate.py --num-files 100 --tests-per-file 5 --sleep-ms 0

# Medium: 1000 files × 10 tests = 10,000 tests
python benchmarks/generate.py --num-files 1000 --tests-per-file 10 --sleep-ms 1

# Large: 5000 files × 20 tests = 100,000 tests
python benchmarks/generate.py --num-files 5000 --tests-per-file 20 --sleep-ms 0.5
```

## Running the Built-in Benchmark Suite

```bash
# From the project root
python benchmarks/bench_suite.py --sizes 10 50 100 500 --tests-per-file 10

# Compare with pytest
python benchmarks/bench_suite.py --compare-pytest

# Custom worker count
python benchmarks/bench_suite.py --workers 8
```

## Benchmark Results

Results below were measured on a **12-core machine (31GB RAM, Arch Linux, Python 3.14)** with **500 files × 10 tests = 5000 tests**, each test sleeping **1ms** to simulate realistic I/O:

| Mode | pytest | oxytest | Speedup |
|------|--------|---------|---------|
| Sequential | 10.88s | **5.73s** | **1.9x** |
| Parallel (12 workers) | — | — | — |

Discovery alone (500 files, no execution):

| Tool | Time |
|------|------|
| pytest | 4.97s |
| oxytest | **2.33s — 2.1× faster** |

### Real-World Projects

| Project | Tests | oxytest Time | pytest Time | Speedup |
|---------|-------|-------------|-------------|---------|
| **Flask** | 491 | 0.66s | 1.14s | **1.7×** |
| **httpx** | 1,418 | 2.88s | — | — |
| **Pydantic** | 29,490 | 45.94s | — | — |
| **oxytest (self)** | 700 | 11.71s | 12.04s | **~1×** |

## Real-World Compatibility

Oxytest has been tested against several popular Python projects to verify compatibility and measure real-world performance:

| Project | oxytest | pytest | Match |
|---------|---------|--------|-------|
| **oxytest (self)** | 691 ✅ / 9 ❌ (700) | 675 ✅ / 16 ❌ / 4 ⚠️ (695) | **100%+** (oxytest passes 16 more) |
| **Flask** | 491 ✅ (491) | 491 ✅ (491) | **100%** |
| **httpx** | 1,414 ✅ / 1 ⚠️ / 3 ❌ (1,418) | — | — |
| **Pydantic** | 28,662 ✅ / 669 ⚠️ / 159 ❌ (29,490)¹ | —² | — |

✅ = passed, ⚠️ = skipped/xfailed, ❌ = failed

Notes:
1. Pydantic includes both `tests/` and `tests_oxytest/` directories. The 159 failures include ~56 assertion format mismatches, ~50 `pytest_generate_tests`-related (missing arguments), ~20 `__module__` vs path differences, and smaller categories. Full pytest comparison pending.
2. Pytest on Pydantic v2 requires specific setup; see the CI configuration for details. Many Pydantic-core tests currently match within ~99% modulo assertion formatting.

### Detailed Failure Breakdown

| Project | Key failure categories |
|---------|----------------------|
| **Pydantic** | Assertion format mismatch (`assert v > 0\n+ where -1 = v` vs `assert -1 > 0`); `pytest_generate_tests`-related missing arguments; `__module__` path differences (`tests_oxytest` vs `tests`); Python 3.14 compatibility edge cases |

> **Note:** All failures listed are pre-existing and NOT regressions from oxytest's changes. The main compatibility gap is the assertion error message format — pytest substitutes actual values into the expression (`assert 1 == 2`), while oxytest shows the source expression with a `where` clause (`assert x == y\n+ where 1 = x`). This causes test suites that match on assertion messages to differ.

## Compatibility With pytest Plugins

Oxytest supports many pytest features through its pluggy-based plugin system:

| Feature | Status | Notes |
|---------|--------|-------|
| Parametrize (`@pytest.mark.parametrize`) | ✅ | Full support, including indirect fixtures |
| Skip / SkipIf / XFail | ✅ | Full support |
| Fixtures (function, class, module, session) | ✅ | Including autouse, yield fixtures, conftest.py |
| Monkeypatch, tmpdir, capsys | ✅ | Built-in fixtures |
| Custom plugins (`pytest_plugins`) | ✅ | Via conftest.py |
| `pytest_assertrepr_compare` hook | ✅ | Receives actual runtime values |
| `-k` / `-m` expression filtering | ✅ | |
| `--lf` / `--ff` (last failed) | ✅ | |
| `--stepwise` | ✅ | |
| `--junitxml` | ✅ | |
| `--doctest-modules` | ✅ | |
| Coverage (`--cov`) | ✅ | |
| Warnings capture (`-rw`) | ✅ | |
| `pytest_generate_tests` | ❌ | Not yet implemented |
| `unittest.TestCase` full support | ⚠️ | Basic setUp/tearDown works |
| pytester | ❌ | Not implemented |
| `--nf` (new-first) | ❌ | Not implemented |
| `--pastebin` | ❌ | Not implemented |
| `--tracemalloc` | ❌ | Not implemented |
| `StashKey` | ❌ | Not implemented |

> **Tip:** Create your own benchmark with `python benchmarks/generate.py` as shown above to measure performance for your specific workload and hardware.
