"""Tests for oxytest._doctest module."""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oxytest._doctest import (
    _has_doctest_docstring,
    _collect_doctests_from_node,
    collect_module_doctests,
    make_doctest_items,
    _DOCTEST_PREFIX,
)


_SAMPLE_PATH = os.path.join(
    os.path.dirname(__file__), "sample_tests", "test_with_doctests.py"
)


def test_has_doctest_docstring_true():
    code = 'def foo():\n    """Has doctest.\n    \n    >>> print(1)\n    1\n    """\n    pass'
    tree = ast.parse(code)
    func = tree.body[0]
    assert _has_doctest_docstring(func) is True


def test_has_doctest_docstring_false():
    code = '"""No doctest here."""\ndef foo(): pass'
    tree = ast.parse(code)
    func = tree.body[1]
    assert _has_doctest_docstring(func) is False


def test_has_doctest_docstring_no_docstring():
    code = "def foo(): pass"
    tree = ast.parse(code)
    func = tree.body[0]
    assert _has_doctest_docstring(func) is False


def test_has_doctest_docstring_non_func():
    code = "x = 1"
    tree = ast.parse(code)
    assert _has_doctest_docstring(tree.body[0]) is False


def test_collect_doctests_from_node():
    code = '''"""Module docstring with >>>.

>>> 1 + 1
2
"""
def foo():
    """Foo docstring with >>>.

    >>> 2 + 2
    4
    """
class Bar:
    """Bar class with >>>.

    >>> Bar()
    <Bar>
    """
    def baz(self):
        """baz method with >>>.

        >>> Bar().baz()
        "ok"
        """
'''
    tree = ast.parse(code)
    results = []
    _collect_doctests_from_node(tree, "mymod", "", results)
    names = [r[0] for r in results]
    assert "mymod" in names
    assert "mymod.foo" in names
    assert "mymod.Bar" in names
    assert "mymod.Bar.baz" in names


def test_collect_module_doctests():
    results = collect_module_doctests(_SAMPLE_PATH)
    names = [r[0] for r in results]
    assert "test_with_doctests.add" in names
    assert "test_with_doctests.Calculator" in names
    assert "test_with_doctests.Calculator.mul" in names
    for _, lineno in results:
        assert isinstance(lineno, int)
        assert lineno > 0


def test_collect_module_doctests_no_source():
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    try:
        f.write("x = 1\ny = 2\n")
        f.close()
        results = collect_module_doctests(f.name)
        assert results == []
    finally:
        os.unlink(f.name)


def test_collect_module_doctests_syntax_error():
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    try:
        f.write("this is not valid python @@@\n")
        f.close()
        results = collect_module_doctests(f.name)
        assert results == []
    finally:
        os.unlink(f.name)


def test_make_doctest_items():
    items = make_doctest_items(_SAMPLE_PATH, None)
    names = [item.name for item in items]
    assert _DOCTEST_PREFIX + "test_with_doctests.add" in names
    assert _DOCTEST_PREFIX + "test_with_doctests.Calculator" in names
    assert _DOCTEST_PREFIX + "test_with_doctests.Calculator.mul" in names
    for item in items:
        assert item.path == _SAMPLE_PATH
        assert item.line_no > 0


def test_make_doctest_items_no_doctests():
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    try:
        f.write("def no_doctest(): pass\n")
        f.close()
        items = make_doctest_items(f.name, None)
        assert items == []
    finally:
        os.unlink(f.name)
