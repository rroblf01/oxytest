import os
import sys
import io
import tempfile
import pathlib
import shutil
import inspect
import asyncio
import logging
import importlib
import threading
from typing import Any, Callable, Dict, Generator, Optional, cast, Union
from contextlib import contextmanager


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
        self._cache: Dict[Union[str, tuple], Any] = {}
        self._active_scopes: Dict[Union[str, tuple], str] = {}
        self._generators: Dict[str, Generator] = {}
        self._async_generators: Dict[str, Any] = {}
        self._resolved_fixtures: list[Any] = []
        self._tmpdirs: list = []
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.current_test_func = None
        self._config = None
        self._current_request_param = None
        self._current_class = None
        self._current_instance = None
        self._setup_builtins()
        self._registered_files: set = set()
        self._autouse_list: Optional[list] = None

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
        self.register_builtin("caplog", self._fixture_caplog, scope="function")
        self.register_builtin("record_property", self._fixture_record_property, scope="function")
        self.register_builtin("record_xml_attribute", self._fixture_record_xml_attribute, scope="function")
        self.register_builtin("record_testsuite_property", self._fixture_record_testsuite_property, scope="function")
        self.register_builtin("cache", self._fixture_cache, scope="session")
        self.register_builtin("subtests", self._fixture_subtests, scope="function")
        self.register_builtin("capsysbinary", self._fixture_capsysbinary, scope="function")
        self.register_builtin("capfdbinary", self._fixture_capfdbinary, scope="function")
        self.register_builtin("recwarn", self._fixture_recwarn, scope="function")
        self.register_builtin("doctest_namespace", self._fixture_doctest_namespace, scope="session")
        self.register_builtin("tmp_path_factory", self._fixture_tmp_path_factory, scope="session")
        self._setup_third_party_fixtures()

    def _setup_third_party_fixtures(self):
        """Register fixtures commonly provided by third-party pytest plugins."""
        self._fixtures["eval_example"] = FixtureDef(self._fixture_eval_example, scope="function", name="eval_example")
        self._fixtures["benchmark"] = FixtureDef(self._fixture_benchmark, scope="function", name="benchmark")

    def _fixture_eval_example(self):
        """Lazy import of pytest_examples fixture."""
        try:
            from pytest_examples import EvalExample
            return EvalExample(tmp_path=pathlib.Path(tempfile.mkdtemp(prefix="oxytest_eval_")), pytest_request=None)  # type: ignore
        except Exception:
            return None

    def register_builtin(self, name: str, func: Callable, scope: str = "function"):
        self._fixtures[name] = FixtureDef(func, scope=scope, name=name)
        self._autouse_list = None

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
            self._autouse_list = None

    def register_from_module(self, module):
        mod_id = id(module)
        if mod_id in self._registered_files:
            return
        self._registered_files.add(mod_id)
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
                if not callable(wrapped) or hasattr(wrapped, "_oxytest_fixture"):
                    continue
                mod = getattr(wrapped, "__module__", "")
                if mod.startswith(("pytest_benchmark", "pytest_codspeed")):
                    continue
                scope = "function"
                params = None
                autouse = False
                fixture_name = attr_name
                if hasattr(obj, "_fixture_function_marker"):
                    marker = obj._fixture_function_marker
                    scope = getattr(marker, "scope", "function") or "function"
                    raw_params = getattr(marker, "params", None)
                    params = (
                        [_unwrap_param(p) for p in raw_params]
                        if raw_params is not None
                        else None
                    )
                    autouse = getattr(marker, "autouse", False)
                    marker_name = getattr(marker, "name", None)
                    if marker_name is not None:
                        fixture_name = marker_name
                wrapped._oxytest_fixture = {
                    "scope": scope,
                    "params": params,
                    "autouse": autouse,
                    "name": fixture_name,
                }
                self.register(wrapped)

    def clear_registered(self):
        """Clear the set of known module ids (for cross-run hygiene)."""
        self._registered_files.clear()

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
        # For class-scoped fixtures, use a composite cache key
        _cache_key = name
        if scope == "class" and self._current_class is not None:
            _cache_key = (name, self._current_class)
        if _cache_key in self._cache:
            cached_scope = self._active_scopes.get(_cache_key)
            if cached_scope == "session" or cached_scope == scope:
                return self._cache[_cache_key]

        if name not in self._fixtures:
            raise LookupError(f"Fixture {name!r} not found")

        fdef = self._fixtures[name]

        # Resolve fixture function arguments recursively
        fixture_sig = inspect.signature(fdef.func)
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
            if fdef.scope == "class" and self._current_class is not None:
                _ckey = (name, self._current_class)
                self._active_scopes[_ckey] = fdef.scope
            else:
                _ckey = name
                self._active_scopes[name] = fdef.scope
            self._cache[_ckey] = value

        self._resolved_fixtures.append(value)
        return value

    def cleanup(self, scope: str = "function"):
        setup_show = os.environ.get("OXYTEST_SETUP_SHOW") == "1"
        # Only teardown generators that match the given scope
        _gen_names = list(self._generators.keys())
        for name in _gen_names:
            _scope = self._active_scopes.get(name, "function")
            if scope != "session" and _scope in ("session", "module"):
                continue
            gen = self._generators[name]
            try:
                next(gen)
            except StopIteration:
                pass
            gen.close()
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (yield)\n".encode())
            del self._generators[name]
        _agen_names = list(self._async_generators.keys())
        for name in _agen_names:
            _scope = self._active_scopes.get(name, "function")
            if scope != "session" and _scope in ("session", "module"):
                continue
            agen = self._async_generators[name]
            try:
                self._loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                pass
            self._loop.run_until_complete(agen.aclose())
            if setup_show:
                os.write(2, f"  TEARDOWN {name} (async yield)\n".encode())
            del self._async_generators[name]
        for value in self._resolved_fixtures:
            if hasattr(value, "stop"):
                try:
                    value.stop()
                except Exception:
                    pass
                if setup_show and hasattr(value, "__class__"):
                    os.write(2, f"  TEARDOWN {value.__class__.__name__} (stop)\n".encode())
        self._resolved_fixtures.clear()
        # Clear cache entries NOT matching the requested scope
        _keys_to_keep = {}
        for name, value in self._cache.items():
            _scope = self._active_scopes.get(name, "function")
            if scope != "session" and _scope == "session":
                _keys_to_keep[name] = value
            elif hasattr(value, "stop"):
                try:
                    value.stop()
                except Exception:
                    pass
        self._cache = _keys_to_keep
        self._active_scopes = {
            k: v for k, v in self._active_scopes.items() if k in _keys_to_keep
        }
        for tmpdir in self._tmpdirs:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass
        self._tmpdirs.clear()

    def cleanup_all(self):
        """Cleanup ALL fixtures including session-scoped generators.
        Called at the end of the test session."""
        for name, gen in self._generators.items():
            try:
                next(gen)
            except StopIteration:
                pass
            gen.close()
        self._generators.clear()
        for name, agen in self._async_generators.items():
            try:
                self._loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                pass
            self._loop.run_until_complete(agen.aclose())
        self._async_generators.clear()
        for value in self._cache.values():
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
        base = getattr(self, '_config', None)
        base_dir = (getattr(base, 'basetemp', None) or getattr(base, '_basetemp', None)) if base else None
        tmpdir = tempfile.mkdtemp(prefix="oxytest_", dir=base_dir)
        self._tmpdirs.append(tmpdir)
        return pathlib.Path(tmpdir)

    def _fixture_tmpdir(self):
        base = getattr(self, '_config', None)
        base_dir = (getattr(base, 'basetemp', None) or getattr(base, '_basetemp', None)) if base else None
        tmpdir = tempfile.mkdtemp(prefix="oxytest_", dir=base_dir)
        self._tmpdirs.append(tmpdir)
        return tmpdir

    def _fixture_capsys(self):
        cf = _CaptureFixture()
        cf.start()
        yield cf
        cf.stop()

    def _fixture_capsysbinary(self):
        cf = _CaptureFixture(binary=True)
        cf.start()
        yield cf
        cf.stop()

    def _fixture_capfd(self):
        return _CaptureFDFixture()

    def _fixture_capfdbinary(self):
        return _CaptureFDFixture(binary=True)

    def _fixture_recwarn(self):
        return _WarningsRecorder()

    def _fixture_doctest_namespace(self):
        return {}

    def _fixture_tmp_path_factory(self):
        return _TempPathFactory()

    def _fixture_monkeypatch(self):
        mp = MonkeyPatch()
        yield mp
        mp.undo()

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

    def _fixture_caplog(self):
        return _CaplogFixture()

    def _fixture_record_property(self):
        return _RecordPropertyFixture()

    def _fixture_record_xml_attribute(self):
        return _RecordXmlAttributeFixture()

    def _fixture_record_testsuite_property(self):
        return _RecordTestsuitePropertyFixture()

    def _fixture_cache(self):
        return _CacheFixture()

    def _fixture_subtests(self):
        return _SubTestFixture()


class _RecordPropertyFixture:
    def __init__(self):
        self.properties = []
    def __call__(self, name, value):
        self.properties.append((name, value))

class _RecordXmlAttributeFixture:
    def __init__(self):
        self.attributes = {}
    def __call__(self, name, value):
        self.attributes[name] = value

class _RecordTestsuitePropertyFixture:
    def __init__(self):
        self.properties = []
    def __call__(self, name, value):
        self.properties.append((name, value))

class _CacheFixture:
    def __init__(self):
        self._store = {}
    def get(self, key, default=None):
        return self._store.get(key, default)
    def set(self, key, value):
        self._store[key] = value
    def clear(self):
        self._store.clear()


class _TempPathFactory:
    def __init__(self):
        self._basetemp = None

    def mktemp(self, basename: str) -> pathlib.Path:
        import tempfile as _tf
        tmpdir = _tf.mkdtemp(prefix=f"{basename}_")
        return pathlib.Path(tmpdir)

    def getbasetemp(self) -> pathlib.Path:
        if self._basetemp is None:
            import tempfile as _tf
            self._basetemp = pathlib.Path(_tf.mkdtemp(prefix="oxytest_"))
        return self._basetemp


class _SubTestFixture:
    """Fixture that supports subtests via ``with subtests.test(...)`` context manager."""
    def __init__(self):
        self._failures = []

    def test(self, **kwargs):
        return _SubTestContext(self, kwargs)


class _SubTestContext:
    def __init__(self, fixture, kwargs):
        self._fixture = fixture
        self._kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, AssertionError):
            msg = str(exc_val)
            params = ", ".join(f"{k}={v!r}" for k, v in self._kwargs.items())
            self._fixture._failures.append(f"subtest ({params}): {msg}")
            return True  # Suppress the exception
        return False


class _CaplogFixture:
    """Capture log records, like pytest's caplog fixture."""

    def __init__(self):
        self._handler = _CaplogHandler()
        logging.getLogger().addHandler(self._handler)
        self._old_levels = {}

    @property
    def records(self):
        return self._handler.records

    @property
    def text(self):
        return "\n".join(self.messages)

    @property
    def messages(self):
        return [r.getMessage() for r in self._handler.records]

    @property
    def record_tuples(self):
        return [(r.name, r.levelno, r.getMessage()) for r in self._handler.records]

    def clear(self):
        self._handler.records.clear()

    def set_level(self, level, logger=None):
        logger = logger or None
        log = logging.getLogger(logger)
        key = logger or "root"
        if key not in self._old_levels:
            self._old_levels[key] = log.level
        log.setLevel(level)

    def at_level(self, level, logger=None):
        import contextlib
        @contextlib.contextmanager
        def _ctx():
            self.set_level(level, logger=logger)
            try:
                yield
            finally:
                self._restore_level(logger)
        return _ctx()

    def _restore_level(self, logger=None):
        key = logger or "root"
        if key in self._old_levels:
            logging.getLogger(logger).setLevel(self._old_levels.pop(key))

    def __del__(self):
        logging.getLogger().removeHandler(self._handler)


class _CaplogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


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
    def __init__(self, binary=False):
        self._binary = binary
        self._old_stdout = None
        self._old_stderr = None
        self._buffer = io.BytesIO() if binary else io.StringIO()

    def start(self):
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        if self._binary:
            import io as _io_bin
            self._stringio = _io_bin.TextIOWrapper(self._buffer)  # type: ignore
            sys.stdout = self._stringio
            sys.stderr = self._stringio
        else:
            self._stringio = self._buffer
            sys.stdout = self._buffer
            sys.stderr = self._buffer

    def stop(self):
        if self._old_stdout is not None:
            sys.stdout = self._old_stdout
        if self._old_stderr is not None:
            sys.stderr = self._old_stderr

    def readouterr(self):
        if self._binary:
            self._buffer.seek(0)
            out = self._buffer.read()
            err = b""
        else:
            out = self._buffer.getvalue() if hasattr(self, '_buffer') else ""
            err = ""
        class _CaptureResult:
            def __init__(self, out_val, err_val):
                self.out = out_val
                self.err = err_val
            def __getitem__(self, i):
                return (self.out, self.err)[i]
            def __iter__(self):
                return iter((self.out, self.err))
        return _CaptureResult(out, err)


class _WarningsRecorder:
    def __init__(self):
        import warnings
        self._warnings = warnings.catch_warnings(record=True)
        self._list = self._warnings.__enter__()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self._warnings.__exit__(*exc_info)

    @property
    def list(self):
        return self._list

    def __getitem__(self, i):
        return self._list[i]

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)

    def pop(self, cls=Warning):
        for i, w in enumerate(self._list):
            if issubclass(w.category, cls):
                return self._list.pop(i)
        return None

    def clear(self):
        self._list.clear()


class _CaptureFDFixture:
    def __init__(self, binary=False):
        self._binary = binary
        self._captured = None

    def start(self):
        self._captured = io.BytesIO() if self._binary else io.StringIO()

    def stop(self):
        pass

    def readouterr(self):
        return (self._captured.getvalue() if self._captured else ""), ""


# Sentinel for MonkeyPatch default params (must be before the class)
_MONKEY_UNSET = object()


class MonkeyPatch:
    _UNSET: Any = object()

    def __init__(self):
        self._saved = []

    @classmethod
    @contextmanager
    def context(cls) -> Generator['MonkeyPatch', None, None]:
        mp = cls()
        try:
            yield mp
        finally:
            mp.undo()

    def setattr(self, target, name=_MONKEY_UNSET, value=_MONKEY_UNSET, raising=True):
        # Support dotted string target like pytest: setattr("module.attr", value)
        if isinstance(target, str):
            parts = target.rsplit(".", 1)
            if len(parts) == 2:
                mod_name, attr_name = parts
                try:
                    target = importlib.import_module(mod_name)
                except ImportError:
                    target = __import__(mod_name)
                # Match pytest semantics:
                #   setattr("mod.attr", val)     → name=val, value=UNSET
                #   setattr("mod.attr", "attr", val) → name="attr", value=val
                if value is _MONKEY_UNSET:
                    return self.setattr(target, attr_name, name, raising=raising)
                return self.setattr(target, attr_name, value, raising=raising)
            # Single-word string: treat as builtins attribute
            #   setattr("name", val)  → target=builtins, attr="name", value=val
            if value is _MONKEY_UNSET:
                return self.setattr(__import__("builtins"), target, name, raising=raising)
            return self.setattr(__import__("builtins"), target, value, raising=raising)
        if name is _MONKEY_UNSET:
            raise TypeError("setattr requires a name")
        try:
            # For class attributes, use __dict__ to avoid descriptor invocation
            if inspect.isclass(target) and name in target.__dict__:
                old = target.__dict__[name]
            else:
                old = getattr(target, name, MonkeyPatch._UNSET)  # type: ignore
        except AttributeError:
            if raising:
                raise
            return
        if value is not MonkeyPatch._UNSET:
            try:
                setattr(target, name, value)  # type: ignore
            except (AttributeError, TypeError):
                if raising:
                    raise
                return
        self._saved.append(("setattr", target, name, old))

    def delattr(self, target, name=_MONKEY_UNSET, raising=True):
        # Support dotted string target like pytest: delattr("module.attr")
        # When name is not given, target acts as a dotted string
        if name is _MONKEY_UNSET:
            if isinstance(target, str):
                parts = target.rsplit(".", 1)
                if len(parts) == 2:
                    mod_name, attr_name = parts
                    try:
                        target = importlib.import_module(mod_name)
                    except ImportError:
                        target = __import__(mod_name)
                    return self.delattr(target, attr_name, raising=raising)
                name = target
                target = __import__("builtins")
            else:
                raise TypeError("delattr requires a name when target is not a string")
        try:
            old = getattr(target, name, MonkeyPatch._UNSET)  # type: ignore
        except AttributeError:
            if raising:
                raise
            return
        try:
            delattr(target, name)  # type: ignore
        except (AttributeError, TypeError):
            if raising:
                raise
            return
        self._saved.append(("setattr", target, name, old))

    def setitem(self, mapping, key, value):
        old = mapping.get(key, MonkeyPatch._UNSET)
        self._saved.append(("setitem", mapping, key, old))
        mapping[key] = value

    def delitem(self, mapping, key, raising=True):
        old = mapping.get(key, MonkeyPatch._UNSET)
        self._saved.append(("setitem", mapping, key, old))
        try:
            del mapping[key]
        except (KeyError, TypeError):
            if raising:
                raise

    def setenv(self, name, value, prepend=None):
        old = os.environ.get(name, MonkeyPatch._UNSET)
        self._saved.append(("env", name, old))
        os.environ[name] = value

    def delenv(self, name, raising=True):
        old = os.environ.get(name, MonkeyPatch._UNSET)
        self._saved.append(("env", name, old))
        try:
            del os.environ[name]
        except KeyError:
            if raising:
                raise

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
                if old is MonkeyPatch._UNSET:
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
                if old is MonkeyPatch._UNSET:
                    if hasattr(target, name):
                        delattr(target, name)
                else:
                    setattr(target, name, old)
            elif item[0] == "setitem":
                _, mapping, key, old = item
                if old is MonkeyPatch._UNSET:
                    mapping.pop(key, None)
                else:
                    mapping[key] = old
        self._saved.clear()


def _unwrap_param(p):
    """Unwrap a pytest.param ParameterSet to get the actual value."""
    if type(p).__name__ == 'ParameterSet':
        if p.values:
            return p.values[0] if len(p.values) == 1 else list(p.values)
        if hasattr(p, 'id') and p.id is not None:
            return p.id
        return None
    return p


_fm_local = threading.local()


def get_fixture_manager() -> FixtureManager:
    try:
        return _fm_local.instance
    except AttributeError:
        fm = FixtureManager()
        _fm_local.instance = fm
        return fm


def register_fixture(func):
    get_fixture_manager().register(func)


fixture_registry = get_fixture_manager()


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
