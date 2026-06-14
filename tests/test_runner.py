import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest


def get_sample_tests():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    return oxytest.discover_tests(sample_dir)


def test_runner_sequential():
    tests = get_sample_tests()
    results = oxytest.run_tests_sequential(tests)
    assert len(results) == len(tests)
    for r in results:
        assert hasattr(r, "passed")
        assert hasattr(r, "duration_ms")
        assert isinstance(r.duration_ms, int)


def test_runner_parallel():
    tests = get_sample_tests()
    results = oxytest.run_tests(tests, num_workers=4)
    assert len(results) == len(tests)
    for r in results:
        assert hasattr(r, "passed")


def test_runner_results_ordering():
    tests = get_sample_tests()
    results = oxytest.run_tests_sequential(tests)
    for i in range(len(results) - 1):
        r1 = results[i]
        r2 = results[i + 1]
        if r1.test.path == r2.test.path:
            assert r1.test.line_no <= r2.test.line_no


def test_runner_passing_tests():
    tests = get_sample_tests()
    results = oxytest.run_tests_sequential(tests)
    passing = [r for r in results if r.passed]
    assert len(passing) > 0


def test_runner_parallel_consistency():
    tests = get_sample_tests()
    seq_results = oxytest.run_tests_sequential(tests)
    par_results = oxytest.run_tests(tests, num_workers=4)
    assert len(seq_results) == len(par_results)
    for sr, pr in zip(seq_results, par_results):
        assert sr.test.name == pr.test.name
        assert sr.test.path == pr.test.path


def test_runner_captures_output():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    output_tests = [t for t in tests if "test_with_output" in t.name]
    if output_tests:
        results = oxytest.run_tests_sequential(output_tests)
        for r in results:
            assert r.output is not None


def test_runner_single_test():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir, pattern="test_pass")
    assert len(tests) == 1
    results = oxytest.run_tests_sequential(tests)
    assert len(results) == 1
    assert results[0].passed


def test_runner_class_tests():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    class_tests = [t for t in tests if "::" in t.name]
    assert len(class_tests) > 0
    results = oxytest.run_tests_sequential(class_tests)
    assert all(r.passed for r in results)
