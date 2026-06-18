import ast
import doctest
import os
import sys


_DOCTEST_PREFIX = "doctest."


def _has_doctest_docstring(node):
    """Check if an AST node has a docstring containing '>>>'."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        return False
    docstring = ast.get_docstring(node)
    if docstring is None:
        return False
    return ">>>" in docstring


def _collect_doctests_from_node(node, module_name: str, parent_name: str, results: list):
    """Recursively collect doctest locations from AST nodes."""
    if _has_doctest_docstring(node):
        name = getattr(node, 'name', '')
        full_name = f"{module_name}.{name}" if name else module_name
        lineno = getattr(node, 'lineno', 1)
        results.append((full_name, lineno))
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            child_name = getattr(child, 'name', '')
            _collect_doctests_from_node(child, module_name, child_name, results)


def collect_module_doctests(filepath: str) -> list[tuple[str, int]]:
    """Scan a Python file for functions/classes with doctest examples.
    Returns list of (fully_qualified_name, lineno) tuples."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        if ">>>" not in source:
            return []
        tree = ast.parse(source, filename=filepath)
        results = []
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        _collect_doctests_from_node(tree, module_name, "", results)
        return results
    except SyntaxError:
        return []


def make_doctest_items(filepath: str, module) -> list:
    """Create TestItem entries for doctests found in a module file."""
    from oxytest._core import TestItem
    doctests = collect_module_doctests(filepath)
    items = []
    for func_name, lineno in doctests:
        item = TestItem()
        item.path = filepath
        item.name = _DOCTEST_PREFIX + func_name
        item.line_no = lineno
        item.args_json = ""
        items.append(item)
    return items


def execute_doctest(filepath: str, name: str):
    """Execute a single doctest from a Python file.
    
    The function/class named by `name` (with 'doctest.' prefix) is found
    in the module and its docstring examples are run via doctest."""
    import importlib.util
    from oxytest._compat import SkipTest

    func_name = name
    if func_name.startswith(_DOCTEST_PREFIX):
        func_name = func_name[len(_DOCTEST_PREFIX):]

    # Build module name from filepath
    rel_path = os.path.relpath(filepath)
    module_name = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py").lstrip(".")

    # Import or get cached module
    if module_name in sys.modules:
        mod = sys.modules[module_name]
    else:
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load {filepath}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

    # Find the object by name (walk dotted path within module)
    obj = mod
    # func_name is like "module_name.func_name" or just "func_name"
    # We skip the module part (first part) if it matches the module name
    name_parts = func_name.split(".")
    start_idx = 0
    if name_parts and name_parts[0] == module_name.split(".")[-1]:
        start_idx = 1
    for part in name_parts[start_idx:]:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            raise LookupError(f"Could not find {'.'.join(name_parts[start_idx:])} in {module_name}")

    docstring = getattr(obj, "__doc__", None)
    if not docstring or ">>>" not in docstring:
        raise SkipTest(f"No doctests in {func_name}")

    # Use Python's doctest module to run examples in the docstring
    import io
    from contextlib import redirect_stdout, redirect_stderr

    finder = doctest.DocTestFinder()
    runner = doctest.DocTestRunner(verbose=False)

    try:
        test = list(finder.find(obj, name=func_name, module=mod))
    except Exception as e:
        raise Exception(f"DOCTEST_ERROR: failed to find doctests in {func_name}: {e}")

    if not test:
        raise SkipTest(f"No doctest examples found in {func_name}")

    failures = 0
    for t in test:
        if not t.examples:
            continue
        f, _ = runner.run(t)
        failures += f

    if failures:
        # Collect output from the runner
        output_buf = io.StringIO()
        with redirect_stdout(output_buf), redirect_stderr(output_buf):
            runner.summarize()
        raise AssertionError(f"DOCTEST_FAIL:{failures} doctest(s) failed in {func_name}\n{output_buf.getvalue()}")
