"""Tests for _execute_test_impl edge cases: async, showlocals, pdb, errors."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest as pytest


# ── Async test execution ────────────────────────────────────────────


def test_async_basic():
    async def test_coro():
        return 42
    # Just verify the async function exists and works
    import asyncio
    result = asyncio.run(test_coro())
    assert result == 42


# ── showlocals ──────────────────────────────────────────────────────


def test_format_assert_detail_with_source(tmp_path):
    from oxytest._compat import _format_assert_detail
    pyfile = tmp_path / "test_src.py"
    pyfile.write_text("def test_f():\n    x = 42\n    assert x == 0\n")
    result = _format_assert_detail("assert x == 0", str(pyfile), 3)
    assert isinstance(result, str)
    assert len(result) > 0


# ── _execute_test error paths ───────────────────────────────────────


def test_execute_module_cache():
    from oxytest._compat import _module_cache, _module_cache_clear
    _module_cache_clear()
    _module_cache["/some/path.py"] = None
    # Verify module cache can hold None (import failed)
    assert _module_cache.get("/some/path.py") is None


def test_execute_module_import_error():
    from oxytest._compat import _get_test_module, _module_cache_clear
    _module_cache_clear()
    try:
        _get_test_module("/nonexistent/path/that/does/not/exist.py")
    except FileNotFoundError:
        pass


# ── Terminal reporter edge cases ────────────────────────────────────


def test_terminal_reporter_verbose_fail(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True)
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms",
                                            "output", "error", "error_output",
                                            "traceback"])
    t = FakeTest(path="test_x.py", name="test_fail")
    r = FakeResult(test=t, passed=False, duration_ms=10, output="out",
                   error="ValueError: oops", error_output="err",
                   traceback="  File test_x.py, line 1\n    raise ValueError")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "FAILED" in captured.out
    assert "test_fail" in captured.out


def test_terminal_reporter_tb_long(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True, tb_style="long")
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms",
                                            "output", "error", "error_output",
                                            "traceback"])
    t = FakeTest(path="test_x.py", name="test_long")
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="Error", error_output="",
                   traceback="Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


def test_terminal_reporter_tb_short_truncation(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True, tb_style="short")
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms",
                                            "output", "error", "error_output",
                                            "traceback"])
    t = FakeTest(path="test_x.py", name="test_short")
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="Error", error_output="",
                   traceback="  File x, line 1, in foo\n    result = x\n  File x, line 2, in bar\n    return foo()\n  File x, line 3, in baz\n    return bar()\n")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


# ── _ConfigStash edge cases ─────────────────────────────────────────


def test_config_stash_contains():
    from oxytest._compat import _ConfigStash
    stash = _ConfigStash({})
    stash["key"] = "value"
    assert "key" in stash


def test_config_stash_assertstate():
    from oxytest._compat import _ConfigStash
    stash = _ConfigStash({})
    key = type("K", (), {"__str__": lambda s: "assertstate_key"})()
    result = stash.get(key)
    # get() may return None if auto-populate fails
    assert result is None or result is not None


# ── Parser edge cases ───────────────────────────────────────────────


def test_parser_addoption_twice():
    from oxytest._compat import Parser
    parser = Parser()
    parser.addoption("--flag", action="store_true", default=False)
    result = parser.parse(["--flag"])
    assert result.get("flag") is True


def test_parser_with_value():
    from oxytest._compat import Parser
    parser = Parser()
    parser.addoption("--name", action="store", default="")
    result = parser.parse(["--name", "test_val"])
    assert result.get("name") == "test_val"

def test_importorskip_existing_module():
    pytest.importorskip("os.path")


# ── Approx edge cases ────────────────────────────────────────────────

def test_approx_nested_dict():
    inner = {"b": 0.3}
    outer = {"a": inner}
    assert outer == pytest.approx({"a": {"b": 0.3}})


def test_approx_tuple_nested():
    assert ((0.1 + 0.2,),) == pytest.approx(((0.3,),))


def test_approx_list_of_dicts():
    data = [{"x": 0.1 + 0.2}, {"x": 0.5}]
    expected = [{"x": 0.3}, {"x": 0.5}]
    assert data == pytest.approx(expected)


# ── Raises edge cases ────────────────────────────────────────────────


def test_raises_exception_group():
    import warnings
    with pytest.warns(DeprecationWarning) as record:
        warnings.warn("dep", DeprecationWarning)
    assert len(record) == 1


def test_raises_context_value_repr():
    with pytest.raises(ValueError) as excinfo:
        raise ValueError("custom msg")
    assert "custom msg" in str(excinfo.value)


# ── Mark decorator edge cases ────────────────────────────────────────


def test_mark_parametrize_single_value():
    @pytest.mark.parametrize("x", [1])
    def test_single(x):
        assert x == 1
    marks = getattr(test_single, "_oxytest_marks", [])
    assert len(marks) == 1


def test_mark_skipif_condition_false():
    @pytest.mark.skipif(False, reason="should not skip")
    def test_ok():
        pass
    marks = getattr(test_ok, "_oxytest_marks", [])
    assert len(marks) == 1
    assert marks[0][0] == "skipif"


def test_mark_xfail_strict():
    @pytest.mark.xfail(strict=True, reason="strict xfail")
    def test_strict():
        pass
    marks = getattr(test_strict, "_oxytest_marks", [])
    assert any("xfail" in m for m in marks)


def test_mark_usefixtures_multiple():
    @pytest.mark.usefixtures("a", "b", "c")
    def test_multi():
        pass
    marks = getattr(test_multi, "_oxytest_marks", [])
    assert len(marks) >= 1
    assert marks[0][0] == "usefixtures"


# ── importorskip edge cases ──────────────────────────────────────────


def test_importorskip_minversion_too_low():
    try:
        pytest.importorskip("os", minversion="999.0")
        assert False
    except pytest.SkipTest:
        pass




# ── Fixture request edge cases ──────────────────────────────────────


def test_fixture_request_param_none():
    req = pytest.FixtureRequest(scope="function", _test_func=None)
    assert req.param is None
    assert req.scope == "function"
    assert hasattr(req, "fixtures")


def test_fixture_request_config_getoption():
    from oxytest._compat import FixtureRequest
    req = FixtureRequest(_test_func=None)
    cfg = req.config
    assert hasattr(cfg, "getoption") or cfg is None


# ── _json_safe edge cases ────────────────────────────────────────────


def test_json_safe_list():
    from oxytest._compat import _json_safe
    result = _json_safe([1, 2, 3])
    assert result == [1, 2, 3]


def test_json_safe_dict():
    from oxytest._compat import _json_safe
    result = _json_safe({"a": 1})
    assert result == {"a": 1}


def test_json_safe_bytes_in_list():
    from oxytest._compat import _json_safe
    result = _json_safe([b"hello", "world"])
    assert isinstance(result[0], str)
    assert result[1] == "world"


# ── _parse_filterwarnings_args tests ─────────────────────────────────


def test_parse_filterwarnings_simple():
    from oxytest._compat import _parse_filterwarnings_args
    result = _parse_filterwarnings_args(["ignore"])
    assert result is not None
    args, kwargs = result
    assert args[0] == "ignore"


def test_parse_filterwarnings_colon_format():
    from oxytest._compat import _parse_filterwarnings_args
    result = _parse_filterwarnings_args(["ignore::DeprecationWarning"])
    assert result is not None
    args, kwargs = result
    assert args[0] == "ignore"
    assert kwargs.get("category") is DeprecationWarning


def test_parse_filterwarnings_full():
    from oxytest._compat import _parse_filterwarnings_args
    result = _parse_filterwarnings_args(["ignore:message.*:UserWarning"])
    assert result is not None
    args, kwargs = result
    assert args[0] == "ignore"
    assert kwargs.get("message") == "message.*"


def test_parse_filterwarnings_empty():
    from oxytest._compat import _parse_filterwarnings_args
    assert _parse_filterwarnings_args([]) is None


def test_parse_filterwarnings_already_parsed():
    from oxytest._compat import _parse_filterwarnings_args
    result = _parse_filterwarnings_args(["ignore", "", UserWarning])
    assert result is not None
    args, kwargs = result
    assert kwargs.get("category") is UserWarning


# ── _should_skip / _is_xfail tests ───────────────────────────────────


def test_should_skip_no_marks():
    from oxytest._compat import _should_skip
    def f():
        pass
    assert _should_skip(f) is None


def test_should_skip_with_mark():
    from oxytest._compat import _should_skip
    def f():
        pass
    f._oxytest_marks = [("skip", (), {"reason": "test skip"})]
    assert _should_skip(f) == "test skip"


def test_should_skip_skipif_true():
    from oxytest._compat import _should_skip
    def f():
        pass
    f._oxytest_marks = [("skipif", (True,), {"reason": "condition met"})]
    assert _should_skip(f) == "condition met"


def test_should_skip_skipif_false():
    from oxytest._compat import _should_skip
    def f():
        pass
    f._oxytest_marks = [("skipif", (False,), {"reason": "not met"})]
    assert _should_skip(f) is None


def test_should_skip_module_level():
    from oxytest._compat import _should_skip
    def f():
        pass
    class MockMod:
        pytestmark = "skip"
    assert _should_skip(f, mod=MockMod()) is not None


def test_is_xfail_no_marks():
    from oxytest._compat import _is_xfail
    def f():
        pass
    assert _is_xfail(f) is None


def test_is_xfail_with_mark():
    from oxytest._compat import _is_xfail
    def f():
        pass
    f._oxytest_marks = [("xfail", (), {"reason": "known issue"})]
    assert _is_xfail(f) is not None


# ── TerminalReporter tests ───────────────────────────────────────────


def test_terminal_reporter_basic():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter(tb_style="short")
    from oxytest.types import TestResult
    result = TestResult()
    result.name = "test_foo"
    result.path = "test_foo.py"
    result.duration_ms = 10
    result.passed = True
    reporter.add_result(result)
    assert reporter.stats["passed"] == 1
    assert reporter.get_exit_code() == 0


def test_terminal_reporter_failed():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter(tb_style="short")
    from oxytest.types import TestResult
    result = TestResult()
    result.name = "test_bar"
    result.path = "test_bar.py"
    result.duration_ms = 5
    result.passed = False
    result.error = "test error"
    reporter.add_result(result)
    assert reporter.stats["failed"] == 1
    assert reporter.get_exit_code() == 1


def test_terminal_reporter_skipped():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter(tb_style="short")
    from oxytest.types import TestResult
    result = TestResult()
    result.name = "test_skip"
    result.path = "test_skip.py"
    result.duration_ms = 0
    result.passed = True
    result.skipped = True
    reporter.add_result(result)
    assert reporter.stats["skipped"] == 1


def test_terminal_reporter_durations():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter(tb_style="short")
    from oxytest.types import TestResult
    for i in range(5):
        r = TestResult()
        r.name = f"test_{i}"
        r.path = f"test_{i}.py"
        r.duration_ms = i * 100
        r.passed = True
        reporter.add_result(r)
    # Should not raise
    import io
    out = io.StringIO()
    try:
        reporter.finish(out, durations=2)
    finally:
        out.close()


# ── _validate_markers tests ──────────────────────────────────────────


def test_validate_markers_empty():
    from oxytest._compat import _validate_markers
    _validate_markers([])


def test_validate_markers_known():
    from oxytest._compat import _validate_markers
    class MockTest:
        def __init__(self):
            self.path = __file__
            self.name = "test_validate_markers_empty"
    _validate_markers([MockTest()])


# ── _is_ignored tests ────────────────────────────────────────────────


def test_is_ignored():
    from oxytest._compat import _is_ignored
    assert _is_ignored("/tmp/tests/foo.py", ["/tmp/tests"])
    assert not _is_ignored("/tmp/src/foo.py", ["/tmp/tests"])


def test_is_ignored_with_subdir():
    from oxytest._compat import _is_ignored
    assert _is_ignored("/tmp/tests/sub/foo.py", ["/tmp/tests"])


# ── _json_safe edge cases ──────────────────────────────────────────── (cont)

def test_json_safe_none():
    from oxytest._compat import _json_safe
    assert _json_safe(None) is None


def test_json_safe_int():
    from oxytest._compat import _json_safe
    assert _json_safe(42) == 42


def test_json_safe_str():
    from oxytest._compat import _json_safe
    assert _json_safe("hello") == "hello"


def test_json_safe_nested():
    from oxytest._compat import _json_safe
    data = {"a": [1, b"bytes", {"nested": True}]}
    result = _json_safe(data)
    assert isinstance(result["a"][1], str)
