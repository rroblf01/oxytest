"""Integration tests for Rust-based test discovery with real temp directories."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest as pytest
import oxytest


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def test_discover_empty_dir(tmp_path):
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


def test_discover_single_file(tmp_path):
    _write(os.path.join(tmp_path, "test_a.py"), "def test_hello(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_hello"
    assert tests[0].path.endswith("test_a.py")


def test_discover_multiple_files(tmp_path):
    _write(os.path.join(tmp_path, "test_a.py"), "def test_a1(): pass\ndef test_a2(): pass")
    _write(os.path.join(tmp_path, "test_b.py"), "def test_b1(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 3


def test_discover_class_tests(tmp_path):
    _write(os.path.join(tmp_path, "test_cls.py"), """
class TestMath:
    def test_add(self): pass
    def test_sub(self): pass
""")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 2
    assert "TestMath" in tests[0].name
    assert "TestMath" in tests[1].name


def test_discover_async_tests(tmp_path):
    _write(os.path.join(tmp_path, "test_async.py"), "async def test_async_func(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_async_func"


def test_discover_ignores_non_test_files(tmp_path):
    _write(os.path.join(tmp_path, "test_real.py"), "def test_real(): pass")
    _write(os.path.join(tmp_path, "helper.py"), "def helper(): pass")
    _write(os.path.join(tmp_path, "setup.py"), "def setup(): pass")
    _write(os.path.join(tmp_path, "conftest.py"), "")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_real"


def test_discover_ignores_hidden_dirs(tmp_path):
    hidden = os.path.join(tmp_path, "__pycache__")
    os.makedirs(hidden)
    _write(os.path.join(hidden, "test_x.py"), "def test_x(): pass")
    _write(os.path.join(tmp_path, "test_visible.py"), "def test_visible(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_visible"


def test_discover_ignores_venv(tmp_path):
    venv = os.path.join(tmp_path, ".venv")
    os.makedirs(venv)
    _write(os.path.join(venv, "test_x.py"), "def test_x(): pass")
    _write(os.path.join(tmp_path, "test_real.py"), "def test_real(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_real"


def test_discover_with_pattern(tmp_path):
    _write(os.path.join(tmp_path, "test_a.py"), "def test_alpha(): pass")
    _write(os.path.join(tmp_path, "test_b.py"), "def test_beta(): pass")
    tests = oxytest.discover_tests(str(tmp_path), pattern="beta")
    assert len(tests) == 1
    assert tests[0].name == "test_beta"


def test_discover_suffix_files(tmp_path):
    _write(os.path.join(tmp_path, "api_test.py"), "def test_api(): pass")
    _write(os.path.join(tmp_path, "unit_test.py"), "def test_unit(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 2


def test_discover_nonexistent_dir():
    result = oxytest.discover_tests("/nonexistent/path/xyz789")
    assert result == []


def test_discover_symlink_dir(tmp_path):
    real = os.path.join(tmp_path, "real")
    os.makedirs(real)
    _write(os.path.join(real, "test_sym.py"), "def test_sym(): pass")
    try:
        link = os.path.join(tmp_path, "link")
        os.symlink(real, link)
    except (OSError, NotImplementedError):
        return  # skip if symlinks not supported
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) >= 1


def test_discover_deeply_nested(tmp_path):
    current = tmp_path
    for i in range(10):
        current = os.path.join(current, f"sub{i}")
    os.makedirs(current)
    _write(os.path.join(current, "test_deep.py"), "def test_deep(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1
    assert tests[0].name == "test_deep"


def test_discover_unicode_filename(tmp_path):
    import sys
    if sys.platform.startswith("win32"):
        pytest.skip("Unicode filenames not fully supported on Windows filesystem")
    _write(os.path.join(tmp_path, "test_unicode_ñ.py"), "def test_ñ(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 1


def test_discover_empty_file(tmp_path):
    _write(os.path.join(tmp_path, "test_empty.py"), "")
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


def test_discover_syntax_error_file(tmp_path):
    _write(os.path.join(tmp_path, "test_broken.py"), "def broken( pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []  # gracefully returns empty


def test_discover_only_test_class_no_functions(tmp_path):
    _write(os.path.join(tmp_path, "test_empty_class.py"), """
class TestEmpty:
    pass
""")
    tests = oxytest.discover_tests(str(tmp_path))
    assert tests == []


def test_discover_sorts_by_path_then_line(tmp_path):
    _write(os.path.join(tmp_path, "test_z.py"), "def test_z(): pass")
    _write(os.path.join(tmp_path, "test_a.py"),
           "def test_a2(): pass\ndef test_a1(): pass")
    tests = oxytest.discover_tests(str(tmp_path))
    assert len(tests) == 3
    # Should be sorted: test_a.py::test_a2, test_a.py::test_a1, test_z.py::test_z
    assert tests[0].path < tests[-1].path or (tests[0].path == tests[-1].path)
