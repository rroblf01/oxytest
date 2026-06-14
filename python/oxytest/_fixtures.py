import os
import sys
import io
import tempfile
import pathlib
import shutil
import inspect
import asyncio
from typing import Any, Callable, Dict, Generator, Optional


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
        self.name = name or func.__name__
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

    def register_builtin(self, name: str, func: Callable, scope: str = "function"):
        self._fixtures[name] = FixtureDef(func, scope=scope, name=name)

    def register(self, func: Callable):
        if hasattr(func, "_oxytest_fixture"):
            meta = func._oxytest_fixture
            self._fixtures[meta["name"]] = FixtureDef(
                func,
                scope=meta["scope"],
                params=meta["params"],
                autouse=meta["autouse"],
                name=meta["name"],
            )

    def register_from_module(self, module):
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            obj = getattr(module, attr_name)
            if hasattr(obj, "_oxytest_fixture"):
                self.register(obj)

    def resolve(self, name: str, scope: str = "function", _resolving: set = None) -> Any:
        if _resolving is None:
            _resolving = set()
        if name in _resolving:
            raise LookupError(f"Circular fixture dependency detected for {name!r}")
        _resolving.add(name)
        try:
            return self._resolve_impl(name, scope, _resolving)
        finally:
            _resolving.discard(name)

    def _resolve_impl(self, name: str, scope: str = "function", _resolving: set = None) -> Any:
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

        if hasattr(value, "start"):
            value.start()

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
        return _CaptureFixture()

    def _fixture_capfd(self):
        return _CaptureFDFixture()

    def _fixture_monkeypatch(self):
        return MonkeyPatch()


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
        return out, ""


class _CaptureFDFixture:
    def __init__(self):
        self._captured = None

    def start(self):
        import faulthandler
        self._captured = io.StringIO()
        faulthandler.enable(file=self._captured)

    def stop(self):
        if self._captured:
            import faulthandler
            faulthandler.disable()

    def readouterr(self):
        return self._captured.getvalue() if self._captured else "", ""


class MonkeyPatch:
    def __init__(self):
        self._saved = []

    def setattr(self, target, name, value, raising=True):
        old = getattr(target, name, _NOT_SET)
        self._saved.append((target, name, old))
        setattr(target, name, value)

    def delattr(self, target, name, raising=True):
        old = getattr(target, name, _NOT_SET)
        self._saved.append((target, name, old))
        delattr(target, name)

    def setitem(self, mapping, key, value):
        old = mapping.get(key, _NOT_SET)
        self._saved.append((mapping, key, old))
        mapping[key] = value

    def delitem(self, mapping, key):
        old = mapping.get(key, _NOT_SET)
        self._saved.append((mapping, key, old))
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

    def undo(self):
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
            elif len(item) == 3:
                target, name, old = item
                if old is _NOT_SET:
                    if hasattr(target, name):
                        delattr(target, name)
                else:
                    setattr(target, name, old)
            else:
                target, key, old = item
                if old is _NOT_SET:
                    target.pop(key, None)
                else:
                    target[key] = old
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
