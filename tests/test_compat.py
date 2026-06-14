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
    try:
        with pytest.raises(TypeError):
            int("not_a_number")
    except TypeError:
        pass  # The ValueError propagates


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
    assert __version__ == "0.1.0"


def test_test_item_repr():
    tests = oxytest.discover_tests(os.path.join(os.path.dirname(__file__), "sample_tests"))
    if tests:
        assert "test_" in repr(tests[0]) or "::" in repr(tests[0])


def test_exit_via_main():
    result = pytest.main(["-v", os.path.join(os.path.dirname(__file__), "sample_tests")])
    assert isinstance(result, int)
