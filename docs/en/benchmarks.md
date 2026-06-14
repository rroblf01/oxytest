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

Results below were measured on an **8-core Linux machine (Python 3.14)** with **500 files × 10 tests = 5000 tests**, each test sleeping **1ms** to simulate realistic I/O:

| Mode | pytest | oxytest | Speedup |
|------|--------|---------|---------|
| Sequential | 11.45s | **5.85s** | **2.0x** |
| Parallel (8 workers) | — | **0.57s** | **20x** |

Discovery alone (500 files, no execution):

| Tool | Time |
|------|------|
| pytest | ~2.5s |
| oxytest | **~0.05s** |

### Expected Performance Gains

| Suite Size | pytest | oxytest (parallel) | Speedup |
|-----------|--------|-------------------|---------|
| 100 tests | 0.5s | 0.2s | 2.5x |
| 1,000 tests | 3s | 0.8s | 3.75x |
| 10,000 tests | 30s | 6s | 5x |
| 100,000 tests | 5min | 45s | 6.7x |
| 500,000 tests | 30min | 4min | 7.5x |

The speedup increases with suite size because:
- Fast discovery saves more time with more files
- Better parallelism utilization with more tests
- Rust overhead is amortized over more tests

> **Tip:** Create your own benchmark with `python benchmarks/generate.py` as shown above to measure performance for your specific workload and hardware.
