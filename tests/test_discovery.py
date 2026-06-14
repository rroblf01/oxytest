import os
import sys
import tempfile
import pathlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest


def test_discover_simple():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    assert len(tests) > 0, "Should discover at least some tests"

    # Check that simple test functions are found
    test_names = [t.name for t in tests]
    assert "test_pass" in test_names
    assert "test_fail" in test_names
    assert "test_string" in test_names
    assert "test_math" in test_names
    assert "test_list" in test_names
    assert "test_dict" in test_names


def test_discover_class_tests():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    test_names = [t.name for t in tests]

    assert "TestMath::test_addition" in test_names
    assert "TestMath::test_subtraction" in test_names
    assert "TestMath::test_multiplication" in test_names
    assert "TestString::test_upper" in test_names


def test_discover_keyword_filter():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir, pattern="math")
    test_names = [t.name for t in tests]
    assert any("math" in n.lower() or "Math" in n for n in test_names)


def test_discover_not_found_directory():
    tests = oxytest.discover_tests("/nonexistent/path")
    assert len(tests) == 0


def test_discover_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        tests = oxytest.discover_tests(tmpdir)
        assert len(tests) == 0


def test_discover_returns_test_items():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    for t in tests:
        assert hasattr(t, "path")
        assert hasattr(t, "name")
        assert hasattr(t, "line_no")
        assert t.path.endswith(".py")
        assert t.name.startswith("test") or "::" in t.name


def test_discover_ordering():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    for i in range(len(tests) - 1):
        current = tests[i]
        next_t = tests[i + 1]
        if current.path == next_t.path:
            assert current.line_no <= next_t.line_no


def test_discover_test_files():
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_tests")
    tests = oxytest.discover_tests(sample_dir)
    files_found = set()
    for t in tests:
        files_found.add(os.path.basename(t.path))
    assert "test_simple.py" in files_found
    assert "test_class.py" in files_found
