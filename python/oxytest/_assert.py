import ast
import sys
import os
import types


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
            for expr in [node.left] + node.ops:
                if isinstance(expr, ast.expr):
                    details.append(expr)


def _rewrite_module(source, filename):
    try:
        tree = ast.parse(source, filename=filename)
        rewriter = _AssertRewriter()
        new_tree = rewriter.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)
    except SyntaxError:
        return source


class _AssertLoader:
    def __init__(self):
        self._installed = False
        self._inject_code = (
            "from oxytest._assert import _oxytest_assert\n"
        )

    def install(self):
        if self._installed:
            return
        self._installed = True
        sys.meta_path.insert(0, self)

    def find_spec(self, fullname, path, target=None):
        return None


_assert_loader = _AssertLoader()
