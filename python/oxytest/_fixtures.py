import os
import sys
import io
import tempfile
import pathlib
import shutil
import inspect
import asyncio
from typing import Any, Callable, Dict, Generator, Optional, cast


class FixtureDef:
    def __init__(
        self,
        func: Callable,
        scope: str = "function",
        params: Optional[list] = None,
        autouse: bool = False,
        name: Optional[str] = None,
    ):
        self.func = func
        self.scope = scope
        self.params = params
        self.autouse = autouse
        self.name = name or getattr(func, "__name__", str(func))
        self.cached_value = None
        self.cached_scope = None


class FixtureManager:
    def __init__(self):
        self._fixtures: Dict[str, FixtureDef] = {}
        self._cache: Dict[str, Any] = {}
        self._active_scopes: Dict[str, str] = {}
        self._generators: Dict[str, Generator] = {}
        self._async_generators: Dict[str, Any] = {}
        self._resolved_fixtures: list[Any] = []
        self._tmpdirs: list = []
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.current_test_func = None
        self._config = None
        self._current_request_param = None
        self._setup_builtins()

    def _setup_builtins(self):
        self.register_builtin("tmp_path", self._fixture_tmp_path, scope="function")
        self.register_builtin("tmpdir", self._fixture_tmpdir, scope="function")
        self.register_builtin("capsys", self._fixture_capsys, scope="function")
        self.register_builtin("capfd", self._fixture_capfd, scope="function")
        self.register_builtin("monkeypatch", self._fixture_monkeypatch, scope="function")
        self.register_builtin("mocker", self._fixture_mocker, scope="function")
        self.register_builtin("benchmark", self._fixture_benchmark, scope="function")
        self.register_builtin("create_module", self._fixture_create_module, scope="function")
        self.register_builtin("pytestconfig", self._fixture_pytestconfig, scope="session")
        self._setup_third_party_fixtures()

    def _setup_third_party_fixtures(self):
        """Register fixtures commonly provided by third-party pytest plugins."""
        self._fixtures["eval_example"] = FixtureDef(self._fixture_eval_example, scope="function", name="eval_example")
        self._fixtures["benchmark"] = FixtureDef(self._fixture_benchmark, scope="function", name="benchmark")

    def _fixture_eval_example(self):
        """Lazy import of pytest_examples fixture."""
        try:
            from pytest_examples import EvalExample
            return EvalExample()
        except Exception:
            return None

    def register_builtin(self, name: str, func: Callable, scope: str = "function"):
        self._fixtures[name] = FixtureDef(func, scope=scope, name=name)

    def register(self, func: Callable):
        if hasattr(func, "_oxytest_fixture"):
            meta: dict[str, Any] = cast("dict[str, Any]", func._oxytest_fixture)
            self._fixtures[meta["name"]] = FixtureDef(
                func,
                scope=meta["scope"],
                params=meta["params"],
                autouse=meta["autouse"],
                name=meta["name"],
            )

    def register_from_module(self, module):
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if hasattr(obj, "_oxytest_fixture"):
                self.register(obj)
            elif hasattr(obj, "_pytestfixturefunction") or (hasattr(obj, "__wrapped__") and hasattr(obj, "name")):
                if hasattr(obj, "_fixture_function"):
                    wrapped = obj._fixture_function
                elif hasattr(obj, "__wrapped__"):
                    wrapped = obj.__wrapped__
                else:
                    continue
                if hasattr(wrapped, "__func__"):
                    wrapped = wrapped.__func__
                else:
                    continue
                if not callable(wrapped) or hasattr(wrapped, "_oxytest_fixture"):
                    continue
                mod = getattr(wrapped, "__module__", "")
                if mod.startswith(("pytest_benchmark", "pytest_codspeed")):
                    continue
                scope = "function"
                params = None
                autouse = False
                if hasattr(obj, "_fixture_function_marker"):
                    marker = obj._fixture_function_marker
                    scope = getattr(marker, "scope", "function") or "function"
                    params = getattr(marker, "params", None)
                    autouse = getattr(marker, "autouse", False)
                wrapped._oxytest_fixture = {
                    "scope": scope,
                    "params": params,
                    "autouse": autouse,
                    "name": attr_name,
                }
                self.register(wrapped)

    def resolve(self, name: str, scope: str = "function", _resolving: Optional[set] = None) -> Any:
        if _resolving is None:
            _resolving = set()
        if name in _resolving:
            raise LookupError(f"Circular fixture dependency detected for {name!r}")
        _resolving.add(name)
        try:
            return self._resolve_impl(name, scope, _resolving)
        finally:
            _resolving.discard(name)

    def _resolve_impl(self, name: str, scope: str = "function", _resolving: Optional[set] = None) -> Any:
        setup_show = os.environ.get("OXYTEST_SETUP_SHOW") == "1"
        if setup_show:
            os.write(2, f"SETUP    {name}\n".encode())
        if setup_show:
            os.write(2, f"SETUP    {name}\n".encode())
        if name in self._cache:
            cached_scope = self._active_scopes.get(name)
            if cached_scope == "session" or cached_scope == scope:
                return self._cache[name]

        if name not in self._fixtures:
            raise LookupError(f"Fixture {name!r} not found")

        fdef = self._fixtures[name]

        # Resolve fixture function arguments recursively
        import inspect as _inspect
        fixture_sig = _inspect.signature(fdef.func)
        fixture_args = []
        for pname, param in fixture_sig.parameters.items():
            if pname == "self":
                continue
            if pname == "request":
                from oxytest._compat import FixtureRequest
                from oxytest._compat import Config as _OxyConfig
                req = FixtureRequest(scope=scope, _test_func=self.current_test_func)
                req._oxytest_config = self._config or _OxyConfig({})
                if isinstance(self._current_request_param, dict):
                    req.param = self._current_request_param.get(name)
                else:
                    req.param = self._current_request_param
                fixture_args.append(req)
            elif pname in self._fixtures:
                sub_value = self.resolve(pname, scope=scope, _resolving=_resolving)
                fixture_args.append(sub_value)
            elif param.default is not param.empty:
                fixture_args.append(param.default)
            else:
                # Skip unknown parameters - they may be provided by parametrization
                pass

        if inspect.isasyncgenfunction(fdef.func):
            agen = fdef.func(*fixture_args)
            try:
                value = self._loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                value = None
            self._async_generators[name] = agen
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (async yield)\n".encode())
        elif inspect.iscoroutinefunction(fdef.func):
            value = self._loop.run_until_complete(fdef.func(*fixture_args))
        else:
            value = fdef.func(*fixture_args)

        if inspect.isgenerator(value):
            try:
                yielded = next(value)
            except StopIteration:
                yielded = None
            self._generators[name] = value
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (yield)\n".encode())
            value = yielded

        if hasattr(value, "start") and callable(value.start):
            value.start()  # ty: ignore

        if fdef.scope in ("session", "module", "class"):
            self._cache[name] = value
            self._active_scopes[name] = fdef.scope

        self._resolved_fixtures.append(value)
        return value

    def cleanup(self, scope: str = "function"):
        setup_show = os.environ.get("OXYTEST_SETUP_SHOW") == "1"
        for name, agen in self._async_generators.items():
            try:
                self._loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                pass
            self._loop.run_until_complete(agen.aclose())
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (async yield)\n".encode())
        self._async_generators.clear()
        for name, gen in self._generators.items():
            try:
                next(gen)
            except StopIteration:
                pass
            gen.close()
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (yield)\n".encode())
        self._generators.clear()
        for value in self._resolved_fixtures:
            if hasattr(value, "stop"):
                try:
                    value.stop()
                except Exception:
                    pass
                if setup_show and hasattr(value, "__class__"):
                    os.write(2, f"  TEARDOWN {value.__class__.__name__} (stop)\n".encode())
        self._resolved_fixtures.clear()
        for name, value in self._cache.items():
            if hasattr(value, "stop"):
                try:
                    value.stop()
                except Exception:
                    pass
        self._cache.clear()
        self._active_scopes.clear()
        for tmpdir in self._tmpdirs:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        self._tmpdirs.clear()

    def finish_fixture(self, value):
        if inspect.isgenerator(value):
            try:
                next(value)
            except StopIteration:
                pass
            value.close()
        if hasattr(value, "stop"):
            value.stop()

    def _fixture_tmp_path(self) -> pathlib.Path:
        tmpdir = tempfile.mkdtemp(prefix="oxytest_")
        self._tmpdirs.append(tmpdir)
        return pathlib.Path(tmpdir)

    def _fixture_tmpdir(self):
        tmpdir = tempfile.mkdtemp(prefix="oxytest_")
        self._tmpdirs.append(tmpdir)
        return tmpdir

    def _fixture_capsys(self):
        cf = _CaptureFixture()
        cf.start()
        yield cf
        cf.stop()

    def _fixture_capfd(self):
        return _CaptureFDFixture()

    def _fixture_monkeypatch(self):
        return MonkeyPatch()

    def _fixture_mocker(self):
        m = MockerFixture()
        yield m
        m.stopall()

    def _fixture_benchmark(self):
        class _BenchmarkStub:
            def __call__(self, fn, *args, **kwargs):
                return fn(*args, **kwargs)
        return _BenchmarkStub()

    def _fixture_create_module(self):
        """Stub for create_module fixture from _pytest.assertion.rewrite."""
        import types as _types
        def _create_module(func=None):
            if func is None:
                return _create_module
            ns = {}
            exec(func.__code__, ns)
            mod = _types.ModuleType(func.__name__)
            mod.__dict__.update(ns)
            return mod
        return _create_module

    def _fixture_pytestconfig(self):
        from oxytest._compat import Config as _OxyConfig
        return self._config or _OxyConfig({})


class MockerFixture:
    """Simplified mock fixture compatible with pytest-mock's mocker fixture."""

    def __init__(self):
        import unittest.mock as _mock
        self._mock = _mock
        self._patches = []

    @property
    def patch(self):
        """Returns a callable that auto-starts patches and tracks them for cleanup."""
        import unittest.mock as _um
        _mocker = self
        class _PatchProxy:
            def __call__(_self, target, *args, **kwargs):
                p = _um.patch(target, *args, **kwargs)
                _mocker._patches.append(p)
                return p.start()
            @property
            def dict(_self):
                return _um.patch.dict
            @property
            def object(_self):
                return _um.patch.object
        return _PatchProxy()

    def stopall(self):
        for p in self._patches:
            p.stop()
        self._patches.clear()

    def stub(self, name=None):
        import unittest.mock as _mock
        return _mock.MagicMock(name=name, spec=_mock.MagicMock)

    def spy(self, obj, name):
        orig = getattr(obj, name)
        class _Spy:
            spy_return: Any = None
            spy_exception: Any = None
            def __call__(self, *args, **kwargs):
                try:
                    r = orig(*args, **kwargs)
                    self.spy_return = r
                    return r
                except Exception as e:
                    self.spy_exception = e
                    raise
        spy = _Spy()
        setattr(obj, name, spy)
        return spy


class _CaptureFixture:
    def __init__(self):
        self._old_stdout = None
        self._old_stderr = None
        self._stringio = io.StringIO()

    def start(self):
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self._stringio
        sys.stderr = self._stringio

    def stop(self):
        if self._old_stdout is not None:
            sys.stdout = self._old_stdout
        if self._old_stderr is not None:
            sys.stderr = self._old_stderr

    def readouterr(self):
        out = self._stringio.getvalue()
        class _CaptureResult:
            def __init__(self, out_val, err_val):
                self.out = out_val
                self.err = err_val
            def __getitem__(self, i):
                return (self.out, self.err)[i]
            def __iter__(self):
                return iter((self.out, self.err))
        return _CaptureResult(out, "")


class _CaptureFDFixture:
    def __init__(self):
        self._captured = None

    def start(self):
        self._captured = io.StringIO()

    def stop(self):
        pass

    def readouterr(self):
        return (self._captured.getvalue() if self._captured else ""), ""


class MonkeyPatch:
    def __init__(self):
        self._saved = []

    def setattr(self, target, name, value, raising=True):
        # Support dotted string target like pytest: setattr("module.attr", value)
        if isinstance(target, str):
            parts = target.rsplit(".", 1)
            if len(parts) == 2:
                import importlib
                mod_name, attr_name = parts
                try:
                    target = importlib.import_module(mod_name)
                except ImportError:
                    target = __import__(mod_name)
                return self.setattr(target, attr_name, value, raising=raising)
            name = target
            target = __import__("builtins")
        try:
            old = getattr(target, name, _NOT_SET)
        except AttributeError:
            if raising:
                raise
            return
        try:
            setattr(target, name, value)
        except (AttributeError, TypeError):
            if raising:
                raise
            return
        self._saved.append(("setattr", target, name, old))

    def delattr(self, target, name, raising=True):
        try:
            old = getattr(target, name, _NOT_SET)
        except AttributeError:
            if raising:
                raise
            return
        try:
            delattr(target, name)
        except (AttributeError, TypeError):
            if raising:
                raise
            return
        self._saved.append(("setattr", target, name, old))

    def setitem(self, mapping, key, value):
        old = mapping.get(key, _NOT_SET)
        self._saved.append(("setitem", mapping, key, old))
        mapping[key] = value

    def delitem(self, mapping, key):
        old = mapping.get(key, _NOT_SET)
        self._saved.append(("setitem", mapping, key, old))
        del mapping[key]

    def setenv(self, name, value, prepend=None):
        old = os.environ.get(name, _NOT_SET)
        self._saved.append(("env", name, old))
        os.environ[name] = value

    def delenv(self, name, raising=True):
        old = os.environ.get(name, _NOT_SET)
        self._saved.append(("env", name, old))
        del os.environ[name]

    def chdir(self, path):
        old = os.getcwd()
        self._saved.append(("cwd", old))
        os.chdir(path)

    def syspath_prepend(self, path):
        import sys as _sys
        self._saved.append(("syspath", path))
        _sys.path.insert(0, path)

    def undo(self):
        import sys as _sys
        for item in reversed(self._saved):
            if item[0] == "env":
                name, old = item[1], item[2]
                if old is _NOT_SET:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = old
            elif item[0] == "cwd":
                old = item[1]
                os.chdir(old)
            elif item[0] == "syspath":
                path = item[1]
                if path in _sys.path:
                    _sys.path.remove(path)
            elif item[0] == "setattr":
                _, target, name, old = item
                if old is _NOT_SET:
                    if hasattr(target, name):
                        delattr(target, name)
                else:
                    setattr(target, name, old)
            elif item[0] == "setitem":
                _, mapping, key, old = item
                if old is _NOT_SET:
                    mapping.pop(key, None)
                else:
                    mapping[key] = old
        self._saved.clear()


_NOT_SET = object()


_fixture_manager = FixtureManager()


def get_fixture_manager() -> FixtureManager:
    return _fixture_manager


def register_fixture(func):
    _fixture_manager.register(func)


fixture_registry = _fixture_manager


__all__ = [
    "FixtureDef",
    "FixtureManager",
    "MonkeyPatch",
    "_CaptureFixture",
    "_CaptureFDFixture",
    "get_fixture_manager",
    "register_fixture",
    "fixture_registry",
]
