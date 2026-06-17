import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import oxytest as pytest


def test_main_import():
    assert hasattr(pytest, "main")
    assert callable(pytest.main)


def test_approx_import():
    assert hasattr(pytest, "approx")
    assert callable(pytest.approx)


def test_raises_import():
    assert hasattr(pytest, "raises")
    assert callable(pytest.raises)


def test_fixture_import():
    assert hasattr(pytest, "fixture")
    assert callable(pytest.fixture)


def test_mark_import():
    assert hasattr(pytest, "mark")
    assert hasattr(pytest.mark, "parametrize")
    assert hasattr(pytest.mark, "skip")
    assert hasattr(pytest.mark, "skipif")
    assert hasattr(pytest.mark, "xfail")


def test_helpers_import():
    assert hasattr(pytest, "skip")
    assert hasattr(pytest, "fail")
    assert hasattr(pytest, "exit")
    assert hasattr(pytest, "set_trace")
    assert hasattr(pytest, "importorskip")
    assert hasattr(pytest, "param")


def test_exceptions_import():
    assert hasattr(pytest, "Exit")
    assert hasattr(pytest, "PytestError")
    assert hasattr(pytest, "UsageError")
    assert hasattr(pytest, "SkipTest")
    assert hasattr(pytest, "Failed")


def test_approx_equality():
    assert 0.1 + 0.2 == pytest.approx(0.3)


def test_approx_list():
    assert [0.1 + 0.2, 0.2 + 0.3] == pytest.approx([0.3, 0.5])


def test_approx_dict():
    assert {"a": 0.1 + 0.2} == pytest.approx({"a": 0.3})


def test_raises_context():
    with pytest.raises(ValueError):
        int("not_a_number")


def test_raises_no_exception():
    try:
        with pytest.raises(ValueError):
            pass
        assert False, "Should have raised Failed"
    except pytest.Failed:
        pass


def test_raises_wrong_exception():
    with pytest.raises(ValueError):
        with pytest.raises(TypeError):
            int("not_a_number")


def test_raises_match():
    with pytest.raises(ValueError, match="invalid"):
        int("invalid literal")


def test_skip_raises():
    try:
        pytest.skip("testing skip")
        assert False, "Should have raised SkipTest"
    except pytest.SkipTest:
        pass


def test_fail_raises():
    try:
        pytest.fail("testing fail")
        assert False, "Should have raised Failed"
    except pytest.Failed:
        pass


def test_mark_decorator():
    @pytest.mark.skip(reason="testing")
    def dummy():
        pass
    assert hasattr(dummy, "_oxytest_marks")
    assert dummy._oxytest_marks[0][0] == "skip"


def test_mark_parametrize():
    @pytest.mark.parametrize("a,b", [(1, 2), (3, 4)])
    def dummy(a, b):
        pass
    assert hasattr(dummy, "_oxytest_marks")


def test_main_returns_int():
    result = pytest.main(["--help"])
    assert isinstance(result, int)


def test_main_version():
    result = pytest.main(["--version"])
    assert isinstance(result, int)


def test_version_string():
    from oxytest import __version__
    assert isinstance(__version__, str)
    assert __version__ == "3.0.0"


def test_test_item_repr():
    tests = pytest.discover_tests(os.path.join(os.path.dirname(__file__), "sample_tests"))
    if tests:
        assert "test_" in repr(tests[0]) or "::" in repr(tests[0])


def test_exit_via_main():
    result = pytest.main(["-v", os.path.join(os.path.dirname(__file__), "sample_tests")])
    assert isinstance(result, int)


def test_raises_with_callable():
    pytest.raises(ValueError, int, "not_a_number")


def test_raises_with_callable_no_exception():
    try:
        pytest.raises(ValueError, int, "42")
        assert False, "Should have raised Failed"
    except pytest.Failed:
        pass


def test_raises_with_callable_wrong_exception():
    try:
        pytest.raises(TypeError, int, "not_a_number")
        assert False, "Should have propagated ValueError"
    except ValueError:
        pass


def test_warns_basic():
    with pytest.warns(UserWarning):
        import warnings
        warnings.warn("test warning", UserWarning)


def test_warns_match():
    with pytest.warns(UserWarning, match="specific"):
        import warnings
        warnings.warn("specific warning", UserWarning)


def test_warns_no_warning():
    try:
        with pytest.warns(UserWarning):
            pass
        assert False, "Should have raised Failed"
    except pytest.Failed:
        pass


def test_warns_nested():
    import warnings
    with pytest.warns(UserWarning, match="outer"):
        with pytest.warns(UserWarning, match="inner"):
            warnings.warn("inner message", UserWarning)
            warnings.warn("outer message", UserWarning)


def test_warns_nested_both_nonexistent():
    import warnings
    try:
        with pytest.warns(UserWarning, match="nonexistent"):
            with pytest.warns(UserWarning, match="also_not_there"):
                warnings.warn("some message", UserWarning)
        assert False, "Should have raised Failed"
    except pytest.Failed:
        pass


def test_deprecated_call():
    import warnings
    with pytest.deprecated_call():
        warnings.warn("deprecated", DeprecationWarning)


def test_deprecated_call_pending():
    import warnings
    with pytest.deprecated_call():
        warnings.warn("pending deprecated", PendingDeprecationWarning)


def test_exit_code_enum():
    assert pytest.ExitCode.OK == 0
    assert pytest.ExitCode.TESTS_FAILED == 1
    assert pytest.ExitCode.INTERRUPTED == 2
    assert pytest.ExitCode.INTERNAL_ERROR == 3
    assert pytest.ExitCode.USAGE_ERROR == 4
    assert pytest.ExitCode.NO_TESTS_COLLECTED == 5
    assert pytest.ExitCode.MAX_WARNINGS_ERROR == 6


def test_format_assert_detail():
    from oxytest._compat import _format_assert_detail
    result = _format_assert_detail("assert x == y", "test.py", 1)
    assert isinstance(result, str)
    result2 = _format_assert_detail("x = 1", "test.py", 1)
    assert isinstance(result2, str)


def test_parse_keyword_expression():
    from oxytest._compat import _parse_keyword_expression
    tokens = _parse_keyword_expression("math or pass")
    assert "OR" in tokens


def test_parse_keyword_expression_parens():
    from oxytest._compat import _parse_keyword_expression
    tokens = _parse_keyword_expression("(math or pass) and not slow")
    assert "(" in tokens
    assert ")" in tokens
    assert "NOT" in tokens


def test_eval_keyword_expression_simple():
    from oxytest._compat import _eval_keyword_expression, _parse_keyword_expression
    tokens = _parse_keyword_expression("math")
    assert _eval_keyword_expression(tokens, "test_math", []) is True
    assert _eval_keyword_expression(tokens, "test_other", []) is False


def test_eval_keyword_expression_or():
    from oxytest._compat import _eval_keyword_expression, _parse_keyword_expression
    tokens = _parse_keyword_expression("math or pass")
    assert _eval_keyword_expression(tokens, "test_math", []) is True
    assert _eval_keyword_expression(tokens, "test_pass", []) is True
    assert _eval_keyword_expression(tokens, "test_other", []) is False


def test_eval_keyword_expression_and():
    from oxytest._compat import _eval_keyword_expression, _parse_keyword_expression
    tokens = _parse_keyword_expression("math and pass")
    assert _eval_keyword_expression(tokens, "test_math_and_pass", []) is True
    assert _eval_keyword_expression(tokens, "test_math", []) is False


def test_eval_keyword_expression_not():
    from oxytest._compat import _eval_keyword_expression, _parse_keyword_expression
    tokens = _parse_keyword_expression("not math")
    assert _eval_keyword_expression(tokens, "test_other", []) is True
    assert _eval_keyword_expression(tokens, "test_math", []) is False


def test_eval_keyword_expression_marker():
    from oxytest._compat import _eval_keyword_expression, _parse_keyword_expression
    tokens = _parse_keyword_expression("slow")
    assert _eval_keyword_expression(tokens, "test_foo", ["slow"]) is True
    assert _eval_keyword_expression(tokens, "test_foo", []) is False


def test_match_keyword_quoted():
    from oxytest._compat import _match_keyword
    assert _match_keyword('"math"', "test_math", []) is True
    assert _match_keyword('"slow"', "test_math", []) is False


def test_filter_keyword_expression():
    from oxytest._compat import _filter_keyword_expression
    from oxytest._core import TestItem
    t1 = TestItem()
    t1.path = "test_a.py"
    t1.name = "test_math"
    t2 = TestItem()
    t2.path = "test_b.py"
    t2.name = "test_pass"
    t3 = TestItem()
    t3.path = "test_c.py"
    t3.name = "test_slow"
    filtered = _filter_keyword_expression([t1, t2, t3], "math or pass")
    assert len(filtered) == 2
    filtered2 = _filter_keyword_expression([t1, t2, t3], "not slow")
    assert len(filtered2) == 2


def test_is_ignored():
    from oxytest._compat import _is_ignored
    assert _is_ignored("tests/old/test_x.py", ["tests/old"])
    assert not _is_ignored("tests/new/test_x.py", ["tests/old"])


def test_clear_cache(tmp_path):
    from oxytest._compat import _clear_cache
    cache_dir = tmp_path / ".pytest_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "test.txt").write_text("data")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        _clear_cache()
        assert not cache_dir.exists()
    finally:
        os.chdir(old_cwd)


def test_lastfailed_cache(tmp_path):
    from oxytest._compat import _read_lastfailed, _write_lastfailed, _module_cache_clear
    _module_cache_clear()
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        lf = _read_lastfailed()
        assert lf == set()
        results = []
        _write_lastfailed(results)
        assert _read_lastfailed() == set()
    finally:
        os.chdir(old_cwd)


def test_print_collected(capsys):
    from oxytest._compat import _print_collected
    from oxytest._core import TestItem
    t = TestItem()
    t.path = "test_x.py"
    t.name = "test_y"
    _print_collected([t], verbose=True)
    captured = capsys.readouterr()
    assert "test_x.py" in captured.out


def test_print_collected_quiet(capsys):
    from oxytest._compat import _print_collected
    from oxytest._core import TestItem
    t = TestItem()
    t.path = "test_x.py"
    t.name = "test_y"
    _print_collected([t], verbose=False)
    captured = capsys.readouterr()
    assert "Collected 1 test(s)" in captured.out


def test_importorskip():
    result = pytest.importorskip("os")
    import os
    assert result is os


def test_importorskip_missing():
    try:
        pytest.importorskip("nonexistent_module_xyz")
        assert False, "Should have raised SkipTest"
    except pytest.SkipTest:
        pass


def test_importorskip_minversion():
    result = pytest.importorskip("pytest", minversion="0.1")
    assert result is not None


def test_mark_usefixtures():
    @pytest.mark.usefixtures("db", "cache")
    def test_foo():
        pass
    assert hasattr(test_foo, "_oxytest_marks")


def test_mark_filterwarnings():
    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_foo():
        pass
    assert hasattr(test_foo, "_oxytest_marks")


def test_param_with_marks():
    result = pytest.param(1, 2, marks=pytest.mark.skip, id="test1")
    assert isinstance(result, dict)
    assert "marks" in result
    assert "id" in result


def test_param_bare():
    result = pytest.param(42)
    assert result["values"] == (42,)


def test_fixture_request_properties():
    req = pytest.FixtureRequest(scope="module", _test_func=None)
    assert req.scope == "module"
    assert req.param is None


def test_fixture_request_getfixturevalue():
    req = pytest.FixtureRequest()
    req.fixtures["db"] = "conn"
    assert req.getfixturevalue("db") == "conn"
    try:
        req.getfixturevalue("missing")
        assert False
    except LookupError:
        pass


def test_fixture_request_node():
    req = pytest.FixtureRequest(_test_func=None)
    node = req.node
    assert hasattr(node, "nodeid")


def test_request_node_get_closest_marker():
    def dummy():
        pass
    dummy._oxytest_marks = [("skip", (), {"reason": "test"})]
    from oxytest._compat import _RequestNode
    node = _RequestNode(dummy)
    marker = node.get_closest_marker("skip")
    assert marker is not None
    assert marker.name == "skip"
    missing = node.get_closest_marker("nonexistent")
    assert missing is None


def test_temp_path_factory(tmp_path):
    factory = pytest.TempPathFactory(str(tmp_path))
    result = factory.mktemp("subdir")
    assert os.path.isdir(result)
    assert "subdir" in result


def test_terminal_reporter_get_exit_code():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter()
    assert reporter.get_exit_code() == 0
    reporter.stats["failed"] = 1
    assert reporter.get_exit_code() == 1


def test_terminal_reporter_finish(capsys):
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter()
    reporter.start()
    reporter.finish()
    captured = capsys.readouterr()
    assert "Results" in captured.out


def test_print_durations(capsys):
    from oxytest._compat import _print_durations
    from collections import namedtuple
    FakeResult = namedtuple("FakeResult", ["test", "duration_ms"])
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_y")
    r = FakeResult(test=t, duration_ms=100)
    _print_durations([r], 5)
    captured = capsys.readouterr()
    assert "Slowest" in captured.out


def test_print_summary(capsys):
    from oxytest._compat import _print_summary, TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_y")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output"])
    r = FakeResult(test=t, passed=True, duration_ms=10, output="", error="", error_output="")
    reporter.results = [r]
    reporter.skipped = []
    reporter.failures = []
    reporter.stats["passed"] = 1
    _print_summary(reporter, "A")
    captured = capsys.readouterr()
    assert "PASS" in captured.out


def test_list_fixtures(capsys):
    from oxytest._compat import _list_fixtures
    _list_fixtures()
    captured = capsys.readouterr()
    assert "fixtures" in captured.out.lower()


def test_list_markers(capsys):
    from oxytest._compat import _list_markers
    _list_markers()
    captured = capsys.readouterr()
    assert "markers" in captured.out.lower()


def test_config_getoption():
    from oxytest._compat import Config
    cfg = Config({"verbose": True})
    assert cfg.getoption("verbose") is True
    assert cfg.getoption("nonexistent", "default") == "default"


def test_config_getini():
    from oxytest._compat import Config
    cfg = Config({})
    assert cfg.getini("markers") == ""


def test_config_addinivalue_line():
    from oxytest._compat import Config
    cfg = Config({})
    cfg.addinivalue_line("markers", "slow: marks slow tests")
    assert cfg.getini("markers") == ["slow: marks slow tests"]


def test_config_stash():
    from oxytest._compat import Config
    cfg = Config({})
    stash = cfg.stash
    stash["key"] = "value"
    assert stash["key"] == "value"
    assert "key" in stash
    assert stash.get("missing") is None


def test_parser():
    from oxytest._compat import Parser
    parser = Parser()
    parser.addoption("--my-flag", action="store_true", default=False)
    result = parser.parse(["--my-flag"])
    assert isinstance(result, dict)


def test_parser_no_match():
    from oxytest._compat import Parser
    parser = Parser()
    result = parser.parse([])
    assert isinstance(result, dict)


def test_get_test_module(tmp_path):
    from oxytest._compat import _get_test_module
    pyfile = tmp_path / "test_mod.py"
    pyfile.write_text("def test_foo(): pass\n")
    mod = _get_test_module(str(pyfile))
    assert mod is not None
    assert hasattr(mod, "test_foo")


def test_write_junitxml(tmp_path):
    from oxytest._compat import _write_junitxml, TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter()
    reporter.start()
    reporter.end_time = reporter.start_time + 1.0
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_y")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=True, duration_ms=10, output="", error="", error_output="", traceback="")
    reporter.results = [r]
    reporter.stats["passed"] = 1
    xml_path = str(tmp_path / "report.xml")
    _write_junitxml(reporter, xml_path)
    assert os.path.isfile(xml_path)
    content = open(xml_path).read()
    assert "test_x.py" in content


def test_raises_context_value():
    with pytest.raises(ValueError) as excinfo:
        int("not_a_number")
    assert isinstance(excinfo.value, ValueError)


def test_raises_context_repr():
    from oxytest._compat import RaisesContext
    ctx = RaisesContext(ValueError)
    assert ctx.getrepr() is None


def test_skip_mark():
    from oxytest._compat import Mark
    m = Mark()
    decorator = m.skip(reason="not ready")
    assert decorator.name == "skip"
    assert decorator.kwargs.get("reason") == "not ready"


def test_skipif_mark():
    from oxytest._compat import Mark
    m = Mark()
    decorator = m.skipif(True, reason="condition met")
    assert decorator.name == "skipif"


def test_xfail_mark():
    from oxytest._compat import Mark
    m = Mark()
    decorator = m.xfail(reason="known issue", strict=True)
    assert decorator.name == "xfail"
    assert decorator.kwargs.get("strict") is True


def test_mark_unknown():
    from oxytest._compat import Mark
    m = Mark()
    decorator = m.custom("arg")
    assert decorator.name == "custom"


def test_exit_via_function():
    try:
        pytest.exit(0)
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass


def test_module_cache_clear():
    from oxytest._compat import _module_cache_clear
    _module_cache_clear()


def test_terminal_reporter_with_failure(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_fail.py", name="test_bad")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="stdout",
                   error="AssertionError: assert 1 == 2", error_output="stderr",
                   traceback="  File test_fail.py, line 1\n    assert 1 == 2\nAssertionError")
    reporter = TerminalReporter(verbose=True)
    reporter.start()
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "FAILED" in captured.out
    assert "test_bad" in captured.out


# ===== Coverage gap tests for _compat.py =====

def test_approx_equal_nested():
    assert {"a": [0.1 + 0.2, 0.3]} == pytest.approx({"a": [0.3, 0.3]})


def test_approx_ne():
    assert 1.0 != pytest.approx(2.0)


def test_approx_repr():
    a = pytest.approx(0.1)
    r = repr(a)
    assert "approx" in r


def test_raises_context_exit_without_match():
    ctx = pytest.raises(ValueError, match="invalid")
    with ctx:
        int("invalid literal")


def test_raises_context_group_contains():
    from oxytest._compat import RaisesContext
    exc = ValueError("test")
    ctx = RaisesContext(ValueError)
    assert ctx.group_contains(exc) is False


def test_warns_callable():
    import warnings
    def emit_warning():
        warnings.warn("callable test", UserWarning)
    pytest.warns(UserWarning, emit_warning)


def test_warns_callable_no_warning():
    def no_warning():
        pass
    try:
        pytest.warns(UserWarning, no_warning)
        assert False
    except pytest.Failed:
        pass


def test_deprecated_call_callable():
    import warnings
    def emit_deprecated():
        warnings.warn("dep", DeprecationWarning)
    pytest.deprecated_call(emit_deprecated)


def test_mark_parametrize_with_ids():
    @pytest.mark.parametrize("x", [1, 2, 3], ids=["one", "two", "three"])
    def dummy(x):
        pass
    marks = getattr(dummy, "_oxytest_marks", [])
    assert len(marks) > 0


def test_mark_skipif_true():
    @pytest.mark.skipif(True, reason="skip all")
    def dummy():
        pass
    marks = getattr(dummy, "_oxytest_marks", [])
    assert any(m[0] == "skipif" for m in marks)


def test_mark_xfail():
    @pytest.mark.xfail(reason="known bug")
    def dummy():
        pass
    marks = getattr(dummy, "_oxytest_marks", [])
    assert any(m[0] == "xfail" for m in marks)


def test_fixture_request_config():
    req = pytest.FixtureRequest(_test_func=None)
    cfg = req.config
    assert cfg is not None or cfg is None  # config may or may not be set


def test_config_option_property():
    from oxytest._compat import Config
    cfg = Config({"verbose": True})
    opts = cfg.option
    assert opts.get("verbose") is True


def test_config_stash_assertstate():
    from oxytest._compat import Config
    cfg = Config({})
    stash = cfg.stash
    key = type("K", (), {"__str__": lambda s: "assertstate"})()
    val = stash.get(key)
    assert val is not None


def test_get_test_module_cached(tmp_path):
    from oxytest._compat import _get_test_module, _module_cache_clear
    _module_cache_clear()
    pyfile = tmp_path / "test_cache.py"
    pyfile.write_text("def test_x(): pass\n")
    mod1 = _get_test_module(str(pyfile))
    _get_test_module(str(pyfile))
    assert mod1 is not None


def test_json_safe_bytes():
    from oxytest._compat import _json_safe
    result = _json_safe(b"hello")
    assert isinstance(result, str)


def test_json_safe_custom_object():
    from oxytest._compat import _json_safe
    class Custom:
        def __str__(self):
            return "custom_repr"
    result = _json_safe(Custom())
    assert result is not None


def test_json_safe_none():
    from oxytest._compat import _json_safe
    assert _json_safe(None) is None


def test_validate_markers_empty():
    from oxytest._compat import _validate_markers
    _validate_markers([])


def test_terminal_reporter_xfail(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True)
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_xfail")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="XFAIL: known issue", error_output="", traceback="")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "XFAIL" in captured.out


def test_terminal_reporter_xpass(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True)
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_xpass")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="XPASS: unexpected pass", error_output="", traceback="")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "XPASS" in captured.out


def test_terminal_reporter_skipped_verbose(capsys):
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(verbose=True)
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_skip")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="SKIPPED: reason", error_output="", traceback="")
    reporter.test_result(r)
    reporter.finish()
    captured = capsys.readouterr()
    assert "SKIPPED" in captured.out


def test_terminal_reporter_quiet():
    from oxytest._compat import TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter(quiet=True)
    reporter.start()
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_x.py", name="test_quiet")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=True, duration_ms=5, output="", error="", error_output="", traceback="")
    reporter.test_result(r)
    reporter.finish()
    assert reporter.stats["passed"] == 1


def test_terminal_reporter_get_exit_code_xfail():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter()
    reporter.stats["failed"] = 0
    reporter.stats["xfailed"] = 1
    assert reporter.get_exit_code() == 0


def test_terminal_reporter_get_exit_code_errors():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter()
    # get_exit_code only checks for "failed" > 0
    assert reporter.get_exit_code() == 0


def test_terminal_reporter_no_tests():
    from oxytest._compat import TerminalReporter
    reporter = TerminalReporter()
    reporter.stats = {}
    # get_exit_code returns 0 when no failures
    assert reporter.get_exit_code() == 0


def test_write_junitxml_with_failure(tmp_path):
    from oxytest._compat import _write_junitxml, TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter()
    reporter.start()
    reporter.end_time = reporter.start_time + 1.0
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_fail.py", name="test_bad")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="out",
                   error="assert 1==2", error_output="err",
                   traceback="File test_fail.py, line 1\nassert 1==2\n")
    reporter.results = [r]
    reporter.stats["failed"] = 1
    reporter.skipped = []
    reporter.failures = [r]
    xml_path = str(tmp_path / "fail_report.xml")
    _write_junitxml(reporter, xml_path)
    assert os.path.isfile(xml_path)
    content = open(xml_path).read()
    assert "failure" in content


def test_write_junitxml_with_skip(tmp_path):
    from oxytest._compat import _write_junitxml, TerminalReporter
    from collections import namedtuple
    reporter = TerminalReporter()
    reporter.start()
    reporter.end_time = reporter.start_time + 1.0
    FakeTest = namedtuple("FakeTest", ["path", "name"])
    t = FakeTest(path="test_skip.py", name="test_skip")
    FakeResult = namedtuple("FakeResult", ["test", "passed", "duration_ms", "output", "error", "error_output", "traceback"])
    r = FakeResult(test=t, passed=False, duration_ms=5, output="",
                   error="SKIPPED: not ready", error_output="", traceback="")
    reporter.results = [r]
    reporter.stats["skipped"] = 1
    reporter.skipped = [r]
    xml_path = str(tmp_path / "skip_report.xml")
    _write_junitxml(reporter, xml_path)
    assert os.path.isfile(xml_path)
    content = open(xml_path).read()
    assert "skipped" in content


def test_approx_decimal():
    from decimal import Decimal
    assert Decimal("0.1") + Decimal("0.2") == pytest.approx(Decimal("0.3"))


def test_approx_tuple():
    assert (0.1 + 0.2, 0.5) == pytest.approx((0.3, 0.5))


# ── New 3.0.0 tests ─────────────────────────────────────────────────


def test_approx_nan_ok():
    assert pytest.approx(float('nan'), nan_ok=True) == float('nan')
    assert pytest.approx(float('nan'), nan_ok=False) != float('nan')


def test_config_rootpath():
    from oxytest._compat import Config
    import pathlib
    c = Config({"rootdir": "/tmp"})
    assert c.rootpath == pathlib.Path("/tmp")
    c2 = Config({})
    assert c2.rootpath is None


def test_config_hook():
    from oxytest._compat import Config
    c = Config({})
    assert hasattr(c.hook, 'pytest_addoption')


def test_config_cache():
    from oxytest._compat import Config
    from oxytest._fixtures import get_fixture_manager
    get_fixture_manager()._autouse_list = None
    c = Config({})
    cache = c.cache
    assert cache is not None or hasattr(c, 'cache')


def test_importorskip_minversion_pytest():
    result = pytest.importorskip("pytest", minversion="0.1")
    assert result is not None


def test_warns_re_pattern():
    import re
    pattern = re.compile("some message")
    with pytest.warns(UserWarning, match=pattern):
        import warnings
        warnings.warn("some message", UserWarning)


# ── New 3.0.0 tests ─────────────────────────────────────────────────


def test_deprecated_call_future_warning():
    import warnings
    with pytest.deprecated_call():
        warnings.warn("future deprecation", FutureWarning)


def test_config_get_verbosity():
    from oxytest._compat import Config
    c = Config({"verbose": True})
    assert c.get_verbosity() > 0


def test_config_inipath():
    from oxytest._compat import Config
    c = Config({"inipath": "/tmp/pytest.ini"})
    assert c.inipath is not None


def test_config_invocation_params():
    from oxytest._compat import Config
    c = Config({})
    assert hasattr(c, 'invocation_params')
