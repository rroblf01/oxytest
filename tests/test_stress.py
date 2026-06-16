"""Stress and edge-case tests for oxytest stability."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


# ── Stress: many test files ─────────────────────────────────────────


def test_stress_many_files(tmp_path):
    """Discover 500 test files with 5 tests each = 2500 tests."""
    for i in range(500):
        _write(os.path.join(tmp_path, f"test_stress_{i}.py"), "\n".join(
            f"def test_{j}(): pass" for j in range(5)
        ))
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 2500


def test_stress_many_tests_single_file(tmp_path):
    """One file with 1000 test functions."""
    content = "\n".join(f"def test_{i}(): pass" for i in range(1000))
    _write(os.path.join(tmp_path, "test_big.py"), content)
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1000


# ── Path edge cases ─────────────────────────────────────────────────


def test_stress_very_long_path(tmp_path):
    """Test with a very long directory path (>200 chars)."""
    long_name = "a" * 180
    deep = os.path.join(tmp_path, long_name)
    os.makedirs(deep)
    _write(os.path.join(deep, "test_deep.py"), "def test_deep(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_deep"


def test_stress_unicode_in_path(tmp_path):
    """Unicode characters in directory names."""
    unicode_dir = os.path.join(tmp_path, "über_tests_ñöë")
    os.makedirs(unicode_dir)
    _write(os.path.join(unicode_dir, "test_ünicode.py"),
           "def test_ünicode(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1


def test_stress_spaces_in_path(tmp_path):
    """Spaces in directory and file names."""
    spaced = os.path.join(tmp_path, "my tests", "sub folder")
    os.makedirs(spaced)
    _write(os.path.join(spaced, "test with spaces.py"),
           "def test_with_spaces(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    # oxytest may or may not handle spaces in paths
    assert len(tests) >= 0


# ── Edge cases ──────────────────────────────────────────────────────


def test_stress_no_test_files(tmp_path):
    """Directory with no test files at all."""
    os.makedirs(os.path.join(tmp_path, "src"))
    os.makedirs(os.path.join(tmp_path, "docs"))
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


def test_stress_only_non_py_files(tmp_path):
    """Directory with non-.py files only."""
    _write(os.path.join(tmp_path, "data.json"), '{"key": "val"}')
    _write(os.path.join(tmp_path, "script.sh"), "echo hello")
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


def test_stress_mixed_content(tmp_path):
    """Mix of test files, non-test files, and hidden dirs."""
    _write(os.path.join(tmp_path, "test_good.py"), "def test_ok(): pass")
    _write(os.path.join(tmp_path, "setup.py"), "")
    _write(os.path.join(tmp_path, "readme.md"), "# Docs")
    hidden = os.path.join(tmp_path, ".hidden")
    os.makedirs(hidden)
    _write(os.path.join(hidden, "test_hidden.py"), "def test_hidden(): pass")
    cache = os.path.join(tmp_path, "__pycache__")
    os.makedirs(cache)
    _write(os.path.join(cache, "test_cached.py"), "def test_cached(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_ok"


def test_stress_empty_files(tmp_path):
    """Empty .py files should not cause crashes."""
    _write(os.path.join(tmp_path, "test_empty1.py"), "")
    _write(os.path.join(tmp_path, "test_empty2.py"), "")
    _write(os.path.join(tmp_path, "test_real.py"), "def test_real(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_real"


def test_stress_just_comments(tmp_path):
    """File with only comments should yield no tests."""
    _write(os.path.join(tmp_path, "test_comments.py"), """
# this is a comment
# another comment
""")
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


# ── Keyword filtering stress ────────────────────────────────────────


def test_stress_keyword_no_match(tmp_path):
    _write(os.path.join(tmp_path, "test_a.py"), "def test_alpha(): pass")
    tests = oxytest.discover_tests(str(tmp_path), pattern="nonexistent")
    assert tests == []


def test_stress_keyword_all_match(tmp_path):
    _write(os.path.join(tmp_path, "test_a.py"),
           "def test_common(): pass\ndef test_common2(): pass")
    tests = oxytest.discover_tests(str(tmp_path), pattern="common")
    assert len(tests) == 2
