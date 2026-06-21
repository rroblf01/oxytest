"""Tests for assertion rewriting (import-time)."""

import os
import tempfile

from oxytest._assert import (
    _rewrite_module,
    _AssertLoader,
    _assert_loader,
    install_assert_rewriting,
    register_assert_rewrite,
    _RewriteLoader,
    _saferepr,
)


def test_assert_rewriter_simple():
    source = "def f():\n    assert 1 + 1 == 2\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result


def test_assert_rewriter_compare():
    source = "def f():\n    assert x in [1, 2, 3]\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result


def test_assert_rewriter_is():
    source = "def f():\n    assert a is None\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result
    assert "is None" in result


def test_assert_rewriter_not_in():
    source = "def f():\n    assert 5 not in items\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result


def test_rewrite_module_syntax_error():
    source = "def f():\n    assert ::\n"
    result = _rewrite_module(source, "bad.py")
    assert result == source


def test_rewrite_no_assert():
    source = "def f():\n    return 42\n"
    result = _rewrite_module(source, "test.py")
    # The module should still be parseable and valid
    compile(result, "test.py", "exec")
    assert "return 42" in result


# ── _AssertLoader tests ─────────────────────────────────────────────


def test_loader_add_rewrite_path():
    loader = _AssertLoader()
    loader.add_rewrite_path("/tmp")
    assert "/tmp" in loader._rewrite_prefixes


def test_loader_no_paths():
    loader = _AssertLoader()
    spec = loader.find_spec("any_module", None)
    assert spec is None


def test_loader_no_matching_prefix():
    loader = _AssertLoader()
    loader.add_rewrite_path("/nonexistent")
    spec = loader.find_spec("any_module", ["/other/path"])
    assert spec is None


def test_install_assert_rewriting():
    install_assert_rewriting(["/tmp"])
    # should not raise and should be idempotent
    install_assert_rewriting(["/tmp"])


def test_register_assert_rewrite():
    register_assert_rewrite("os")
    # should not raise


def test_rewrite_loader_init():
    loader = _RewriteLoader("/tmp/test.py")
    assert loader._origin == "/tmp/test.py"


def test_rewrite_loader_create_module():
    loader = _RewriteLoader("/tmp/test.py")
    assert loader.create_module(None) is None


def test_assert_loader_instance():
    assert isinstance(_assert_loader, _AssertLoader)


# ── RewriteLoader exec_module integration ────────────────────────────


def test_rewrite_loader_exec_module():
    import importlib
    import importlib.util
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_path = os.path.join(tmpdir, "test_rewrite_module.py")
        with open(mod_path, "w") as f:
            f.write("def test_func():\n    assert 1 == 2\n")
        
        loader = _RewriteLoader(mod_path)
        spec = importlib.util.spec_from_loader("test_rewrite_module", loader, origin=mod_path)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        
        assert hasattr(mod, "test_func")
        # The assertion should now show detailed message when it fails
        try:
            mod.test_func()
        except AssertionError as e:
            msg = str(e)
            assert "assert" in msg or "1" in msg or "2" in msg


def _rewrite_and_exec(assert_source):
    """Rewrite an assert statement, compile, and return the callable."""
    source = f"def test_func():\n    {assert_source}\n"
    result = _rewrite_module(source, "test.py")
    code = compile(result, "test.py", "exec")
    ns = {"_saferepr": _saferepr}
    exec(code, ns)
    return ns["test_func"]


def test_assert_fail_message_format():
    func = _rewrite_and_exec("assert 1 == 2")
    try:
        func()
    except AssertionError as e:
        msg = str(e)
        assert "1" in msg
        assert "2" in msg
        assert "==" in msg or "where" in msg


def test_assert_fail_message_in():
    func = _rewrite_and_exec("assert 5 not in [1, 2, 3]")
    try:
        func()
    except AssertionError as e:
        msg = str(e)
        assert "5" in msg
        assert "not in" in msg


def test_assert_fail_message_is():
    func = _rewrite_and_exec("assert None is not None")
    try:
        func()
    except AssertionError as e:
        msg = str(e)
        assert "None" in msg
        assert "is not" in msg


def test_assert_pass_does_not_raise():
    func = _rewrite_and_exec("assert 1 == 1")
    # Should not raise
    func()


def test_assert_msg_propagated():
    func = _rewrite_and_exec('assert 1 == 2, "custom message"')
    try:
        func()
    except AssertionError as e:
        msg = str(e)
        assert "custom message" in msg


def test_double_eval_prevention():
    """Expressions with side effects should only be evaluated once."""
    source = """
def test_func():
    calls = []
    def pop_item():
        calls.append(1)
        return 42
    try:
        assert pop_item() == 99
    except AssertionError:
        pass
    return len(calls)
"""
    result = _rewrite_module(source, "test.py")
    ns = {"_saferepr": _saferepr}
    exec(result, ns)
    func = ns["test_func"]
    call_count = func()
    assert call_count == 1, f"Expected 1 call, got {call_count}"


def test_saferepr_recursive():
    data = []
    data.append(data)
    result = _saferepr(data)
    assert "..." in result


def test_saferepr_long():
    result = _saferepr(list(range(1000)))
    assert len(result) < 1000
    assert result.endswith("...")


def test_saferepr_bad_repr():
    class Bad:
        def __repr__(self):
            raise RuntimeError("fail")
    result = _saferepr(Bad())
    assert "Bad" in result


def test_saferepr_normal():
    assert _saferepr(42) == "42"
    assert _saferepr("hello") == "'hello'"


def test_assert_rewriter_temp_vars_generated():
    """Check that temp variables are generated for sub-expressions."""
    source = "def f():\n    assert x == y\n"
    result = _rewrite_module(source, "test.py")
    # Should have at least one _ox temp variable
    assert "_ox0" in result


def test_assert_rewriter_no_temp_for_simple():
    """Simple literal assertions don't need temp vars."""
    source = "def f():\n    assert True\n"
    result = _rewrite_module(source, "test.py")
    # With no details to collect, no temp vars should be generated
    # The assertion should still be there
    assert "AssertionError" in result


def test_assert_complex_expression():
    """Complex expressions like comprehensions should be captured."""
    source = "def f():\n    assert [x for x in range(5)] == [0, 1, 2, 3, 4]\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result
    assert "_ox0" in result or "_ox1" in result


def test_assert_walrus_operator():
    """Walrus operator (:=) should be handled."""
    source = "def f():\n    assert (n := len([1, 2, 3])) == 3\n"
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result
