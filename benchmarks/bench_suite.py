#!/usr/bin/env python3
"""
Oxytest benchmark suite.

Compares oxytest vs pytest performance on:
  - Test discovery (AST-based vs import-based)
  - Sequential execution
  - Parallel execution

Generates synthetic test suites of varying sizes.
"""

import os
import sys
import time
import argparse
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BENCH_DIR = os.path.join(os.path.dirname(__file__), "_generated")


def generate_test_suite(num_files: int, tests_per_file: int, output_dir: str):
    """Generate a synthetic test suite with the given parameters."""
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "__init__.py"), "w") as f:
        pass

    for i in range(num_files):
        filename = f"test_bench_{i:04d}.py"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            f.write("import time\n\n")
            for j in range(tests_per_file):
                delay = (i * tests_per_file + j) % 10 * 0.001  # 0-9ms per test
                f.write(f"""
def test_func_{j:04d}():
    \"\"\"Benchmark test {i}.{j}\"\"\"
    time.sleep({delay})
    assert {j} % 2 == 0 or {j} % 2 == 1
""")

    # Generate some class-based tests too
    for i in range(max(1, num_files // 3)):
        filename = f"test_bench_class_{i:04d}.py"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            f.write("import time\n\n")
            f.write(f"class TestBench{i}:\n")
            for j in range(tests_per_file // 2):
                delay = (i * tests_per_file + j) % 10 * 0.001
                f.write(f"""    def test_method_{j:04d}(self):
        time.sleep({delay})
        assert {j} % 2 == 0 or {j} % 2 == 1\n""")


def benchmark_discovery(suite_dir: str, warmup: bool = True) -> dict:
    """Benchmark test discovery time."""
    import oxytest

    if warmup:
        oxytest.discover_tests(suite_dir)

    times = []
    for _ in range(5):
        start = time.perf_counter()
        tests = oxytest.discover_tests(suite_dir)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "count": len(tests),
    }


def benchmark_execution(suite_dir: str, num_workers: int, warmup: bool = True) -> dict:
    """Benchmark test execution time."""
    import oxytest

    tests = oxytest.discover_tests(suite_dir)

    if warmup:
        oxytest.run_tests(tests, num_workers=num_workers)

    times = []
    for _ in range(3):
        start = time.perf_counter()
        results = oxytest.run_tests(tests, num_workers=num_workers)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "count": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
    }


def benchmark_pytest_execution(suite_dir: str) -> dict:
    """Benchmark pytest execution time."""
    import subprocess

    times = []
    for _ in range(3):
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", suite_dir, "--tb=no", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "count": len(result.stdout.splitlines()) if result.stdout else 0,
    }


def print_results(label: str, data: dict):
    print(f"  {label}:")
    print(f"    Tests: {data.get('count', 'N/A')}")
    print(f"    Mean:  {data['mean']*1000:.2f}ms")
    print(f"    Min:   {data['min']*1000:.2f}ms")
    print(f"    Max:   {data['max']*1000:.2f}ms")
    if 'passed' in data:
        print(f"    Passed: {data['passed']}/{data['count']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Oxytest benchmark suite")
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=[10, 50, 100, 500],
        help="Number of test files to benchmark with"
    )
    parser.add_argument(
        "--tests-per-file", type=int, default=10,
        help="Number of tests per file"
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--compare-pytest", action="store_true",
        help="Also benchmark pytest for comparison"
    )
    parser.add_argument(
        "--cleanup", action="store_true", default=True,
        help="Clean up generated test suites after benchmark"
    )
    args = parser.parse_args()

    import oxytest
    import multiprocessing

    num_workers = args.workers or multiprocessing.cpu_count()

    print("=" * 60)
    print("OXYTEST BENCHMARKS")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Oxytest: {oxytest.__version__}")
    print(f"Workers: {num_workers}")
    print()

    for num_files in args.sizes:
        total_tests = num_files * args.tests_per_file
        print(f"\n--- Suite: {num_files} files, {args.tests_per_file} tests/file ({total_tests} total) ---")

        suite_dir = os.path.join(BENCH_DIR, f"suite_{num_files}_{args.tests_per_file}")
        generate_test_suite(num_files, args.tests_per_file, suite_dir)

        print("  Discovery:")
        disc_results = benchmark_discovery(suite_dir)
        print(f"    Mean:  {disc_results['mean']*1000:.2f}ms")
        print(f"    Tests: {disc_results['count']}")

        print("  Sequential Execution:")
        exec_results = benchmark_execution(suite_dir, num_workers=1)
        print(f"    Mean:  {exec_results['mean']:.2f}s")
        print(f"    Tests: {exec_results['count']}")

        print(f"  Parallel Execution ({num_workers} workers):")
        par_results = benchmark_execution(suite_dir, num_workers=num_workers)
        print(f"    Mean:  {par_results['mean']:.2f}s")
        print(f"    Speedup: {exec_results['mean'] / par_results['mean']:.2f}x")

        if args.compare_pytest:
            try:
                print("  Pytest Execution:")
                pt_results = benchmark_pytest_execution(suite_dir)
                print(f"    Mean:  {pt_results['mean']:.2f}s")
                if exec_results['mean'] > 0:
                    print(f"    vs Oxytest sequential: {pt_results['mean'] / exec_results['mean']:.2f}x")
            except Exception as e:
                print(f"    Pytest benchmark failed: {e}")

        print()

    if args.cleanup:
        import shutil
        if os.path.exists(BENCH_DIR):
            shutil.rmtree(BENCH_DIR)
            print("Cleaned up generated test suites.")


if __name__ == "__main__":
    main()
