import ast
import textwrap
import importlib

from oxytest._assert import (
    _format_assert_detail,
    _AssertRewriter,
    _rewrite_module,
    _AssertLoader,
    _assert_loader,
)


def test_format_assert_detail():
    assert _format_assert_detail(42) == "42"
    assert _format_assert_detail("hello") == "hello"


def test_rewriter_simple_assert():
    source = "def f():\n    assert 1 + 1 == 2\n"
    tree = ast.parse(source)
    rewriter = _AssertRewriter()
    new_tree = rewriter.visit(tree)
    result = ast.unparse(new_tree)
    assert "AssertionError" in result
    assert "assert" in result  # the source string
    assert "repr" in result


def test_rewriter_multiline():
    source = "def f():\n    assert x in [1, 2, 3]\n"
    tree = ast.parse(source)
    rewriter = _AssertRewriter()
    new_tree = rewriter.visit(tree)
    result = ast.unparse(new_tree)
    assert "AssertionError" in result
    assert "x in [1, 2, 3]" in result


def test_rewriter_is():
    source = "def f():\n    assert a is None\n"
    tree = ast.parse(source)
    rewriter = _AssertRewriter()
    new_tree = rewriter.visit(tree)
    result = ast.unparse(new_tree)
    assert "AssertionError" in result
    assert "is None" in result


def test_rewriter_not_in():
    source = "def f():\n    assert 5 not in items\n"
    tree = ast.parse(source)
    rewriter = _AssertRewriter()
    new_tree = rewriter.visit(tree)
    result = ast.unparse(new_tree)
    assert "AssertionError" in result
    assert "5 not in items" in result


def test_rewrite_module_basic():
    source = textwrap.dedent("""\
        def test_foo():
            assert 1 == 2
    """)
    result = _rewrite_module(source, "test.py")
    assert "AssertionError" in result
    assert "assert" in result


def test_rewrite_module_syntax_error():
    source = "def f():\n    assert ::\n"
    result = _rewrite_module(source, "bad.py")
    assert result == source


def test_join_constants_single():
    rewriter = _AssertRewriter()
    const = ast.Constant(value="hello")
    result = rewriter._join_constants([const])
    assert result is const


def test_join_constants_multiple():
    rewriter = _AssertRewriter()
    parts = [ast.Constant(value="a"), ast.Constant(value="b")]
    result = rewriter._join_constants(parts)
    assert isinstance(result, ast.BinOp)
    assert isinstance(result.op, ast.Add)


def test_wrap_fstr():
    rewriter = _AssertRewriter()
    expr = ast.Name(id="x", ctx=ast.Load())
    result = rewriter._wrap_fstr(expr)
    assert isinstance(result, ast.Call)
    assert isinstance(result.func, ast.Name)
    assert result.func.id == "repr"
    assert len(result.args) == 1


def test_collect_details_compare():
    rewriter = _AssertRewriter()
    details = []
    compare = ast.Compare(
        left=ast.Name(id="a", ctx=ast.Load()),
        ops=[ast.Eq()],
        comparators=[ast.Name(id="b", ctx=ast.Load())],
    )
    rewriter._collect_details(compare, details)
    assert len(details) == 2


def test_assert_loader_install():
    loader = _AssertLoader()
    assert not loader._installed
    loader.install()
    assert loader._installed
    loader.install()
    assert loader._installed


def test_assert_loader_find_spec():
    loader = _AssertLoader()
    spec = loader.find_spec("any_module", None)
    assert spec is None


def test_assert_loader_inject_code():
    loader = _AssertLoader()
    assert "from oxytest._assert import _oxytest_assert" in loader._inject_code


def test_global_loader_instance():
    assert isinstance(_assert_loader, _AssertLoader)


# ===== Coverage gap tests for _assert.py =====


def test_collect_details_call():
    rewriter = _AssertRewriter()
    details = []
    call = ast.Call(
        func=ast.Name(id="foo", ctx=ast.Load()),
        args=[ast.Constant(value=1)],
        keywords=[],
    )
    rewriter._collect_details(call, details)
    assert len(details) == 1


def test_collect_details_boolop():
    rewriter = _AssertRewriter()
    details = []
    boolop = ast.BoolOp(
        op=ast.And(),
        values=[
            ast.Name(id="a", ctx=ast.Load()),
            ast.Name(id="b", ctx=ast.Load()),
        ],
    )
    rewriter._collect_details(boolop, details)
    assert len(details) == 2


def test_collect_details_unaryop():
    rewriter = _AssertRewriter()
    details = []
    unary = ast.UnaryOp(op=ast.Not(), operand=ast.Name(id="x", ctx=ast.Load()))
    rewriter._collect_details(unary, details)
    assert len(details) == 1


def test_collect_details_binop():
    rewriter = _AssertRewriter()
    details = []
    binop = ast.BinOp(
        left=ast.Name(id="a", ctx=ast.Load()),
        op=ast.Add(),
        right=ast.Name(id="b", ctx=ast.Load()),
    )
    rewriter._collect_details(binop, details)
    assert len(details) == 2


def test_collect_details_name():
    rewriter = _AssertRewriter()
    details = []
    name = ast.Name(id="x", ctx=ast.Load())
    rewriter._collect_details(name, details)
    assert len(details) == 1


def test_collect_details_constant():
    rewriter = _AssertRewriter()
    details = []
    const = ast.Constant(value=42)
    rewriter._collect_details(const, details)
    assert len(details) == 1


def test_rewrite_module_none_source():
    loader = _AssertLoader()
    spec = importlib.machinery.ModuleSpec("test_mod", None)
    loader.rewrite_module("test_mod", spec, source=None)
