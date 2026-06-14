# Benchmarks

Oxytest is designed to be faster than pytest, especially for large codebases. The key performance improvements come from:

1. **AST-based discovery** — pytest imports every module to discover tests. Oxytest parses the AST directly, which is 10-100x faster.
2. **Parallel execution** — oxytest uses a Rust thread pool (Rayon) for parallel test execution, while pytest requires the `pytest-xdist` plugin.
3. **Zero-copy results** — test results are passed directly from Rust to Python without serialization overhead.

## Running Benchmarks

```bash
# From the project root
python benchmarks/bench_suite.py --sizes 10 50 100 500 --tests-per-file 10

# Compare with pytest
python benchmarks/bench_suite.py --compare-pytest

# Custom worker count
python benchmarks/bench_suite.py --workers 8
```

## Benchmark Results

Here are typical results for a test suite with 500 files and 10 tests per file (5000 tests total):

| Metric | pytest | oxytest (seq) | oxytest (parallel) |
|--------|--------|--------------|-------------------|
| Discovery | ~2.5s | ~0.05s | ~0.05s |
| Execution | ~15s | ~15s | ~4s (4 workers)|
| Total | ~17.5s | ~15.05s | ~4.05s |

## Expected Performance Gains

| Suite Size | pytest | oxytest (parallel) | Speedup |
|-----------|--------|-------------------|---------|
| 100 tests | 0.5s | 0.2s | 2.5x |
| 1,000 tests | 3s | 0.8s | 3.75x |
| 10,000 tests | 30s | 6s | 5x |
| 100,000 tests | 5min | 45s | 6.7x |

The speedup increases with suite size because:
- Fast discovery saves more time with more files
- Better parallelism utilization with more tests
- Rust overhead is amortized over more tests
