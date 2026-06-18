"""Tests for keyword (-k) and marker (-m) expression filtering."""

from oxytest._compat import (
    _parse_keyword_expression,
    _eval_keyword_expression,
    _match_keyword,
    _filter_keyword_expression,
    _filter_marker_expression,
)


def _make_test(path="tests/test_foo.py", name="test_bar"):
    from oxytest import TestItem
    t = TestItem()
    t.path = path
    t.name = name
    t.line_no = 1
    t.args_json = ""
    return t


# ── Keyword expression parsing ──────────────────────────────────────


def test_parse_simple():
    assert _parse_keyword_expression("foo") == ["foo"]


def test_parse_and():
    assert _parse_keyword_expression("foo and bar") == ["foo", "AND", "bar"]


def test_parse_or():
    assert _parse_keyword_expression("foo or bar") == ["foo", "OR", "bar"]


def test_parse_not():
    assert _parse_keyword_expression("not foo") == ["NOT", "foo"]


def test_parse_parens():
    result = _parse_keyword_expression("(foo or bar) and baz")
    assert result == ["(", "foo", "OR", "bar", ")", "AND", "baz"]


def test_parse_nested():
    result = _parse_keyword_expression("not (foo and bar)")
    assert result == ["NOT", "(", "foo", "AND", "bar", ")"]


def test_parse_quoted():
    result = _parse_keyword_expression('"foo bar"')
    assert len(result) == 1
    assert result[0] == '"foo bar"'


# ── Keyword expression evaluation ────────────────────────────────────


def test_eval_simple():
    assert _eval_keyword_expression(["foo"], "test_foo.py::test_foo", []) is True
    assert _eval_keyword_expression(["bar"], "test_foo.py::test_foo", []) is False


def test_eval_and():
    tokens = _parse_keyword_expression("foo and bar")
    assert _eval_keyword_expression(tokens, "test_foo_bar.py::test_foo_bar", []) is True
    assert _eval_keyword_expression(tokens, "test_foo.py::test_foo", []) is False


def test_eval_or():
    tokens = _parse_keyword_expression("foo or bar")
    assert _eval_keyword_expression(tokens, "test_foo.py::test_foo", []) is True
    assert _eval_keyword_expression(tokens, "test_baz.py::test_baz", []) is False


def test_eval_not():
    tokens = _parse_keyword_expression("not foo")
    assert _eval_keyword_expression(tokens, "test_bar.py::test_bar", []) is True
    assert _eval_keyword_expression(tokens, "test_foo.py::test_foo", []) is False


def test_eval_parens():
    tokens = _parse_keyword_expression("(foo or bar) and baz")
    assert _eval_keyword_expression(tokens, "test_foo_baz.py::test_foo_baz", []) is True
    assert _eval_keyword_expression(tokens, "test_foo.py::test_foo", []) is False


def test_eval_empty():
    assert _eval_keyword_expression([], "test_foo.py::test_foo", []) is True


# ── _match_keyword ───────────────────────────────────────────────────


def test_match_keyword_simple():
    assert _match_keyword("foo", "test_foo.py::test_foo", []) is True
    assert _match_keyword("bar", "test_foo.py::test_foo", []) is False


def test_match_keyword_markers():
    markers = ["slow"]
    assert _match_keyword("slow", "test_foo.py::test_foo", markers) is True
    assert _match_keyword("fast", "test_foo.py::test_foo", markers) is False


def test_match_keyword_marker_objects():
    class MockMark:
        def __init__(self, name):
            self.name = name
    markers = [MockMark("slow")]
    assert _match_keyword("slow", "test_foo.py::test_foo", markers) is True


def test_filter_keyword_empty():
    result = _filter_keyword_expression([], "foo")
    assert result == []


def test_filter_marker_empty():
    result = _filter_marker_expression([], "slow")
    assert result == []
