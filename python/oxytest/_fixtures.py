import os
import sys
import io
import tempfile
import pathlib
import shutil
from contextlib import contextmanager
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
        self._tmpdirs: list = []
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

    def resolve(self, name: str, scope: str = "function") -> Any:
        if name in self._cache:
            cached_scope = self._active_scopes.get(name)
            if cached_scope == "session" or cached_scope == scope:
                return self._cache[name]

        if name not in self._fixtures:
            raise LookupError(f"Fixture {name!r} not found")

        fdef = self._fixtures[name]
        value = fdef.func()

        if fdef.scope in ("session", "module", "class"):
            self._cache[name] = value
            self._active_scopes[name] = fdef.scope

        return value

    def cleanup(self, scope: str = "function"):
        for tmpdir in self._tmpdirs:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        self._tmpdirs.clear()

    def _fixture_tmp_path(self) -> pathlib.Path:
        tmpdir = tempfile.mkdtemp(prefix="oxytest_")
        self._tmpdirs.append(tmpdir)
        return pathlib.Path(tmpdir)

    def _fixture_tmpdir(self):
        import py  # local import to avoid dependency
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

    def undo(self):
        for item in reversed(self._saved):
            if item[0] == "env":
                name, old = item[1], item[2]
                if old is _NOT_SET:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = old
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
