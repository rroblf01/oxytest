#!/usr/bin/env python3
"""
Generate a large synthetic test suite for benchmarking oxytest vs pytest.

Usage:
    # Generate 1000 files with 10 tests each (default)
    python benchmarks/generate.py

    # Generate 5000 files with 20 tests each
    python benchmarks/generate.py --num-files 5000 --tests-per-file 20

    # Benchmark: oxytest vs pytest (fair comparison)
    time python -m oxytest benchmark_tests/ --tb=no -q          # oxytest sequential
    time python -m pytest benchmark_tests/ --tb=no -q            # pytest (no xdist)
    time python -m oxytest benchmark_tests/ --tb=no -q -n auto   # oxytest parallel
    time python -m pytest benchmark_tests/ --tb=no -q -n auto    # pytest + xdist

    # Clean up
    python benchmarks/generate.py --cleanup
"""

import os
import sys
import random
import argparse
import time

DEFAULT_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmark_tests")


def make_asserts(rng: random.Random, n: int = 3) -> list[str]:
    """Generate random assertion statements."""
    opts = []
    a, b = rng.randint(1, 100), rng.randint(1, 100)
    opts.append(f"assert {a} + {b} == {a + b}")
    opts.append(f"assert {a} * {b} == {a * b}")
    opts.append(f"assert abs({a - b}) >= 0")
    s = f"\"hello{rng.randint(0, 999)}\""
    opts.append(f"assert len({s}) > 0")
    x = rng.randint(1, 50)
    opts.append(f"assert {x} in list(range({x + 10}))")
    vals = [rng.randint(1, 100) for _ in range(5)]
    opts.append(f"assert sorted([{','.join(map(str, vals))}]) == [{','.join(map(str, sorted(vals)))}]")
    k, v = rng.choice(["a", "b", "c", "x", "y"]), rng.randint(0, 100)
    opts.append(f"assert dict({k}={v}).get('{k}') == {v}")
    opts.append(f"assert str({a} + {b}) == '{a + b}'")
    opts.append(f"assert isinstance({a}, int)")
    a2 = rng.randint(1, 20)
    opts.append(f"assert pow({a2}, 2) == {a2 * a2}")
    return opts[:n]


def generate_suite(
    num_files: int,
    tests_per_file: int,
    output_dir: str,
    sleep_ms: float,
    seed: int,
    class_ratio: float,
):
    """Generate a synthetic test suite."""
    rng = random.Random(seed)
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "__init__.py"), "w"):
        pass

    total_func = 0
    total_class = 0
    total_param = 0

    for i in range(num_files):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"  Generating file {i + 1}/{num_files}...", end="\r", file=sys.stderr)
            sys.stderr.flush()

        is_class = rng.random() < class_ratio
        filename = f"test_bench_{i:04d}.py"
        filepath = os.path.join(output_dir, filename)
        lines: list[str] = []

        if is_class:
            lines.append("import time\n")
            lines.append(f"\n\nclass TestBench{i}:\n")
            for j in range(tests_per_file):
                delay = round(sleep_ms / 1000, 6)
                asserts = make_asserts(rng, n=rng.randint(1, 3))
                body = "\n".join(f"        {a}" for a in asserts)
                lines.append(f"""
    def test_{i}_{j:04d}(self):
        time.sleep({delay})
{body}
""")
            total_class += tests_per_file
        else:
            lines.append("import time\n")
            for j in range(tests_per_file):
                delay = round(sleep_ms / 1000, 6)
                asserts = make_asserts(rng, n=rng.randint(1, 3))
                body = "\n".join(f"    {a}" for a in asserts)
                lines.append(f"""
def test_{i}_{j:04d}():
    time.sleep({delay})
{body}
""")
            total_func += tests_per_file

        with open(filepath, "w") as f:
            f.writelines(lines)

    print(f"  Generated {num_files} file(s), ", end="", file=sys.stderr)
    total = total_func + total_class + total_param
    print(f"{total} test(s) total", file=sys.stderr)
    if total_func:
        print(f"    Function tests: {total_func}", file=sys.stderr)
    if total_class:
        print(f"    Class tests:    {total_class}", file=sys.stderr)
    if total_param:
        print(f"    Parametrize:    {total_param}", file=sys.stderr)

    return total


def cleanup(output_dir: str):
    import shutil
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
        print(f"Removed {output_dir}")
    else:
        print(f"Nothing to clean up at {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic test suite for benchmarking")
    parser.add_argument("--num-files", type=int, default=1000, help="Number of test files (default: 1000)")
    parser.add_argument("--tests-per-file", type=int, default=10, help="Tests per file (default: 10)")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT, help=f"Output directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--sleep-ms", type=float, default=0.5, help="Time.sleep(ms) per test (default: 0.5)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--class-ratio", type=float, default=0.3, help="Ratio of class-based tests (default: 0.3)")
    parser.add_argument("--cleanup", action="store_true", help="Remove generated directory and exit")
    args = parser.parse_args()

    if args.cleanup:
        cleanup(args.output_dir)
        return

    print("=" * 60)
    print("OXYTEST BENCHMARK SUITE GENERATOR")
    print("=" * 60)
    print(f"  Files:        {args.num_files}")
    print(f"  Tests/file:   {args.tests_per_file}")
    print(f"  Total:        {args.num_files * args.tests_per_file}")
    print(f"  Sleep:        {args.sleep_ms}ms per test")
    print(f"  Class ratio:  {args.class_ratio}")
    print(f"  Output:       {args.output_dir}")
    print(f"  Seed:         {args.seed}")
    print()

    start = time.time()
    total = generate_suite(
        num_files=args.num_files,
        tests_per_file=args.tests_per_file,
        output_dir=args.output_dir,
        sleep_ms=args.sleep_ms,
        seed=args.seed,
        class_ratio=args.class_ratio,
    )
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.2f}s — {total} test(s) generated in {args.output_dir}")
    print()
    print("Fair benchmark commands:")
    print()
    print("  # 1) Sequential: oxytest vs pytest (no parallel)")
    print(f"    time python -m oxytest {args.output_dir} --tb=no -q")
    print(f"    time python -m pytest {args.output_dir} --tb=no -q")
    print()
    print("  # 2) Parallel: oxytest -n auto vs pytest -n auto (requires pytest-xdist)")
    print(f"    time python -m oxytest {args.output_dir} --tb=no -q -n auto")
    print(f"    time python -m pytest {args.output_dir} --tb=no -q -n auto")
    print()
    print("  # To clean up:")
    print(f"    python {__file__} --cleanup")


if __name__ == "__main__":
    main()
