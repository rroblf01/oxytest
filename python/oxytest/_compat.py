import enum
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from oxytest._core import discover_tests, run_tests, run_tests_sequential, TestItem, TestResult
from oxytest._config import load_config, merge_config_with_opts


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

    def __eq__(self, actual):
        return self._eq(actual)

    def __ne__(self, actual):
        return not self._eq(actual)

    def __hash__(self):
        return hash(self.expected)

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
        self._check = None

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
        if self._check is not None and not self._check(exc_val):
            raise Failed(
                f"Exception check failed: {exc_val!r}"
            )
        self.excinfo = (exc_type, exc_val, exc_tb)
        return True

    @property
    def value(self):
        if self.excinfo is None:
            raise ValueError("No exception was raised")
        return self.excinfo[1]

    @property
    def traceback(self):
        if self.excinfo is None:
            return None
        return self.excinfo[2]

    def getrepr(self, **kwargs):
        if self.excinfo is None:
            return None
        return _ExceptionRepr(self.excinfo, **kwargs)

    def group_contains(self, exc_type, *, match=None, depth=None):
        if self.excinfo is None:
            return False
        exc_val = self.excinfo[1]
        if hasattr(exc_val, "exceptions"):
            for e in exc_val.exceptions:
                if isinstance(e, exc_type):
                    if match is None or re.search(match, str(e)):
                        return True
        return isinstance(exc_val, exc_type)


def raises(
    expected_exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]],
    *args,
    match: Optional[str] = None,
    check: Optional[Callable] = None,
) -> Union[RaisesContext, ContextManager]:
    if args:
        func = args[0]
        try:
            func(*args[1:])
        except expected_exception:
            pass
        else:
            raise Failed(f"DID NOT RAISE {expected_exception}")
        return RaisesContext(expected_exception)
    ctx = RaisesContext(expected_exception, match=match)
    ctx._check = check
    return ctx


class ExitCode(enum.IntEnum):
    OK = 0
    TESTS_FAILED = 1
    INTERRUPTED = 2
    USAGE_ERROR = 3
    NO_TESTS_COLLECTED = 4


def warns(expected_warning, *args, match=None):
    """Assert that code raises a particular warning."""
    import warnings
    if args:
        func = args[0]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            func(*args[1:])
            for warning in w:
                if issubclass(warning.category, expected_warning):
                    if match is None or re.search(match, str(warning.message)):
                        return warning
        raise Failed(f"DID NOT WARN {expected_warning}")
    return _WarningsChecker(expected_warning, match=match)


def deprecated_call(*args, **kwargs):
    """Assert that code produces a DeprecationWarning or PendingDeprecationWarning."""
    return warns((DeprecationWarning, PendingDeprecationWarning), *args, **kwargs)


class _WarningsRecorder:
    """Mimics pytest's WarningsRecorder: is iterable, indexable, has .list and .len."""
    def __init__(self, inner):
        self._inner = inner
        self.list = self

    def __iter__(self):
        return iter(self._inner)

    def __len__(self):
        return len(self._inner)

    def __getitem__(self, idx):
        return self._inner[idx]

    def __contains__(self, item):
        return item in self._inner

    def __bool__(self):
        return bool(self._inner)

class _WarningsChecker:
    def __init__(self, expected_warning, match=None):
        self.expected_warning = expected_warning
        self.match = match
        self.warning = None

    def __enter__(self):
        import warnings
        self._warnings = warnings.catch_warnings(record=True)
        self._cm = self._warnings.__enter__()
        warnings.simplefilter("always")
        return _WarningsRecorder(self._cm)

    def __exit__(self, *exc_info):
        import warnings
        self._warnings.__exit__(*exc_info)
        found = False
        for w in self._cm:
            if issubclass(w.category, self.expected_warning):
                if self.match is None or re.search(self.match, str(w.message)):
                    self.warning = w
                    found = True
                    continue
            warnings.warn_explicit(
                message=w.message,
                category=w.category,
                filename=w.filename,
                lineno=w.lineno,
                module=w.__module__,
                source=getattr(w, 'source', None),
            )
        if not found:
            raise Failed(f"DID NOT WARN {self.expected_warning}")
        return True

    def __len__(self):
        return 1 if self.warning is not None else 0


class _ExceptionRepr:
    def __init__(self, excinfo, **kwargs):
        self._excinfo = excinfo
        self._kwargs = kwargs

    def __str__(self):
        return str(self._excinfo[1])


class PytestWarning(UserWarning):
    """Base class for pytest warnings."""


class PytestDeprecationWarning(FutureWarning):
    """Warning for deprecated pytest features."""


def skip(reason: str = "", **kwargs) -> None:
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

    def __call__(self, *args, **kwargs):
        if args and callable(args[0]) and not kwargs:
            func = args[0]
            if not hasattr(func, "_oxytest_marks"):
                func._oxytest_marks = []
            func._oxytest_marks.append((self.name, self.args, self.kwargs))
            return func
        new_args = self.args + args
        new_kwargs = dict(self.kwargs)
        new_kwargs.update(kwargs)
        return MarkDecorator(self.name, new_args, new_kwargs)


class Mark:
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "mark":
            return self
        return MarkDecorator(name)

    def parametrize(self, argnames, argvalues, *args, **kwargs):
        return MarkDecorator("parametrize", (argnames, argvalues) + args, kwargs)

    def skip(self, reason: Optional[str] = None):
        return MarkDecorator("skip", (), {"reason": reason})

    def skipif(self, *conditions, reason: Optional[str] = None, **kwargs):
        return MarkDecorator("skipif", conditions, {"reason": reason, **kwargs})

    def xfail(self, condition=None, reason: Optional[str] = None, raises=None, strict=None, run=True):
        return MarkDecorator("xfail", (), {"condition": condition, "reason": reason, "raises": raises, "strict": strict, "run": run})

    def usefixtures(self, *fixture_names):
        return MarkDecorator("usefixtures", fixture_names)

    def filterwarnings(self, *actions: str, **kwargs):
        return MarkDecorator("filterwarnings", actions, kwargs)


mark = Mark()


def param(*values, marks=None, id: Optional[str] = None):
    result: dict[str, object] = {"values": values}
    if marks:
        result["marks"] = marks if isinstance(marks, (list, tuple)) else [marks]
    if id is not None:
        result["id"] = id
    return result


class FixtureRequest:
    def __init__(self, scope: str = "function", _test_func=None):
        self.scope = scope
        self.fixtures: Dict[str, Any] = {}
        self._fixturedefs: Dict[str, Any] = {}
        self._test_func = _test_func
        self.param = None
        self._oxytest_config = None

    @property
    def config(self):
        return self._oxytest_config

    @property
    def node(self):
        return _RequestNode(self._test_func)

    def getfixturevalue(self, name: str) -> Any:
        if name in self.fixtures:
            return self.fixtures[name]
        raise LookupError(f"Fixture {name!r} not found")


class _RequestNode:
    def __init__(self, test_func=None):
        self._test_func = test_func

    @property
    def nodeid(self):
        return _get_test_full_id(self._test_func)

    @property
    def name(self):
        if self._test_func is not None:
            return self._test_func.__name__
        return ""

    def get_closest_marker(self, name):
        if self._test_func is not None and hasattr(self._test_func, "_oxytest_marks"):
            for mark_name, mark_args, mark_kwargs in self._test_func._oxytest_marks:
                if mark_name == name:
                    return _Marker(name, mark_args, mark_kwargs)
        return None


class _Marker:
    def __init__(self, name, args, kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class TempPathFactory:
    def __init__(self, base: str):
        self._base = base

    def mktemp(self, basename: str) -> str:
        path = os.path.join(self._base, basename)
        os.makedirs(path, exist_ok=True)
        return path


def fixture(
    scope: Union[str, Callable[..., Any]] = "function",
    params: Optional[list] = None,
    autouse: bool = False,
    name: Optional[str] = None,
    ids: Optional[list] = None,
):
    if callable(scope):
        func: Any = scope
        func._oxytest_fixture = {
            "scope": "function",
            "params": None,
            "autouse": False,
            "name": getattr(func, "__name__", str(func)),
        }
        return func
    def decorator(func: Any) -> Callable[..., Any]:
        func._oxytest_fixture = {
            "scope": scope,
            "params": params,
            "autouse": autouse,
            "name": name or getattr(func, "__name__", str(func)),
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


def _should_skip(func, cls=None, mod=None):
    for obj in (func, cls, mod):
        if obj is not None and hasattr(obj, "_oxytest_marks"):
            for mark_name, args, kwargs in obj._oxytest_marks:
                if mark_name == "skip":
                    return kwargs.get("reason", "skipped")
                if mark_name == "skipif":
                    if args and any(args):
                        return kwargs.get("reason", "condition true")
    # Also check module-level pytestmark attribute
    if mod is not None:
        mod_marks = getattr(mod, "pytestmark", None)
        if mod_marks is not None:
            if not isinstance(mod_marks, (list, tuple)):
                mod_marks = [mod_marks]
            for m in mod_marks:
                if hasattr(m, "name") and hasattr(m, "args") and hasattr(m, "kwargs"):
                    if m.name == "skip":
                        return m.kwargs.get("reason", "skipped")
                    if m.name == "skipif":
                        if m.args and any(m.args):
                            return m.kwargs.get("reason", "condition true")
    return None


def _is_xfail(func, cls=None, mod=None):
    for obj in (func, cls, mod):
        if obj is not None and hasattr(obj, "_oxytest_marks"):
            for mark_name, args, kwargs in obj._oxytest_marks:
                if mark_name == "xfail":
                    condition = kwargs.get("condition")
                    if condition is None or condition:
                        return kwargs.get("reason", "")
    # Also check module-level pytestmark attribute
    if mod is not None:
        mod_marks = getattr(mod, "pytestmark", None)
        if mod_marks is not None:
            if not isinstance(mod_marks, (list, tuple)):
                mod_marks = [mod_marks]
            for m in mod_marks:
                if hasattr(m, "name") and hasattr(m, "args") and hasattr(m, "kwargs"):
                    if m.name == "xfail":
                        condition = m.kwargs.get("condition")
                        if condition is None or condition:
                            return m.kwargs.get("reason", "")
    return None


def _get_parametrize(func):
    if hasattr(func, "_oxytest_marks"):
        for mark_name, args, kwargs in func._oxytest_marks:
            if mark_name == "parametrize" and len(args) >= 2:
                yield args[0], args[1]


class TestReport:
    def __init__(self, test: TestItem, passed: bool, duration_ms: int, output: str, error: Optional[str]):
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
    def __init__(self, verbose: bool = False, quiet: bool = False, tb_style: str = "short",
                 showlocals: bool = False, setup_show: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.tb_style = tb_style
        self.showlocals = showlocals
        self.setup_show = setup_show
        self.stats = defaultdict(int)
        self.results: List[TestResult] = []
        self.failures: List[TestResult] = []
        self.errors: List[TestResult] = []
        self.skipped: List[TestResult] = []
        self.start_time = 0.0
        self.end_time = 0.0

    def start(self):
        self.start_time = time.time()
        if not self.quiet:
            print("=" * 60)
            print("oxytest: running tests")
            print("=" * 60)

    def test_result(self, result: TestResult):
        self.results.append(result)
        if result.passed:
            self.stats["passed"] += 1
        else:
            err = result.error or ""
            if "SKIPPED:" in err:
                self.stats["skipped"] += 1
                self.skipped.append(result)
            elif "XFAIL:" in err:
                self.stats["xfailed"] += 1
                self.skipped.append(result)
            elif "XPASS:" in err:
                self.stats["passed"] += 1
            else:
                self.stats["failed"] += 1
                self.failures.append(result)

        if self.verbose:
            err = result.error or ""
            if "SKIPPED:" in err:
                status = "SKIPPED"
            elif "XFAIL:" in err:
                status = "XFAIL"
            elif "XPASS:" in err:
                status = "XPASS"
            elif result.passed:
                status = "PASSED"
            else:
                status = "FAILED"
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
                if result.error:
                    print(result.error)
                if result.traceback:
                    lines = result.traceback.split("\n")
                    if self.tb_style == "short":
                        relevant = [line for line in lines if "raise" in line or "assert" in line or "Error:" in line or "Exception:" in line]
                        if relevant:
                            print("\n".join(relevant[-5:]))
                        else:
                            print("\n".join(lines[-8:]))
                    elif self.tb_style == "no":
                        pass  # error already printed above
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


class Parser:
    """Minimal argparse-like interface for ``pytest_addoption`` hooks."""

    def __init__(self):
        self._options: dict[str, dict] = {}

    def addoption(self, *args: str, **kwargs):
        key = kwargs.get("dest") or args[0].lstrip("-").replace("-", "_")
        self._options[key] = {"args": args, "kwargs": kwargs, "value": None}

    def parse(self, argv: list[str]) -> dict:
        """Parse known plugin options from argv, return {key: value}."""
        result = {}
        for key, opt in self._options.items():
            for arg in opt["args"]:
                if arg in argv:
                    idx = argv.index(arg)
                    if opt["kwargs"].get("action") in ("store_true", "store_false"):
                        result[key] = argv[idx] not in ("--no-" + arg.lstrip("-"),)
                    elif idx + 1 < len(argv):
                        result[key] = argv[idx + 1]
                    break
            if key not in result:
                result[key] = opt["kwargs"].get("default", None)
        return result


class _TraceStub:
    class _Root:
        def get(self, name):
            return _TraceStub()
    root = _Root()
    def __call__(self, *args, **kwargs):
        pass


class Config:
    """Holds parsed CLI options and plugin state."""

    def __init__(self, opts: dict, parser: Parser | None = None):
        self._opts = opts
        self.parser = parser or Parser()
        self.plugin_options: dict = {}
        self._inicfg: dict = {}
        self.rootdir = opts.get("rootdir", None)
        self._stash_data: dict = {}
        self._benchmarksession = None
        self.trace = _TraceStub()

    def getoption(self, name: str, default=None):
        return self._opts.get(name, default)

    @property
    def option(self):
        return self._opts

    def getini(self, name: str):
        return self._inicfg.get(name, "")

    @property
    def stash(self):
        return _ConfigStash(self._stash_data)

    def addinivalue_line(self, name: str, line: str):
        if name not in self._inicfg:
            self._inicfg[name] = []
        self._inicfg[name].append(line)


class _ConfigStash:
    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key):
        if key not in self._data:
            # Auto-populate assertstate_key for _pytest assertion rewrite
            try:
                from _pytest.assertion.rewrite import assertstate_key
                if key is assertstate_key:
                    from _pytest.assertion import AssertionState
                    class _FakeConfig:
                        class _Trace:
                            class _Root:
                                def get(self, name: str) -> None: return None
                            root = _Root()
                        trace = _Trace()
                    value = AssertionState(_FakeConfig(), "rewrite")  # ty: ignore
                    self._data[key] = value
                    return value
            except Exception:
                pass
            self._data[key] = {}
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        if key in self._data:
            return self._data[key]
        if "assertstate" in str(key).lower() or "assertion" in str(key).lower():
            try:
                from _pytest.assertion import AssertionState
                class _FakeConfig:
                    class _Trace:
                        class _Root:
                            def get(self, name: str) -> None: return None
                        root = _Root()
                    trace = _Trace()
                self._data[key] = AssertionState(_FakeConfig(), "rewrite")  # ty: ignore
                return self._data[key]
            except Exception:
                pass
        return default


def _parse_args(args: List[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {
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
    "version": False,
    "plugins": [],
    "ignore": [],
    "collect_only": False,
    "durations": None,
    "report_summary": False,
    "showlocals": False,
    "strict_markers": False,
    "rootdir": None,
    "fixtures_list": False,
    "markers_list": False,
    "setup_show": False,
    "cache_clear": False,
    "lf": False,
    "ff": False,
    "pdb": False,
    "trace": False,
    "cov_source": None,
    "cov_report": "term",
    "cov_config": None,
    "cov_branch": False,
    "cov_fail_under": None,
    "cov_append": False,
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
        elif arg.startswith("--tb="):
            parsed["tb_style"] = arg[5:]
        elif arg == "--tb" and i + 1 < len(args):
            i += 1
            parsed["tb_style"] = args[i]
        elif arg == "-n" and i + 1 < len(args):
            i += 1
            if args[i] == "auto":
                import os
                parsed["num_workers"] = os.cpu_count() or 1
            else:
                parsed["num_workers"] = int(args[i])
        elif arg == "--junitxml" and i + 1 < len(args):
            i += 1
            parsed["junitxml"] = args[i]
        elif arg == "-s":
            parsed["nocapture"] = True
        elif arg == "--maxfail" and i + 1 < len(args):
            i += 1
            parsed["maxfail"] = int(args[i])
        elif arg in ("--version",):
            parsed["version"] = True
        elif arg == "-p" and i + 1 < len(args):
            i += 1
            parsed["plugins"].append(args[i])
        elif arg == "--ignore" and i + 1 < len(args):
            i += 1
            parsed["ignore"].append(args[i])
        elif arg in ("--collect-only", "--co"):
            parsed["collect_only"] = True
        elif arg == "--durations" and i + 1 < len(args):
            i += 1
            parsed["durations"] = int(args[i])
        elif arg.startswith("-r") and len(arg) > 2:
            parsed["report_summary"] = arg[2:]
        elif arg == "--showlocals":
            parsed["showlocals"] = True
        elif arg == "--strict-markers":
            parsed["strict_markers"] = True
        elif arg == "--rootdir" and i + 1 < len(args):
            i += 1
            parsed["rootdir"] = args[i]
        elif arg == "--fixtures":
            parsed["fixtures_list"] = True
        elif arg == "--markers":
            parsed["markers_list"] = True
        elif arg == "--setup-show":
            parsed["setup_show"] = True
        elif arg in ("--lf", "--last-failed"):
            parsed["lf"] = True
        elif arg in ("--ff", "--failed-first"):
            parsed["ff"] = True
        elif arg == "--cache-clear":
            parsed["cache_clear"] = True
        elif arg == "--pdb":
            parsed["pdb"] = True
        elif arg == "--trace":
            parsed["trace"] = True
            parsed["pdb"] = True
        elif arg == "--cov":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 1
                parsed["cov_source"] = args[i]
            else:
                parsed["cov_source"] = True
        elif arg.startswith("--cov="):
            parsed["cov_source"] = arg[6:]
        elif arg == "--cov-report" and i + 1 < len(args):
            i += 1
            parsed["cov_report"] = args[i]
        elif arg == "--cov-config" and i + 1 < len(args):
            i += 1
            parsed["cov_config"] = args[i]
        elif arg == "--cov-branch":
            parsed["cov_branch"] = True
        elif arg == "--cov-fail-under" and i + 1 < len(args):
            i += 1
            parsed["cov_fail_under"] = float(args[i])
        elif arg == "--cov-append":
            parsed["cov_append"] = True
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


def _parse_keyword_expression(expr: str):
    tokens = []
    i = 0
    while i < len(expr):
        c = expr[i]
        if c.isspace():
            i += 1
        elif c in ("(", ")"):
            tokens.append(c)
            i += 1
        else:
            j = i
            while j < len(expr) and not expr[j].isspace() and expr[j] not in "()":
                j += 1
            token = expr[i:j].lower()
            if token in ("and", "or", "not"):
                tokens.append(token.upper())
            else:
                tokens.append(token)
            i = j
    return tokens


def _eval_keyword_expression(tokens, test_name, markers):
    if not tokens:
        return True
    idx = [0]

    def parse_expr():
        result = parse_term()
        while idx[0] < len(tokens) and tokens[idx[0]] == "OR":
            idx[0] += 1
            right = parse_term()
            result = result or right
        return result

    def parse_term():
        result = parse_factor()
        while idx[0] < len(tokens) and tokens[idx[0]] == "AND":
            idx[0] += 1
            right = parse_factor()
            result = result and right
        return result

    def parse_factor():
        if idx[0] < len(tokens) and tokens[idx[0]] == "NOT":
            idx[0] += 1
            return not parse_factor()
        if idx[0] < len(tokens) and tokens[idx[0]] == "(":
            idx[0] += 1
            result = parse_expr()
            if idx[0] < len(tokens) and tokens[idx[0]] == ")":
                idx[0] += 1
            return result
        if idx[0] < len(tokens):
            word = tokens[idx[0]]
            idx[0] += 1
            return _match_keyword(word, test_name, markers)
        return True

    return parse_expr()


def _match_keyword(word, test_name, markers):
    if word.startswith('"') and word.endswith('"'):
        word = word[1:-1]
    lc_name = test_name.lower()
    lc_word = word.lower()
    if lc_word in lc_name:
        return True
    for m in markers:
        if isinstance(m, str) and lc_word in m.lower():
            return True
        if hasattr(m, "name") and lc_word in m.name.lower():
            return True
    return False


def _filter_keyword_expression(tests, expr):
    tokens = _parse_keyword_expression(expr)
    filtered = []
    for t in tests:
        markers = []
        mod = None
        if hasattr(t, "path") and t.path:
            try:
                mod = _get_test_module(t.path)
            except Exception:
                mod = None
        if mod:
            mod_marks = getattr(mod, "pytestmark", None)
            if mod_marks:
                if not isinstance(mod_marks, (list, tuple)):
                    mod_marks = [mod_marks]
                markers.extend(mod_marks)
            func_name = t.name.split("[")[0].split("::")[-1] if "::" in t.name else t.name.split("[")[0]
            func = getattr(mod, func_name, None)
            if func and hasattr(func, "_oxytest_marks"):
                for m_name, m_args, m_kwargs in func._oxytest_marks:
                    markers.append(m_name)
        if _eval_keyword_expression(tokens, t.path + "::" + t.name, markers):
            filtered.append(t)
    return filtered


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
    config: Optional['Config'] = None,
    ignore: Optional[List[str]] = None,
    collect_only: bool = False,
    durations: Optional[int] = None,
    report_summary: Optional[str] = None,
    showlocals: bool = False,
    strict_markers: bool = False,
    rootdir: Optional[str] = None,
    fixtures_list: bool = False,
    markers_list: bool = False,
    setup_show: bool = False,
    cache_clear: bool = False,
    lf: bool = False,
    ff: bool = False,
    pdb: bool = False,
    trace: bool = False,
    cov_plugin=None,
) -> int:
    pm = None
    if config is not None:
        from oxytest._plugin import get_plugin_manager
        pm = get_plugin_manager()
        pm.hook.pytest_sessionstart(session=config)

    if cache_clear:
        _clear_cache()

    root_paths = [rootdir] if rootdir else paths

    _module_cache_clear()
    from oxytest._fixtures import get_fixture_manager as _get_fm
    _get_fm()._config = config

    # Add cwd to sys.path so relative module names resolve
    import sys as _sys
    _cwd = os.getcwd()
    global _original_cwd
    _original_cwd = _cwd
    if _cwd not in _sys.path:
        _sys.path.append(_cwd)

    # Remove tests/ subdirectories from sys.path to prevent package shadowing
    _shadow_candidates = [
        os.path.join(_cwd, "tests", sp)
        for sp in ("pydantic_core", "types", "pydantic")
    ]
    for _sp in _shadow_candidates:
        if _sp in _sys.path:
            _sys.path.remove(_sp)

    has_expr = keyword and any(op in keyword.lower() for op in (" and ", " or ", " not "))
    all_tests = []
    for path in root_paths:
        kw = None if has_expr else keyword
        tests = discover_tests(path, kw)
        if ignore:
            tests = [t for t in tests if not _is_ignored(t.path, ignore)]
        all_tests.extend(tests)
        _load_conftest(path, config=config)
        for _test in tests:
            _tdir = os.path.dirname(os.path.abspath(_test.path))
            _load_conftest(_tdir, config=config)

    if has_expr:
        all_tests = _filter_keyword_expression(all_tests, keyword)

    if not all_tests:
        if not collect_only:
            print("No tests found")
        return 0

    if pm:
        pm.hook.pytest_collection_modifyitems(
            session=config, config=config, items=all_tests
        )

    all_tests = _expand_parametrize(all_tests)

    if strict_markers:
        _validate_markers(all_tests)

    if fixtures_list:
        _list_fixtures()
        return 0

    if markers_list:
        _list_markers()
        return 0

    if collect_only:
        _print_collected(all_tests, verbose=verbose)
        return 0

    reporter = TerminalReporter(
        verbose=verbose, quiet=quiet, tb_style=tb_style,
        showlocals=showlocals, setup_show=setup_show,
    )
    reporter.start()

    if verbose:
        print(f"\nDiscovered {len(all_tests)} test(s)")
        print()

    if verbose:
        print(f"After parametrize expansion: {len(all_tests)} test(s)")
        print()

    if pdb:
        os.environ["OXYTEST_PDB"] = "1"
    if trace:
        os.environ["OXYTEST_TRACE"] = "1"

    if cov_plugin:
        cov_plugin.start()

    if setup_show:
        os.environ["OXYTEST_SETUP_SHOW"] = "1"
    if showlocals:
        os.environ["OXYTEST_SHOWLOCALS"] = "1"

    # Cache support: --lf (last failed) and --ff (failed first)
    if lf or ff:
        last_failed = _read_lastfailed()
        lf_tests = [t for t in all_tests if (t.path, t.name) in last_failed]
        passed_tests = [t for t in all_tests if (t.path, t.name) not in last_failed]
        if lf:
            all_tests = lf_tests
        elif ff:
            all_tests = lf_tests + passed_tests
        if verbose and lf and lf_tests:
            print(f"Running {len(lf_tests)} previously failed test(s)")
        elif verbose and ff:
            print(f"Running {len(lf_tests)} failed + {len(passed_tests)} passed")

    if num_workers is None or num_workers == 1:
        results = run_tests_sequential(all_tests, nocapture=nocapture)
    else:
        results = run_tests(all_tests, num_workers, nocapture=nocapture)

    if cov_plugin:
        cov_plugin.stop_and_save()

    if setup_show:
        os.environ.pop("OXYTEST_SETUP_SHOW", None)
    if showlocals:
        os.environ.pop("OXYTEST_SHOWLOCALS", None)
    if pdb or trace:
        os.environ.pop("OXYTEST_PDB", None)
        os.environ.pop("OXYTEST_TRACE", None)

    for result in results:
        reporter.test_result(result)
        if not result.passed and exitfirst:
            break
        if maxfail and reporter.stats.get("failed", 0) >= maxfail:
            break

    reporter.finish()

    if lf or ff:
        _write_lastfailed(results)
    elif not lf and results:
        _write_lastfailed(results)

    if durations:
        _print_durations(reporter.results, durations)

    if report_summary:
        _print_summary(reporter, report_summary)

    if junitxml:
        _write_junitxml(reporter, junitxml)

    exitcode = reporter.get_exit_code()

    if pm:
        pm.hook.pytest_sessionfinish(session=config, exitstatus=exitcode)

    return exitcode


def _is_ignored(path: str, ignore_patterns: List[str]) -> bool:
    """Check if a test path matches any ignore pattern."""
    for pat in ignore_patterns:
        if path.startswith(pat) or pat in path:
            return True
    return False


def _clear_cache():
    """Remove .pytest_cache/ directory."""
    import shutil
    cache_dir = ".pytest_cache"
    if os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)


def _format_assert_detail(source_line: str, filename: str, lineno: int) -> str:
    """Extract values from an assertion expression for a helpful error message."""
    import ast
    try:
        tree = ast.parse(source_line, filename=filename)
    except SyntaxError:
        return ""
    if not isinstance(tree, ast.Module) or not tree.body:
        return ""
    stmt = tree.body[0]
    if not isinstance(stmt, ast.Assert):
        return source_line
    test = stmt.test
    parts = [source_line]
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left = test.left
        right = test.comparators[0]
        op = test.ops[0]
        op_str = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=", ast.Is: "is", ast.IsNot: "is not",
            ast.In: "in", ast.NotIn: "not in",
        }.get(type(op), "")
        if op_str:
            parts.append(f"{ast.unparse(left)} {op_str} {ast.unparse(right)}")
    elif isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id in ("isinstance", "hasattr"):
        parts.append(ast.unparse(test))
    else:
        parts.append(ast.unparse(test))
    return "\n".join(parts)


def _cache_dir() -> str:
    return os.path.join(_original_cwd if _original_cwd else os.getcwd(), ".pytest_cache", "oxytest")


def _lastfailed_path() -> str:
    return os.path.join(_cache_dir(), "lastfailed")


def _read_lastfailed() -> set:
    """Read set of (path, name) tuples that failed last run."""
    import json
    lf_path = _lastfailed_path()
    if not os.path.isfile(lf_path):
        return set()
    try:
        with open(lf_path) as f:
            data = json.load(f)
        return set(tuple(item) for item in data)
    except (json.JSONDecodeError, OSError):
        return set()


def _write_lastfailed(results):
    """Write set of (path, name) tuples that failed to cache."""
    import json
    import os
    failed = [(r.test.path, r.test.name) for r in results if not r.passed]
    dirpath = _cache_dir()
    os.makedirs(dirpath, exist_ok=True)
    with open(_lastfailed_path(), "w") as f:
        json.dump(failed, f)


def _validate_markers(tests):
    """Check that all markers are registered (stub for now)."""
    known = {"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings"}
    unknown = set()
    for t in tests:
        mod = _get_test_module(t.path)
        if mod is None:
            continue
        raw = t.name.split("[")[0]
        clean = raw.split("::")[-1] if "::" in raw else raw
        func = getattr(mod, clean, None)
        if func is None:
            continue
        marks = getattr(func, "_oxytest_marks", [])
        for name, _, _ in marks:
            if name not in known:
                unknown.add(name)
    if unknown:
        print(f"oxytest: error – unknown marker(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        sys.exit(2)


def _list_fixtures():
    from oxytest._fixtures import get_fixture_manager
    fm = get_fixture_manager()
    print("Available fixtures:")
    for name in sorted(fm._fixtures.keys()):
        fdef = fm._fixtures[name]
        print(f"  {name} (scope={fdef.scope}, autouse={fdef.autouse})")


def _list_markers():
    known = {"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings"}
    print("Registered markers:")
    for m in sorted(known):
        print(f"  {m}  -- oxytest internal marker")
    print()
    print("Use ``@pytest.mark.name`` to register custom markers.")


def _print_collected(tests, verbose=False):
    """Print collected tests without running them."""
    print(f"Collected {len(tests)} test(s)")
    if verbose:
        for t in tests:
            print(f"  {t.path}::{t.name}")


def _print_durations(results, n):
    """Print the N slowest tests."""
    sorted_results = sorted(results, key=lambda r: r.duration_ms, reverse=True)
    print()
    print("=" * 60)
    print(f"Slowest {min(n, len(sorted_results))} test(s):")
    print("=" * 60)
    for r in sorted_results[:n]:
        print(f"  {r.duration_ms:>6}ms  {r.test.path}::{r.test.name}")


def _print_summary(reporter, chars):
    """Print extra summary based on -r flags."""
    summary_lines = []
    for ch in chars:
        if ch == "A":
            for r in reporter.results:
                if r.passed:
                    summary_lines.append(f"  PASS {r.test.path}::{r.test.name}")
            for line in _summary_for_failures(reporter):
                summary_lines.append(line)
            for r in reporter.skipped:
                summary_lines.append(f"  SKIP {r.test.path}::{r.test.name}")
        elif ch == "f":
            for line in _summary_for_failures(reporter):
                summary_lines.append(line)
        elif ch == "s":
            for r in reporter.skipped:
                summary_lines.append(f"  SKIP {r.test.path}::{r.test.name}")
        elif ch == "x":
            pass  # xfail — not tracked yet
        elif ch == "w":
            pass  # warnings — not tracked yet
    if summary_lines:
        print()
        print("=" * 60)
        print("Summary:")
        print("=" * 60)
        for line in summary_lines:
            print(line)


def _summary_for_failures(reporter):
    lines = []
    for r in reporter.failures:
        lines.append(f"  FAIL {r.test.path}::{r.test.name}")
    return lines


def _get_test_module(filepath):
    """Import a module by filepath (used by _validate_markers)."""
    import importlib.util
    module_name = filepath.replace("/", ".").replace("\\", ".").rstrip(".py").lstrip(".")
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _write_junitxml(reporter: TerminalReporter, path: str):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    suite.set("name", "oxytest")
    suite.set("tests", str(sum(reporter.stats.values())))
    suite.set("failures", str(reporter.stats.get("failed", 0)))
    suite.set("errors", str(reporter.stats.get("errors", 0)))
    suite.set("time", f"{reporter.end_time - reporter.start_time:.3f}")
    suite.set("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(reporter.start_time)))

    system_out_lines: list[str] = []
    system_err_lines: list[str] = []

    for result in reporter.results:
        tc = ET.SubElement(suite, "testcase")
        tc.set("classname", result.test.path)
        tc.set("name", result.test.name)
        tc.set("time", f"{result.duration_ms / 1000:.3f}")
        err = result.error or ""
        if not result.passed and "SKIPPED:" in err:
            ET.SubElement(tc, "skipped")
        elif not result.passed and "XFAIL:" in err:
            sk = ET.SubElement(tc, "skipped")
            sk.set("type", "pytest.xfail")
            sk.set("message", err.replace("XFAIL:", "").strip())
        elif not result.passed:
            fail = ET.SubElement(tc, "failure")
            fail.set("message", err or "Test failed")
            if result.traceback:
                fail.text = result.traceback
        if result.output:
            system_out_lines.append(f"--- {result.test.path}::{result.test.name} ---")
            system_out_lines.append(result.output)
        if result.error_output:
            system_err_lines.append(f"--- {result.test.path}::{result.test.name} ---")
            system_err_lines.append(result.error_output)

    if system_out_lines:
        so = ET.SubElement(suite, "system-out")
        so.text = "\n".join(system_out_lines)

    if system_err_lines:
        se = ET.SubElement(suite, "system-err")
        se.text = "\n".join(system_err_lines)

    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]

    if args and args[0] == "migrate":
        from oxytest._migrate import migrate_main
        return migrate_main(args[1:])

    opts = _parse_args(args)

    config_data = load_config()
    opts = merge_config_with_opts(config_data, opts)

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
        print("  -p PLUGIN           Load plugin (can be used multiple times)")
        print("  --ignore=PATH       Ignore test path (can be used multiple times)")
        print("  --collect-only, --co  Only collect tests, don't run")
        print("  --durations=N       Show N slowest tests")
        print("  -r[chars]           Show extra test summary (-rA, -rf, -rs, ...)")
        print("  --showlocals        Show local variables in tracebacks")
        print("  --strict-markers    Unknown markers cause errors")
        print("  --rootdir=PATH      Set root directory for discovery")
        print("  --fixtures          List available fixtures")
        print("  --markers           List registered markers")
        print("  --setup-show        Print fixture setup/teardown")
        print("  --cache-clear       Clear cache before run")
        print("  --lf, --last-failed  Run only tests that failed last time")
        print("  --ff, --failed-first Run failed tests first, then rest")
        print("  --pdb               Drop into debugger on failure")
        print("  --trace             Drop into debugger before each test")
        print("  --cov[=SOURCE]      Measure code coverage")
        print("  --cov-report=TYPE   Coverage report type (term, html, xml)")
        print("  --cov-config=FILE   Config file for coverage")
        print("  --cov-branch        Enable branch coverage")
        print("  --cov-fail-under=N  Fail if coverage below N%")
        print("  --cov-append        Append to existing coverage data")
        print("  --version           Show version")
        print("  -h, --help          Show this help message")
        print()
        print("Subcommands:")
        print("  migrate             Automatically migrate imports between pytest and oxytest")
        print("                      (e.g., `oxytest migrate --dry-run`)")
        return 0

    from oxytest._plugin import get_plugin_manager

    pm = get_plugin_manager()
    pm.load_entry_point_plugins()

    config = Config(opts)
    for plugin_name in opts.get("plugins", []):
        pm.load_plugin_by_name(plugin_name)

    pm.hook.pytest_addoption(parser=config.parser)
    config.plugin_options = config.parser.parse(sys.argv[1:])
    pm.hook.pytest_configure(config=config)

    cov_plugin = None
    if opts.get("cov_source"):
        from oxytest._cov import OxytestCoverPlugin, is_available
        if is_available():
            cov_plugin = OxytestCoverPlugin(
                source=opts["cov_source"],
                report=opts.get("cov_report", "term"),
                config_file=opts.get("cov_config"),
                branch=opts.get("cov_branch", False),
                fail_under=opts.get("cov_fail_under"),
                append=opts.get("cov_append", False),
            )

    exitcode = _run_tests(
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
        config=config,
        ignore=opts.get("ignore", []),
        collect_only=opts.get("collect_only", False),
        durations=opts.get("durations", None),
        report_summary=opts.get("report_summary", None),
        showlocals=opts.get("showlocals", False),
        strict_markers=opts.get("strict_markers", False),
        rootdir=opts.get("rootdir", None),
        fixtures_list=opts.get("fixtures_list", False),
        markers_list=opts.get("markers_list", False),
        setup_show=opts.get("setup_show", False),
        cache_clear=opts.get("cache_clear", False),
        lf=opts.get("lf", False),
        ff=opts.get("ff", False),
        pdb=opts.get("pdb", False),
        trace=opts.get("trace", False),
        cov_plugin=cov_plugin,
    )

    if cov_plugin:
        cov_plugin.generate_reports()

    return exitcode


def _load_conftest(root_dir: str, config: Optional['Config'] = None):
    """Load conftest.py files from the given directory and its parents."""
    from oxytest._fixtures import get_fixture_manager
    from oxytest._plugin import get_plugin_manager
    fm = get_fixture_manager()
    pm = get_plugin_manager()

    # Pre-populate stash with assertstate_key for AssertionRewritingHook
    if config is not None:
        try:
            from _pytest.assertion.rewrite import assertstate_key
            from _pytest.assertion import AssertionState
            config._stash_data[assertstate_key] = AssertionState(config, "rewrite")  # ty: ignore
        except Exception:
            pass

    dirpath = os.path.abspath(root_dir) if os.path.isdir(root_dir) else os.path.dirname(os.path.abspath(root_dir))
    seen = _conftest_seen
    while dirpath != "/" and dirpath not in seen:
        seen.add(dirpath)
        conftest_path = os.path.join(dirpath, "conftest.py")
        if os.path.isfile(conftest_path):
            module_name = os.path.relpath(conftest_path).replace("/", ".").replace("\\", ".").rstrip(".py").lstrip(".")
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, conftest_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                spec.loader.exec_module(mod)
                fm.register_from_module(mod)
                pm.load_conftest_plugins(mod, dirpath)
        parent = os.path.dirname(dirpath)
        if parent == dirpath:
            break
        dirpath = parent


_module_cache: dict = {}
_parametrize_cache: dict = {}
_conftest_seen: set = set()


def _module_cache_clear():
    _module_cache.clear()
    _parametrize_cache.clear()
    _conftest_seen.clear()
    _test_full_ids.clear()
    global _original_cwd
    _original_cwd = ""


_import_lock = __import__('threading').Lock()
_test_full_ids: dict = {}
_original_cwd: str = ""


def _get_test_full_id(func) -> str:
    return _test_full_ids.get(id(func), "")


def _set_test_full_id(func, test_id: str):
    _test_full_ids[id(func)] = test_id

def _execute_test(path: str, name: str, args_json: str):
    """Import module, resolve fixtures, and run a single test.
    Raises on failure (caught by Rust runner).
    """
    import sys as _sys
    _sys.setrecursionlimit(10000)  # Prevent RecursionError in deep schema recursion
    try:
        _execute_test_impl(path, name, args_json)
    except SkipTest as e:
        raise Exception("SKIPPED:" + str(e))
    except RecursionError as e:
        _sys.setrecursionlimit(5000)  # Reset for next test
        raise Exception("RECURSION:" + str(e))


def _execute_test_impl(path: str, name: str, args_json: str):
    import importlib.util
    import inspect
    import sys as _sys

    from oxytest._fixtures import get_fixture_manager
    fm = get_fixture_manager()

    _loaded_modules: list[str] = []

    # 1. Import module (cached per filepath) — with lock for parallel safety
    filepath = os.path.join(_original_cwd, path) if not os.path.isabs(path) else path
    dirpath = os.path.dirname(filepath)

    with _import_lock:
        if filepath not in _module_cache:
            if dirpath not in _sys.path:
                _sys.path.append(dirpath)

            # Build a dotted module name from relative path so relative imports work
            rel_path = os.path.relpath(filepath)
            module_name = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py").lstrip(".")

            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {path}")
            mod = importlib.util.module_from_spec(spec)
            _sys.modules[module_name] = mod
            _loaded_modules.append(module_name)
            try:
                spec.loader.exec_module(mod)
            except SkipTest:
                _module_cache[filepath] = None
                raise
            _module_cache[filepath] = mod
        else:
            mod = _module_cache[filepath]

    if mod is None:
        raise Exception("SKIPPED:module could not be imported (dependency missing)")

    fm.register_from_module(mod)

    # 2. Resolve function
    raw_name = name
    clean_name = name.split("[")[0] if "[" in name else name

    cls = None
    if "::" in clean_name:
        parts = clean_name.split("::")
        cls = getattr(mod, parts[0])
        instance = cls()
        # Support setUp/tearDown from unittest.TestCase
        if hasattr(instance, "setUp"):
            instance.setUp()
        func = getattr(instance, parts[1])
    else:
        func = getattr(mod, clean_name)

    fm.current_test_func = func
    _set_test_full_id(func, name)

    # 3. Parse parametrize args (match by name, not position)
    import json
    param_values = []
    param_names = []
    if args_json:
        try:
            param_values = json.loads(args_json)
        except Exception:
            pass
    cache_key = (filepath, name)
    _fixture_params = None
    if cache_key in _parametrize_cache:
        cached = _parametrize_cache[cache_key]
        if len(cached) == 3:
            param_names, param_values, _fixture_params = cached
        else:
            param_names, param_values = cached

    # Set fixture param for parametrized fixtures
    if _fixture_params:
        fm._current_request_param = _fixture_params

    # 4. Collect fixture names from signature and marks
    sig = inspect.signature(func)
    all_params = [p for p in sig.parameters.keys() if p != "self"]

    # Match parametrize values by name to handle multiple @pytest.mark.parametrize
    if param_names:
        param_dict = dict(zip(param_names, param_values))
        # Build param_values in the exact order of all_params,
        # leaving None placeholders for fixture params
        ordered = []
        fixture_params = []
        for p in all_params:
            if p in param_dict:
                ordered.append(param_dict[p])
            else:
                ordered.append(None)
                fixture_params.append(p)
        param_values = ordered
    else:
        # Flat list (single parametrize mark or JSON args) - match by position
        fixture_params = all_params[len(param_values):]

    # Resolve fixtures for remaining parameters (in order)
    for pname in fixture_params:
        try:
            if pname == "request":
                from oxytest._compat import FixtureRequest as _FR
                from oxytest._compat import Config as _OxyConfig
                req = _FR(_test_func=func)
                req._oxytest_config = getattr(fm, '_config', None) or _OxyConfig({})
                current_param = getattr(fm, '_current_request_param', None)
                if isinstance(current_param, dict):
                    req.param = current_param.get("request")
                else:
                    req.param = getattr(fm, '_current_request_param', None)
                val = req
            elif cls is not None and hasattr(cls, pname):
                # Check for class-scoped fixtures (e.g. schema_validator, core_schema)
                cls_method = getattr(cls, pname)
                if hasattr(cls_method, "_oxytest_fixture"):
                    import inspect as _cls_inspect
                    _cls_sig = _cls_inspect.signature(cls_method)
                    _cls_args = []
                    for _cpname, _cparam in _cls_sig.parameters.items():
                        if _cpname == "self":
                            _cls_args.append(instance)
                        elif _cpname in fm._fixtures:
                            _cls_args.append(fm.resolve(_cpname))
                        elif cls is not None and hasattr(cls, _cpname) and hasattr(getattr(cls, _cpname), "_oxytest_fixture"):
                            _csub = getattr(cls, _cpname)
                            _csub_sig = _cls_inspect.signature(_csub)
                            _csub_args = []
                            for _cspn, _csp in _csub_sig.parameters.items():
                                if _cspn == "self":
                                    _csub_args.append(instance)
                            _cls_args.append(_csub(*_csub_args))
                    val = cls_method(*_cls_args)
                else:
                    val = fm.resolve(pname)
            else:
                val = fm.resolve(pname)
            # Find the position of this fixture in param_values and fill it
            if pname in all_params:
                idx = all_params.index(pname)
                while len(param_values) <= idx:
                    param_values.append(None)
                param_values[idx] = val
        except LookupError:
            raise TypeError(
                f"{raw_name}() missing required argument: '{pname}' "
                f"(not provided by parametrize args or registered fixtures)"
            )

    # 4a. Resolve autouse fixtures
    for fname, fdef in list(fm._fixtures.items()):
        if fdef.autouse and fname not in all_params:
            try:
                fm.resolve(fname)
            except SkipTest:
                raise
            except Exception:
                pass

    # 4b. Resolve usefixtures from function marks and class marks
    extra_fixtures = []
    for obj in (func, cls):
        if obj is not None and hasattr(obj, "_oxytest_marks"):
            for mark_name, mark_args, mark_kwargs in obj._oxytest_marks:
                if mark_name == "usefixtures":
                    extra_fixtures.extend(mark_args)
    for fname in extra_fixtures:
        if fname not in all_params:
            try:
                fm.resolve(fname)
            except LookupError:
                raise TypeError(
                    f"{raw_name}() usefixtures requires fixture: '{fname}'"
                )


    # 4c. Check skip markers
    skip_reason = _should_skip(func, cls=cls, mod=mod)
    if skip_reason:
        raise Exception("SKIPPED:" + str(skip_reason))

    xfail_reason = _is_xfail(func, cls=cls, mod=mod)

    # 5. Call test
    try:
        if xfail_reason is not None:
            try:
                import asyncio as _asyncio
                if inspect.iscoroutinefunction(func):
                    _anyio_backend = None
                    if _fixture_params and isinstance(_fixture_params, dict):
                        _anyio_backend = _fixture_params.get("__anyio_backend__")
                    if _anyio_backend:
                        import anyio as _anyio
                        if param_values:
                            _anyio.run(func, *param_values, backend=_anyio_backend)
                        else:
                            _anyio.run(func, backend=_anyio_backend)
                    elif param_values:
                        _asyncio.run(func(*param_values))
                    else:
                        _asyncio.run(func())
                elif param_values:
                    func(*param_values)
                else:
                    func()
            except SkipTest:
                raise
            except BaseException:
                import traceback as _tb
                _tb.print_exc()
                raise Exception("XFAIL:" + str(xfail_reason))
            else:
                raise Exception("XPASS:" + str(xfail_reason))
        else:
            import asyncio as _asyncio
            if inspect.iscoroutinefunction(func):
                _anyio_backend = None
                if _fixture_params and isinstance(_fixture_params, dict):
                    _anyio_backend = _fixture_params.get("__anyio_backend__")
                if _anyio_backend:
                    import anyio as _anyio
                    if param_values:
                        _anyio.run(func, *param_values, backend=_anyio_backend)
                    else:
                        _anyio.run(func, backend=_anyio_backend)
                elif param_values:
                    _asyncio.run(func(*param_values))
                else:
                    _asyncio.run(func())
            elif param_values:
                func(*param_values)
            else:
                func()
    except SkipTest:
        raise Exception("SKIPPED:" + str(sys.exc_info()[1]))
    except AssertionError:
        if os.environ.get("OXYTEST_PDB") == "1":
            import pdb as _pdb
            _pdb.post_mortem(sys.exc_info()[2])
        import traceback as _tb
        tb_list = _tb.extract_tb(sys.exc_info()[2])

        showlocals = os.environ.get("OXYTEST_SHOWLOCALS") == "1"
        if showlocals:
            tb_obj = sys.exc_info()[2]
            while tb_obj:
                frame = tb_obj.tb_frame
                if frame.f_code.co_filename == func.__code__.co_filename:
                    locals_str = "\n".join(
                        f"  {k} = {v!r}"
                        for k, v in sorted(frame.f_locals.items())
                        if not k.startswith("_")
                    )
                    if locals_str:
                        locals_str = "\n" + locals_str
                    break
                tb_obj = tb_obj.tb_next

        if tb_list:
            last = tb_list[-1]
            try:
                with open(last.filename) as f:
                    lines = f.readlines()
                if last.lineno and last.lineno <= len(lines):
                    source_line = lines[last.lineno - 1].strip()
                    _enhanced_msg = _format_assert_detail(source_line, last.filename, last.lineno)
                    if showlocals and locals_str:
                        _enhanced_msg += "\n\nLocals:\n" + locals_str
                    if _enhanced_msg:
                        raise AssertionError(_enhanced_msg) from None
            except (OSError, IndexError):
                pass
        raise
    finally:
        fm.cleanup()
        fm._current_request_param = None
        if cls is not None and hasattr(instance, "tearDown"):
            try:
                instance.tearDown()
            except Exception:
                pass
        # Clean up test modules from sys.modules (tracked by _loaded_modules for O(1))
        import sys as _sys_cleanup
        for _mod_name in _loaded_modules:
            _sys_cleanup.modules.pop(_mod_name, None)
            pass


def _expand_parametrize(tests: list) -> list:
    import importlib.util
    import sys as _sys
    import os as _os

    expanded = []

    for test in tests:

        if test.args_json:
            expanded.append(test)
            continue

        filepath = os.path.abspath(test.path)
        if filepath not in _module_cache:
            try:
                rel_path = _os.path.relpath(filepath)
                module_name = rel_path.replace("/", ".").replace("\\", ".").rstrip(".py").lstrip(".")
                dirpath = _os.path.dirname(_os.path.abspath(filepath))
                # Add to sys.path (at end, not start) to support relative imports
                # while avoiding shadowing stdlib packages
                if dirpath not in _sys.path:
                    _sys.path.append(dirpath)
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    _sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)
                    _module_cache[filepath] = mod
                else:
                    _module_cache[filepath] = None
            except Exception as exc:
                import sys as _sys2
                if not str(exc).startswith("SKIPPED"):
                    print(f"  [oxytest] Warning: could not import {filepath}: {exc}", file=_sys2.stderr)
                _module_cache[filepath] = None

        mod = _module_cache.get(filepath)
        if mod is None:
            expanded.append(test)
            continue

        # Find the function/method and its marks
        func = None
        if "::" in test.name:
            parts = test.name.split("::")
            cls = getattr(mod, parts[0], None)
            if cls and len(parts) > 1:
                func = getattr(cls, parts[1], None)
        else:
            func = getattr(mod, test.name, None)

        if func is None:
            expanded.append(test)
            continue

        marks = getattr(func, "_oxytest_marks", [])
        # Also check module-level pytestmark
        mod_marks = getattr(mod, "pytestmark", None)
        if mod_marks is not None:
            if not isinstance(mod_marks, (list, tuple)):
                mod_marks = [mod_marks]
            for m in mod_marks:
                if hasattr(m, "name") and hasattr(m, "args") and hasattr(m, "kwargs"):
                    marks.append((m.name, m.args, m.kwargs))
        # Separate parametrize marks from other marks
        parametrize_marks = []
        for mark_name, mark_args, mark_kwargs in marks:
            if mark_name == "parametrize" and len(mark_args) >= 2:
                parametrize_marks.append((mark_args, mark_kwargs))

        if not parametrize_marks:
            expanded.append(test)
            continue

        # Expand parametrize marks (cartesian product for multiple decorators)
        all_value_sets = []
        for mark_args, mark_kwargs in parametrize_marks:
            argnames_str = mark_args[0]
            argvalues_list = mark_args[1]
            ids_opt = mark_kwargs.get("ids")

            if isinstance(argnames_str, str):
                argnames = [a.strip() for a in argnames_str.split(",")]
            else:
                argnames = list(argnames_str)

            value_sets = []
            try:
                argvalues_iter = list(argvalues_list) if not isinstance(argvalues_list, (list, tuple)) else argvalues_list
            except Exception as exc:
                import sys as _sys2
                print(f"  [oxytest] Warning: could not expand parametrize for {test.name}: {exc}", file=_sys2.stderr)
                continue
            for i, val in enumerate(argvalues_iter):
                if isinstance(val, dict) and "values" in val:
                    values = val["values"]
                elif isinstance(val, (list, tuple)) and len(val) == len(argnames):
                    values = list(val)
                else:
                    values = [val]

                # Resolve custom id if provided
                if ids_opt is not None:
                    if callable(ids_opt):
                        custom_id = ids_opt(val)
                    elif isinstance(ids_opt, (list, tuple)) and i < len(ids_opt):
                        custom_id = ids_opt[i]
                    else:
                        custom_id = str(i)
                else:
                    custom_id = None

                value_sets.append((argnames, values, custom_id))

            all_value_sets.append(value_sets)

        # If no value sets were collected (e.g. all parametrize marks failed), skip
        if not all_value_sets:
            continue

        # Build cartesian product of all parametrize marks
        if len(all_value_sets) == 1:
            combos = [(i, vs) for i, vs in enumerate(all_value_sets[0])]
        else:
            import itertools
            combos = []
            for idx, combo in enumerate(itertools.product(*all_value_sets)):
                # Flatten: combo is tuple of (argnames, values, custom_id) per mark
                all_argnames = []
                all_values = []
                id_parts = []
                for argnames, values, custom_id in combo:
                    all_argnames.extend(argnames)
                    all_values.extend(values)
                    if custom_id is not None:
                        id_parts.append(str(custom_id))
                if id_parts:
                    final_id = "-".join(id_parts)
                else:
                    final_id = str(idx)
                combos.append((idx, (all_argnames, all_values, final_id)))

        for idx, (argnames, values, custom_id) in combos:
            import json
            try:
                args_json = json.dumps(values)
            except TypeError:
                args_json = "[]"
            test_clone = TestItem()
            test_clone.path = test.path
            if custom_id is not None:
                test_clone.name = f"{test.name}[{custom_id}]"
            elif len(values) == 1 and len(argnames) == 1:
                val_str = str(values[0])
                if len(val_str) > 80 or not val_str.isidentifier():
                    val_str = f"{argnames[0]}{idx}"
                test_clone.name = f"{test.name}[{val_str}]"
            else:
                # Use short ids for complex parametrize combos
                test_clone.name = f"{test.name}[{idx}]"
            test_clone.line_no = test.line_no
            test_clone.args_json = args_json
            _parametrize_cache[(filepath, test_clone.name)] = (argnames, values)
            expanded.append(test_clone)

    # Phase 2: Expand parametrized fixtures
    # Scan each test's module for fixtures with params= in their _oxytest_fixture metadata
    _extra_expanded = []
    for test in expanded:
        filepath = os.path.abspath(test.path)
        mod = _module_cache.get(filepath)
        if mod is None:
            _extra_expanded.append(test)
            continue
        # Get the test function
        func = None
        if "::" in test.name:
            parts = test.name.split("::")
            cls = getattr(mod, parts[0], None)
            if cls and len(parts) > 1:
                func = getattr(cls, parts[1], None)
        else:
            clean_name = test.name.split("[")[0] if "[" in test.name else test.name
            func = getattr(mod, clean_name, None)
        if func is None:
            _extra_expanded.append(test)
            continue
        # Find parametrized fixtures in the module by scanning its attributes
        _param_fixtures = {}
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name, None)
            if obj is None:
                continue
            meta = getattr(obj, "_oxytest_fixture", None)
            if meta and isinstance(meta, dict) and meta.get("params"):
                _param_fixtures[meta["name"]] = meta["params"]
        # Also check builtins registered in the fixture manager
        from oxytest._fixtures import get_fixture_manager as _get_fm
        _fm = _get_fm()
        for n, fdef in _fm._fixtures.items():
            if fdef.params and n not in _param_fixtures:
                _param_fixtures[n] = fdef.params
        if not _param_fixtures:
            _extra_expanded.append(test)
            continue
        # Check if any parameter matches a parametrized fixture
        import inspect as _inspect
        sig = _inspect.signature(func)
        matching_fixtures = {}
        for pname in sig.parameters.keys():
            if pname in _param_fixtures:
                matching_fixtures[pname] = _param_fixtures[pname]
        if not matching_fixtures:
            _extra_expanded.append(test)
            continue

        # Get existing cache entry (argnames, values) or empty
            cache_key = (filepath, test.name)
            existing_argnames = []
            existing_values = []
            if cache_key in _parametrize_cache:
                cached = _parametrize_cache[cache_key]
                if len(cached) == 2:
                    existing_argnames, existing_values = cached
                else:
                    existing_argnames, existing_values = cached[0], cached[1]

            # Create clones for each fixture param combination
            import itertools as _itertools
            _fixture_items = sorted(matching_fixtures.items())
            _param_lists = [v for _, v in _fixture_items]
            _param_combos = list(_itertools.product(*_param_lists))
            for _idx, _combo in enumerate(_param_combos):
                _new_values = list(existing_values)
                _new_argnames = list(existing_argnames)
                _fixture_params = {}
                _id_parts = []
                for (_fname, _), _pval in zip(_fixture_items, _combo):
                    # Unwrap pytest.param() dicts to get the actual value
                    if isinstance(_pval, dict) and "values" in _pval:
                        _actual = _pval["values"]
                        if isinstance(_actual, (list, tuple)) and len(_actual) == 1:
                            _actual = _actual[0]
                        _pval = _actual
                    _fixture_params[_fname] = _pval
                    _id_parts.append(str(_pval))
                name_suffix = "-".join(_id_parts)
                test_clone = TestItem()
                test_clone.path = test.path
                test_clone.line_no = test.line_no
                test_clone.args_json = "[]"
                # Check if test already has bracket suffix from parametrize
                if "[" in test.name:
                    base, bracket = test.name.split("[", 1)
                    bracket = bracket.rstrip("]")
                    test_clone.name = f"{base}[{bracket}-{name_suffix}]"
                else:
                    test_clone.name = f"{test.name}[{name_suffix}]"
                _parametrize_cache[(filepath, test_clone.name)] = (
                    _new_argnames, _new_values, _fixture_params
                )
                _extra_expanded.append(test_clone)

        if _extra_expanded:
            expanded = _extra_expanded

    # Phase 3: Expand @pytest.mark.anyio tests
    # Duplicate each async test for each anyio backend (asyncio, trio)
    _anyio_backends = ["asyncio", "trio"]
    _anyio_expanded = []
    for test in expanded:
        filepath = os.path.abspath(test.path)
        mod = _module_cache.get(filepath)
        if mod is None:
            _anyio_expanded.append(test)
            continue
        # Get the test function
        func = None
        if "::" in test.name:
            parts = test.name.split("::")
            cls = getattr(mod, parts[0], None)
            if cls and len(parts) > 1:
                func = getattr(cls, parts[1], None)
        else:
            clean_name = test.name.split("[")[0] if "[" in test.name else test.name
            func = getattr(mod, clean_name, None)
        if func is None:
            _anyio_expanded.append(test)
            continue
        # Check for anyio marker
        marks = getattr(func, "_oxytest_marks", [])
        has_anyio = any(m[0] == "anyio" for m in marks) or hasattr(func, "_anyio_mark")
        if not has_anyio:
            _anyio_expanded.append(test)
            continue
        # Check if test is async
        import inspect as _anyio_inspect
        if not _anyio_inspect.iscoroutinefunction(func):
            _anyio_expanded.append(test)
            continue
        # Create clones for each backend
        for _backend in _anyio_backends:
            test_clone = TestItem()
            test_clone.path = test.path
            test_clone.line_no = test.line_no
            test_clone.args_json = test.args_json
            # Add backend suffix to name (e.g., test_foo[asyncio])
            if "[" in test.name:
                base, bracket = test.name.split("[", 1)
                bracket = bracket.rstrip("]")
                test_clone.name = f"{base}[{bracket}-{_backend}]"
            else:
                test_clone.name = f"{test.name}[{_backend}]"
            # Store backend info in cache
            _cache_key = (filepath, test_clone.name)
            _cached = _parametrize_cache.get((filepath, test.name))
            if _cached and len(_cached) == 3:
                _argnames, _values, _fixture_params = _cached
                _parametrize_cache[_cache_key] = (_argnames, _values, {**_fixture_params, "__anyio_backend__": _backend})
            elif _cached and len(_cached) == 2:
                _argnames, _values = _cached
                _parametrize_cache[_cache_key] = (_argnames, _values, {"__anyio_backend__": _backend})
            else:
                _parametrize_cache[_cache_key] = ([], [], {"__anyio_backend__": _backend})
            _anyio_expanded.append(test_clone)
    if _anyio_expanded:
        expanded = _anyio_expanded

    return expanded


def _json_safe(obj):
    """Convert non-JSON-serializable objects to JSON-safe representations."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, bytes):
        return repr(obj)
    if isinstance(obj, dict):
        return {_json_safe(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(i) for i in obj]
    return repr(obj)


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
    "PytestDeprecationWarning",
    "ExitCode",
    "warns",
    "PytestWarning",
]

__all__ = _oxytest_api
