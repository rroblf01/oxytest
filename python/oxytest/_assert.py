import ast
import sys
import os
import importlib.abc
import importlib.util


def _format_assert_detail(test_val):
    return str(test_val)


_BINOP_FORMATS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}


class _AssertRewriter(ast.NodeTransformer):
    def visit_Assert(self, node):
        details = []
        self._collect_details(node.test, details)
        source = f"assert {ast.unparse(node.test)}"
        msg_parts = [ast.Constant(value=source)]
        for expr in details:
            msg_parts.append(ast.Constant(value="\n  "))
            msg_parts.append(self._wrap_fstr(expr))
        joined = self._join_constants(msg_parts)
        raise_call = ast.Raise(
            exc=ast.Call(
                func=ast.Name(id="AssertionError", ctx=ast.Load()),
                args=[joined],
                keywords=[],
            ),
            cause=None,
        )
        if_stmt = ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=node.test),
            body=[raise_call],
            orelse=[],
        )
        return if_stmt

    def _join_constants(self, parts):
        if len(parts) == 1:
            return parts[0]
        result = parts[0]
        for p in parts[1:]:
            result = ast.BinOp(left=result, op=ast.Add(), right=p)
        return result

    def _wrap_fstr(self, expr):
        return ast.Call(
            func=ast.Name(id="repr", ctx=ast.Load()),
            args=[expr],
            keywords=[],
        )

    def _collect_details(self, node, details):
        if isinstance(node, ast.Compare):
            for expr in [node.left] + node.comparators:
                if isinstance(expr, ast.expr):
                    details.append(expr)
        elif isinstance(node, ast.Call):
            details.append(node)
        elif isinstance(node, ast.BoolOp):
            for val in node.values:
                self._collect_details(val, details)
        elif isinstance(node, ast.UnaryOp):
            self._collect_details(node.operand, details)
        elif isinstance(node, ast.BinOp):
            details.append(node.left)
            details.append(node.right)
        elif isinstance(node, ast.Name) or isinstance(node, ast.Constant):
            details.append(node)


def _rewrite_module(source, filename):
    try:
        tree = ast.parse(source, filename=filename)
        rewriter = _AssertRewriter()
        new_tree = rewriter.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)
    except SyntaxError:
        return source


class _RewriteLoader(importlib.abc.Loader):
    """Custom loader that rewrites assert statements before compilation."""

    def __init__(self, origin):
        self._origin = origin

    def create_module(self, spec):
        return None  # Use default module creation

    def exec_module(self, module):
        filename = self._origin
        if not filename or not os.path.isfile(filename):
            raise ImportError(f"cannot load {module.__name__} from {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            source = f.read()
        if "assert " in source or "assert(" in source:
            rewritten = _rewrite_module(source, filename)
        else:
            rewritten = source
        code = compile(rewritten, filename, "exec", dont_inherit=True)
        exec(code, module.__dict__)


class _AssertLoader(importlib.abc.MetaPathFinder):
    """Import hook that rewrites assert statements in test files."""

    def __init__(self):
        self._rewrite_prefixes = set()

    def add_rewrite_path(self, path):
        """Register a directory whose modules should have asserts rewritten."""
        abs_path = os.path.abspath(path)
        self._rewrite_prefixes.add(abs_path)

    def find_spec(self, fullname, path, target=None):
        if not self._rewrite_prefixes:
            return None
        if not path:
            return None
        for entry in path:
            norm_entry = os.path.abspath(entry) if entry else ""
            for prefix in self._rewrite_prefixes:
                if norm_entry.startswith(prefix):
                    # Manually construct the spec without calling find_spec (avoids recursion)
                    origin = None
                    is_pkg = False
                    base_path = os.path.join(norm_entry, fullname.replace(".", os.sep))
                    py_path = base_path + ".py"
                    init_path = os.path.join(base_path, "__init__.py")
                    if os.path.isfile(init_path):
                        origin = init_path
                        is_pkg = True
                    elif os.path.isfile(py_path):
                        origin = py_path
                    if origin:
                        return importlib.util.spec_from_loader(
                            fullname,
                            _RewriteLoader(origin),
                            origin=origin,
                            is_package=is_pkg,
                        )
        return None


_assert_loader = _AssertLoader()


def install_assert_rewriting(rewrite_paths):
    """Install the assert rewriting hook for the given paths."""
    for p in rewrite_paths:
        _assert_loader.add_rewrite_path(p)
    if not any(isinstance(x, _AssertLoader) for x in sys.meta_path):
        sys.meta_path.insert(0, _assert_loader)


def register_assert_rewrite(*names):
    """Register modules for assert rewriting.
    Public API matching pytest.register_assert_rewrite().
    Accepts module names (strings) which are converted to filesystem paths
    for the rewriting hook."""
    for name in names:
        try:
            spec = importlib.util.find_spec(name)
        except (ModuleNotFoundError, ValueError):
            spec = None
        if spec and spec.origin:
            _assert_loader.add_rewrite_path(os.path.dirname(spec.origin))
    if not any(isinstance(x, _AssertLoader) for x in sys.meta_path):
        sys.meta_path.insert(0, _assert_loader)
