import os
import re
import sys
import math
import time
import json
import xml.etree.ElementTree as ET
import traceback as tb_module
from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from oxytest._core import discover_tests, run_tests, run_tests_sequential, TestItem, TestResult


Exit = SystemExit


class PytestError(Exception):
    pass


class UsageError(PytestError):
    pass


class SkipTest(Exception):
    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(reason)


class Failed(Exception):
    pass


class ApproxDecimal:
    def __init__(self, expected, rel=None, abs=None, nan_ok=False):
        self.expected = expected
        self.rel = rel if rel is not None else 1e-6
        self.abs = abs if abs is not None else 1e-12
        self.nan_ok = nan_ok

    def __repr__(self):
        return f"approx({self.expected!r}, rel={self.rel}, abs={self.abs})"

    def _eq(self, actual):
        if actual is None or self.expected is None:
            return actual == self.expected
        if isinstance(self.expected, (int, float)):
            diff = abs(actual - self.expected)
            abs_tol = max(self.abs, self.rel * max(abs(actual), abs(self.expected)))
            return diff <= abs_tol
        if isinstance(self.expected, (list, tuple)):
            if len(actual) != len(self.expected):
                return False
            return all(
                ApproxDecimal(e, rel=self.rel, abs=self.abs, nan_ok=self.nan_ok)._eq(a)
                for a, e in zip(actual, self.expected)
            )
        if isinstance(self.expected, dict):
            if set(actual.keys()) != set(self.expected.keys()):
                return False
            return all(
                ApproxDecimal(self.expected[k], rel=self.rel, abs=self.abs, nan_ok=self.nan_ok)._eq(actual[k])
                for k in self.expected
            )
        return actual == self.expected


def approx(expected, rel=None, abs=None, nan_ok=False):
    return ApproxDecimal(expected, rel=rel, abs=abs, nan_ok=nan_ok)


class RaisesContext:
    def __init__(
        self,
        expected_exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]],
        match: Optional[str] = None,
    ):
        self.expected_exception = expected_exception
        self.match = match
        self.excinfo = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise Failed(
                f"DID NOT RAISE {self.expected_exception}"
            )
        if not issubclass(exc_type, self.expected_exception):
            return False
        if self.match is not None and exc_val is not None:
            if not re.search(self.match, str(exc_val)):
                raise Failed(
                    f"Exception pattern {self.match!r} does not match {exc_val!r}"
                )
        self.excinfo = (exc_type, exc_val, exc_tb)
        return True


def raises(
    expected_exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]],
    *args,
    match: Optional[str] = None,
) -> Union[RaisesContext, ContextManager]:
    if args:
        func = args[0]
        try:
            func(*args[1:])
        except expected_exception:
            return None
        raise Failed(f"DID NOT RAISE {expected_exception}")
    return RaisesContext(expected_exception, match=match)


def skip(reason: str = "") -> None:
    raise SkipTest(reason)


def fail(reason: str = "") -> None:
    raise Failed(reason)


def exit(exit_code: int = 0) -> None:
    raise SystemExit(exit_code)


def set_trace():
    import pdb
    pdb.set_trace()


def importorskip(modname: str, minversion: Optional[str] = None, reason: Optional[str] = None):
    try:
        mod = __import__(modname)
        if minversion:
            import importlib.metadata
            version = importlib.metadata.version(modname)
            if tuple(map(int, version.split(".")[:2])) < tuple(map(int, minversion.split(".")[:2])):
                raise SkipTest(f"module {modname} version {version} < {minversion}")
        return mod
    except ImportError:
        raise SkipTest(reason or f"could not import {modname}")


class MarkDecorator:
    def __init__(self, name: str, args: tuple = (), kwargs: Optional[dict] = None):
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}

    def __call__(self, func):
        if not hasattr(func, "_oxytest_marks"):
            func._oxytest_marks = []
        func._oxytest_marks.append((self.name, self.args, self.kwargs))
        return func


class Mark:
    def parametrize(self, argnames, argvalues, *args, **kwargs):
        return MarkDecorator("parametrize", (argnames, argvalues) + args, kwargs)

    def skip(self, reason: Optional[str] = None):
        return MarkDecorator("skip", (), {"reason": reason})

    def skipif(self, condition, reason: Optional[str] = None):
        return MarkDecorator("skipif", (condition,), {"reason": reason})

    def xfail(self, condition=None, reason: Optional[str] = None, raises=None, strict=None):
        return MarkDecorator("xfail", (), {"condition": condition, "reason": reason, "raises": raises, "strict": strict})

    def usefixtures(self, *fixture_names):
        return MarkDecorator("usefixtures", fixture_names)

    def filterwarnings(self, action: str):
        return MarkDecorator("filterwarnings", (action,))


mark = Mark()


def param(*values, marks=None, id: Optional[str] = None):
    result = {"values": values}
    if marks:
        result["marks"] = marks if isinstance(marks, (list, tuple)) else [marks]
    if id is not None:
        result["id"] = id
    return result


class FixtureRequest:
    def __init__(self, scope: str = "function"):
        self.scope = scope
        self.fixtures: Dict[str, Any] = {}
        self._fixturedefs: Dict[str, Any] = {}

    def getfixturevalue(self, name: str) -> Any:
        if name in self.fixtures:
            return self.fixtures[name]
        raise LookupError(f"Fixture {name!r} not found")


class TempPathFactory:
    def __init__(self, base: str):
        self._base = base

    def mktemp(self, basename: str) -> str:
        import tempfile
        path = os.path.join(self._base, basename)
        os.makedirs(path, exist_ok=True)
        return path


def fixture(
    scope: str = "function",
    params: Optional[list] = None,
    autouse: bool = False,
    name: Optional[str] = None,
):
    def decorator(func):
        func._oxytest_fixture = {
            "scope": scope,
            "params": params,
            "autouse": autouse,
            "name": name or func.__name__,
        }
        return func
    return decorator


def _get_fixtures(func):
    fixtures = []
    if hasattr(func, "_oxytest_fixture"):
        fixtures.append(func._oxytest_fixture)
    if hasattr(func, "_oxytest_marks"):
        for mark_name, args, kwargs in func._oxytest_marks:
            if mark_name == "usefixtures":
                fixtures.extend(args)
    return fixtures


def _should_skip(func):
    if hasattr(func, "_oxytest_marks"):
        for mark_name, args, kwargs in func._oxytest_marks:
            if mark_name == "skip":
                return kwargs.get("reason", "skipped")
            if mark_name == "skipif":
                if args and args[0]:
                    return kwargs.get("reason", "condition true")
    return None


def _is_xfail(func):
    if hasattr(func, "_oxytest_marks"):
        for mark_name, args, kwargs in func._oxytest_marks:
            if mark_name == "xfail":
                condition = kwargs.get("condition")
                if condition is None or condition:
                    return kwargs.get("reason", "")
    return None


def _get_parametrize(func):
    if hasattr(func, "_oxytest_marks"):
        for mark_name, args, kwargs in func._oxytest_marks:
            if mark_name == "parametrize" and len(args) >= 2:
                yield args[0], args[1]


class TestReport:
    def __init__(self, test: TestItem, passed: bool, duration_ms: u64, output: str, error: Optional[str]):
        self.nodeid = f"{test.path}::{test.name}"
        self.passed = passed
        self.failed = not passed
        self.duration = duration_ms / 1000.0
        self.duration_ms: int = duration_ms
        self.output = output
        self.error = error
        self.test = test

    @property
    def when(self) -> str:
        return "call"


class TerminalReporter:
    def __init__(self, verbose: bool = False, quiet: bool = False, tb_style: str = "short"):
        self.verbose = verbose
        self.quiet = quiet
        self.tb_style = tb_style
        self.stats = defaultdict(int)
        self.failures: List[TestResult] = []
        self.errors: List[TestResult] = []
        self.skipped: List[TestResult] = []
        self.start_time = 0.0
        self.end_time = 0.0

    def start(self):
        self.start_time = time.time()
        if not self.quiet:
            print("=" * 60)
            print(f"oxytest: running tests")
            print("=" * 60)

    def test_result(self, result: TestResult):
        if result.passed:
            self.stats["passed"] += 1
        else:
            if result.error == "SKIPPED":
                self.stats["skipped"] += 1
                self.skipped.append(result)
            else:
                self.stats["failed"] += 1
                self.failures.append(result)

        if self.verbose:
            status = "PASSED" if result.passed else "FAILED"
            test_name = f"{result.test.path}::{result.test.name}"
            print(f"{status:>7} {test_name}  [{result.duration_ms}ms]")
        elif not self.quiet:
            if result.passed:
                print(".", end="", flush=True)
            else:
                print("F", end="", flush=True)

    def finish(self):
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        total = sum(self.stats.values())

        if not self.quiet:
            print()

        if self.failures:
            print()
            print("=" * 60)
            print("FAILURES")
            print("=" * 60)
            for result in self.failures:
                test_name = f"{result.test.path}::{result.test.name}"
                print(f"\n--- {test_name} ---")
                if result.output:
                    print(result.output)
                if result.error_output:
                    print(result.error_output, file=sys.stderr)
                if result.traceback:
                    lines = result.traceback.split("\n")
                    if self.tb_style == "short":
                        relevant = [l for l in lines if "raise" in l or "assert" in l or "Error:" in l or "Exception:" in l]
                        if relevant:
                            print("\n".join(relevant[-5:]))
                        else:
                            print("\n".join(lines[-8:]))
                    elif self.tb_style == "no":
                        if result.error:
                            print(result.error)
                    else:
                        print(result.traceback)

        print()
        print("=" * 60)
        print(f"Results: {total} tests")
        for key, count in sorted(self.stats.items()):
            print(f"  {key}: {count}")
        print(f"Time: {total_time:.2f}s")
        print("=" * 60)

    def get_exit_code(self) -> int:
        if self.stats.get("failed", 0) > 0:
            return 1
        return 0


def _parse_args(args: List[str]) -> dict:
    parsed = {
        "paths": [],
        "verbose": False,
        "quiet": False,
        "exitfirst": False,
        "keyword": None,
        "tb_style": "short",
        "num_workers": None,
        "junitxml": None,
        "nocapture": False,
        "maxfail": None,
        "coverage": False,
        "version": False,
    }

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-v", "--verbose"):
            parsed["verbose"] = True
        elif arg in ("-q", "--quiet"):
            parsed["quiet"] = True
        elif arg in ("-x", "--exitfirst"):
            parsed["exitfirst"] = True
        elif arg == "-k" and i + 1 < len(args):
            i += 1
            parsed["keyword"] = args[i]
        elif arg == "--tb" and i + 1 < len(args):
            i += 1
            parsed["tb_style"] = args[i]
        elif arg == "-n" and i + 1 < len(args):
            i += 1
            parsed["num_workers"] = int(args[i])
        elif arg == "--junitxml" and i + 1 < len(args):
            i += 1
            parsed["junitxml"] = args[i]
        elif arg == "-s":
            parsed["nocapture"] = True
        elif arg == "--maxfail" and i + 1 < len(args):
            i += 1
            parsed["maxfail"] = int(args[i])
        elif arg == "--coverage":
            parsed["coverage"] = True
        elif arg in ("--version",):
            parsed["version"] = True
        elif arg in ("-h", "--help"):
            parsed["help"] = True
        elif arg.startswith("-"):
            pass  # ignore unknown flags
        else:
            parsed["paths"].append(arg)
        i += 1

    if not parsed["paths"]:
        parsed["paths"] = ["."]

    return parsed


def _run_tests(
    paths: List[str],
    verbose: bool = False,
    quiet: bool = False,
    exitfirst: bool = False,
    keyword: Optional[str] = None,
    tb_style: str = "short",
    num_workers: Optional[int] = None,
    junitxml: Optional[str] = None,
    nocapture: bool = False,
    maxfail: Optional[int] = None,
) -> int:
    py = None  # GIL handled by Rust

    all_tests = []
    for path in paths:
        tests = discover_tests(path, keyword)
        all_tests.extend(tests)

    if not all_tests:
        print("No tests found")
        return 0

    reporter = TerminalReporter(verbose=verbose, quiet=quiet, tb_style=tb_style)
    reporter.start()

    if verbose:
        print(f"\nDiscovered {len(all_tests)} test(s)")
        print()

    if num_workers is None or num_workers == 1:
        results = run_tests_sequential(all_tests)
    else:
        results = run_tests(all_tests, num_workers)

    had_failure = False
    for result in results:
        reporter.test_result(result)
        if not result.passed and exitfirst:
            break
        if maxfail and reporter.stats.get("failed", 0) >= maxfail:
            break

    reporter.finish()

    if junitxml:
        _write_junitxml(reporter, junitxml)

    return reporter.get_exit_code()


def _write_junitxml(reporter: TerminalReporter, path: str):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    suite.set("name", "oxytest")
    suite.set("tests", str(sum(reporter.stats.values())))
    suite.set("failures", str(reporter.stats.get("failed", 0)))
    suite.set("errors", str(reporter.stats.get("errors", 0)))
    suite.set("time", f"{reporter.end_time - reporter.start_time:.3f}")

    for result in reporter.failures:
        tc = ET.SubElement(suite, "testcase")
        tc.set("classname", result.test.path)
        tc.set("name", result.test.name)
        tc.set("time", f"{result.duration_ms / 1000:.3f}")
        fail = ET.SubElement(tc, "failure")
        fail.set("message", result.error or "Test failed")
        if result.traceback:
            fail.text = result.traceback

    for result in reporter.skipped:
        tc = ET.SubElement(suite, "testcase")
        tc.set("classname", result.test.path)
        tc.set("name", result.test.name)
        ET.SubElement(tc, "skipped")

    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]

    opts = _parse_args(args)

    if opts.get("version"):
        from oxytest import __version__
        print(f"oxytest {__version__}")
        return 0

    if opts.get("help"):
        print("Usage: oxytest [options] [paths]")
        print()
        print("Options:")
        print("  -v, --verbose       Increase verbosity")
        print("  -q, --quiet         Quiet output")
        print("  -x, --exitfirst     Exit on first failure")
        print("  -k EXPRESSION       Filter tests by keyword")
        print("  --tb=style          Traceback style (short, long, native, no)")
        print("  -n WORKERS          Number of parallel workers")
        print("  --junitxml=PATH     Generate JUnit XML report")
        print("  -s                  Don't capture stdout/stderr")
        print("  --maxfail=N         Stop after N failures")
        print("  --coverage          Enable coverage")
        print("  --version           Show version")
        print("  -h, --help          Show this help message")
        return 0

    return _run_tests(
        paths=opts["paths"],
        verbose=opts["verbose"],
        quiet=opts["quiet"],
        exitfirst=opts["exitfirst"],
        keyword=opts["keyword"],
        tb_style=opts["tb_style"],
        num_workers=opts["num_workers"],
        junitxml=opts["junitxml"],
        nocapture=opts["nocapture"],
        maxfail=opts["maxfail"],
    )


_oxytest_api = [
    "main",
    "approx",
    "raises",
    "fixture",
    "mark",
    "skip",
    "skipif",
    "xfail",
    "param",
    "fail",
    "exit",
    "set_trace",
    "importorskip",
    "Exit",
    "PytestError",
    "UsageError",
    "SkipTest",
    "Failed",
    "approx",
    "ApproxDecimal",
    "FixtureRequest",
    "TempPathFactory",
    "TestReport",
    "Mark",
    "MarkDecorator",
    "raises",
    "RaisesContext",
]

__all__ = _oxytest_api
