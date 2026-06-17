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
