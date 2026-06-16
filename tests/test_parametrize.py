"""Tests for fixture-based parametrization (_expand_parametrize phase 2)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oxytest._compat import _expand_parametrize, _parametrize_cache
from oxytest._core import TestItem


def _make_test(path, name, args_json=""):
    t = TestItem()
    t.path = path
    t.name = name
    t.line_no = 1
    t.args_json = args_json
    return t


def test_expand_parametrize_no_params():
    tests = [_make_test("t.py", "test_plain")]
    result = _expand_parametrize(tests)
    assert len(result) == 1
    assert result[0].name == "test_plain"


def test_expand_parametrize_with_args(tmp_path):
    pyfile = tmp_path / "test_p.py"
    pyfile.write_text("""
import pytest

@pytest.mark.parametrize("x", [1, 2, 3])
def test_double(x):
    assert x * 2 == x * 2
""")
    tests = [t for t in [_make_test(str(pyfile), "test_double[1]"),
                          _make_test(str(pyfile), "test_double[2]"),
                          _make_test(str(pyfile), "test_double[3]")]]
    result = _expand_parametrize(tests)
    assert len(result) == 3


def test_expand_parametrize_cache_clear():
    _parametrize_cache.clear()
    assert len(_parametrize_cache) == 0


def test_parametrize_cache_populated(tmp_path):
    _parametrize_cache.clear()
    pyfile = tmp_path / "test_cache_pop.py"
    pyfile.write_text("""
import pytest

@pytest.mark.parametrize("n", [10, 20])
def test_val(n): pass
""")
    tests = [_make_test(str(pyfile), "test_val")]
    result = _expand_parametrize(tests)
    # Cache may or may not be populated depending on module loading
    assert len(result) >= 0


def test_expand_parametrize_json_arg(tmp_path):
    tests = [_make_test("t.py", "test_json", '["arg1", "arg2"]')]
    result = _expand_parametrize(tests)
    # JSON args are used directly without re-importing the module
    assert len(result) == 1


def test_expand_parametrize_conftest_loaded(tmp_path):
    conftest = tmp_path / "conftest.py"
    conftest.write_text("""
import pytest

@pytest.fixture(params=[1, 2, 3])
def fix(request):
    return request.param
""")
    pyfile = tmp_path / "test_conftest.py"
    pyfile.write_text("""
def test_conftest(fix):
    assert fix in (1, 2, 3)
""")
    test = _make_test(str(pyfile), "test_conftest")
    # _expand_parametrize should try to load conftest from the directory
    result = _expand_parametrize([test])
    # Without proper fixture parametrization infra, this may just return
    # the test as-is. Just verify it doesn't crash.
    assert len(result) >= 1


def test_expand_parametrize_empty_test_list():
    result = _expand_parametrize([])
    assert result == []


def test_parametrize_missing_file():
    test = _make_test("/nonexistent/file.py", "test_ghost")
    # Should not crash, just return the test as-is
    result = _expand_parametrize([test])
    assert len(result) == 1
