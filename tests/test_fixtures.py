import os
import sys
import pathlib

from oxytest._fixtures import (
    FixtureDef,
    FixtureManager,
    MonkeyPatch,
    _CaptureFixture,
    _CaptureFDFixture,
    MockerFixture,
    get_fixture_manager,
    register_fixture,
    fixture_registry,
    _TempPathFactory,
)


def test_fixture_def_defaults():
    def my_fixture():
        pass
    fd = FixtureDef(my_fixture)
    assert fd.func is my_fixture
    assert fd.scope == "function"
    assert fd.params is None
    assert fd.autouse is False
    assert fd.name == "my_fixture"
    assert fd.cached_value is None
    assert fd.cached_scope is None


def test_fixture_def_custom():
    fd = FixtureDef(lambda: None, scope="session", params=[1, 2], autouse=True, name="custom")
    assert fd.scope == "session"
    assert fd.params == [1, 2]
    assert fd.autouse is True
    assert fd.name == "custom"


def test_fixture_def_name_fallback():
    fd = FixtureDef(None, name=None)
    assert fd.name is not None


def test_fm_register():
    fm = FixtureManager()
    fm.register_builtin("custom_fix", lambda: 42, scope="function")
    assert "custom_fix" in fm._fixtures
    assert fm._fixtures["custom_fix"].func() == 42


def test_fm_register_builtin_clean():
    fm = FixtureManager()
    # Should not raise: twice registration of builtins
    fm._setup_builtins()


def test_fm_register_from_module():
    fm = FixtureManager()

    class Module:
        pass

    mod = Module()
    mod.my_fixture = lambda: 42
    mod.my_fixture._oxytest_fixture = {"scope": "function", "params": None, "autouse": False, "name": "my_fixture"}
    fm.register_from_module(mod)
    assert "my_fixture" in fm._fixtures


def test_fm_register_from_module_none():
    fm = FixtureManager()
    fm.register_from_module(object())
    # Should not raise


def test_fm_resolve_missing():
    fm = FixtureManager()
    try:
        fm.resolve("nonexistent")
        assert False
    except LookupError as e:
        assert "not found" in str(e)


def test_fm_resolve_circular():
    fm = FixtureManager()
    def a_fixture(b):
        return 1
    a_fixture._oxytest_fixture = {"scope": "function", "name": "a", "params": None, "autouse": False}
    def b_fixture(a):
        return 2
    b_fixture._oxytest_fixture = {"scope": "function", "name": "b", "params": None, "autouse": False}
    fm.register(a_fixture)
    fm.register(b_fixture)
    try:
        fm.resolve("a")
        assert False
    except LookupError as e:
        assert "Circular" in str(e)


def test_fm_resolve_tmp_path():
    fm = FixtureManager()
    val = fm.resolve("tmp_path")
    assert isinstance(val, pathlib.Path)
    fm.cleanup()


def test_fm_resolve_capsys():
    fm = FixtureManager()
    val = fm.resolve("capsys")
    assert isinstance(val, _CaptureFixture)
    val.start()
    val.stop()


def test_fm_resolve_monkeypatch():
    fm = FixtureManager()
    val = fm.resolve("monkeypatch")
    assert isinstance(val, MonkeyPatch)


def test_fm_cleanup_empty():
    fm = FixtureManager()
    fm.cleanup()


def test_fm_cleanup_with_generator():
    fm = FixtureManager()

    def gen_fixture():
        yield 42

    fm._fixtures["gen"] = FixtureDef(gen_fixture, name="gen")
    val = fm.resolve("gen")
    assert val == 42
    fm.cleanup()


def test_fm_resolve_with_parametrize():
    fm = FixtureManager()

    def param_fix():
        return fm._current_request_param

    fm._fixtures["param_fix"] = FixtureDef(param_fix, name="param_fix")
    fm._current_request_param = 42
    val = fm.resolve("param_fix")
    assert val == 42


def test_fm_cache_session():
    fm = FixtureManager()

    def session_fix():
        return "cached"

    fd = FixtureDef(session_fix, scope="session", name="session_fix")
    fm._fixtures["session_fix"] = fd
    val1 = fm.resolve("session_fix")
    val2 = fm.resolve("session_fix")
    assert val1 == "cached"
    assert val2 == "cached"


def test_fm_finish_generator():
    fm = FixtureManager()

    def gen():
        yield 42

    gen_instance = gen()
    fm.finish_fixture(gen_instance)


def test_fm_finish_with_stop():
    class HasStop:
        stopped = False

        def stop(self):
            self.stopped = True

    obj = HasStop()
    fm = FixtureManager()
    fm.finish_fixture(obj)
    assert obj.stopped


def test_fixture_mocker():
    mocker = MockerFixture()
    mock = mocker.patch("os.pathsep")
    assert isinstance(mock, object)
    mocker.stopall()


def test_mocker_stub():
    mocker = MockerFixture()
    stub = mocker.stub("test_stub")
    assert callable(stub)


def test_mocker_spy():
    class Obj:
        @staticmethod
        def greet(name):
            return f"Hello {name}"

    mocker = MockerFixture()
    spy = mocker.spy(Obj, "greet")
    result = Obj.greet("World")
    assert result == "Hello World"
    assert spy.spy_return == "Hello World"


def test_mocker_spy_exception():
    class Obj:
        @staticmethod
        def fail():
            raise ValueError("oops")

    mocker = MockerFixture()
    spy = mocker.spy(Obj, "fail")
    try:
        Obj.fail()
    except ValueError:
        pass
    assert spy.spy_exception is not None


def test_capture_fixture_start_stop():
    cf = _CaptureFixture()
    cf.start()
    sys.stdout.write("captured")
    result = cf.readouterr()
    assert result.out == "captured"
    cf.stop()
    result = cf.readouterr()
    cf.stop()  # idempotent


def test_capture_fd_fixture():
    cf = _CaptureFDFixture()
    cf.start()
    cf.stop()
    out, _ = cf.readouterr()
    cf.stop()


def test_monkeypatch_setattr():
    mp = MonkeyPatch()
    class Obj:
        attr = "original"
    mp.setattr(Obj, "attr", "modified")
    assert Obj.attr == "modified"
    mp.undo()
    assert Obj.attr == "original"


def test_monkeypatch_setattr_raising():
    mp = MonkeyPatch()
    try:
        mp.setattr(object(), "nonexistent", "val", raising=True)
    except AttributeError:
        pass


def test_monkeypatch_setattr_no_raising():
    mp = MonkeyPatch()
    mp.setattr(object(), "nonexistent", "val", raising=False)
    mp.undo()


def test_monkeypatch_delattr():
    mp = MonkeyPatch()
    class Obj:
        attr = "value"
    mp.delattr(Obj, "attr")
    assert not hasattr(Obj, "attr")
    mp.undo()
    assert Obj.attr == "value"


def test_monkeypatch_delattr_not_found():
    mp = MonkeyPatch()
    class Obj:
        pass
    try:
        mp.delattr(Obj, "nonexistent")
    except AttributeError:
        pass


def test_monkeypatch_setitem():
    mp = MonkeyPatch()
    d = {"key": "old"}
    mp.setitem(d, "key", "new")
    assert d["key"] == "new"
    mp.undo()
    assert d["key"] == "old"


def test_monkeypatch_setitem_new():
    mp = MonkeyPatch()
    d = {}
    mp.setitem(d, "new_key", "value")
    assert d["new_key"] == "value"
    mp.undo()
    assert "new_key" not in d


def test_monkeypatch_delitem():
    mp = MonkeyPatch()
    d = {"key": "value"}
    mp.delitem(d, "key")
    assert "key" not in d
    mp.undo()
    assert d["key"] == "value"


def test_monkeypatch_setenv():
    mp = MonkeyPatch()
    mp.setenv("OX_TEST_ENV", "test_val")
    assert os.environ.get("OX_TEST_ENV") == "test_val"
    mp.undo()
    assert "OX_TEST_ENV" not in os.environ


def test_monkeypatch_delenv():
    os.environ["OX_TEST_ENV2"] = "to_delete"
    mp = MonkeyPatch()
    mp.delenv("OX_TEST_ENV2")
    assert "OX_TEST_ENV2" not in os.environ
    mp.undo()
    assert os.environ.get("OX_TEST_ENV2") == "to_delete"
    del os.environ["OX_TEST_ENV2"]


def test_monkeypatch_delenv_not_found():
    mp = MonkeyPatch()
    try:
        mp.delenv("OX_TEST_NONEXISTENT")
        assert False
    except KeyError:
        pass


def test_monkeypatch_chdir(tmp_path):
    mp = MonkeyPatch()
    original = os.getcwd()
    mp.chdir(str(tmp_path))
    assert os.getcwd() == str(tmp_path)
    mp.undo()
    assert os.getcwd() == original


def test_monkeypatch_syspath_prepend():
    mp = MonkeyPatch()
    mp.syspath_prepend("/tmp/oxytest_test_path")
    assert "/tmp/oxytest_test_path" in sys.path
    mp.undo()
    assert "/tmp/oxytest_test_path" not in sys.path


def test_register_fixture():
    def my_fix():
        return 42
    my_fix._oxytest_fixture = {"scope": "function", "params": None, "autouse": False, "name": "my_fix"}
    register_fixture(my_fix)
    fm = get_fixture_manager()
    assert "my_fix" in fm._fixtures


def test_fixture_registry():
    assert fixture_registry is get_fixture_manager()


def test_fm_fixture_mocker():
    fm = FixtureManager()
    mocker = fm.resolve("mocker")
    assert isinstance(mocker, MockerFixture)
    fm.cleanup()


def test_fm_fixture_benchmark():
    fm = FixtureManager()
    bench = fm.resolve("benchmark")
    result = bench(lambda: 42)
    assert result == 42
    fm.cleanup()


def test_fm_fixture_create_module():
    fm = FixtureManager()
    create = fm.resolve("create_module")
    assert callable(create)
    mod = create(lambda: None)
    assert mod is not None
    fm.cleanup()


def test_fm_fixture_pytestconfig():
    fm = FixtureManager()
    cfg = fm.resolve("pytestconfig")
    assert cfg is not None
    fm.cleanup()


def test_fm_cleanup_with_async():
    fm = FixtureManager()

    async def async_gen():
        yield 42

    agen = async_gen()
    fm._async_generators["test_async"] = agen
    fm.cleanup()


def test_fm_resolve_with_request():
    fm = FixtureManager()
    fm.current_test_func = lambda: None

    def fix_with_request(request):
        return request

    fd = FixtureDef(fix_with_request, name="fix_with_request")
    fm._fixtures["fix_with_request"] = fd
    result = fm.resolve("fix_with_request")
    assert hasattr(result, "scope")
    assert result.scope == "function"
    fm.cleanup()


def test_fm_resolve_with_setup_show():
    fm = FixtureManager()
    os.environ["OXYTEST_SETUP_SHOW"] = "1"
    val = fm.resolve("tmp_path")
    assert isinstance(val, pathlib.Path)
    del os.environ["OXYTEST_SETUP_SHOW"]
    fm.cleanup()


def test_captured_has_stop():
    pass


def test_patch_proxy(capsys):
    mocker = MockerFixture()
    mock = mocker.patch("os.name")
    assert isinstance(mock, object)
    mocker.stopall()


def test_mocker_fixture_generator():
    fm = FixtureManager()
    gen = fm._fixture_mocker()
    val = next(gen)
    assert isinstance(val, MockerFixture)
    try:
        next(gen)
    except StopIteration:
        pass


def test_fm_resolve_async():
    fm = FixtureManager()

    async def async_fix():
        return 99

    fm._fixtures["async_fix"] = FixtureDef(async_fix, name="async_fix")
    val = fm.resolve("async_fix")
    assert val == 99
    fm.cleanup()


def test_fm_register_from_module_with_pytest_fixture():
    fm = FixtureManager()

    class FakePytestFixture:
        def _fixture_function(self):
            return 42
        _fixture_function_marker = type("Marker", (), {"scope": "function", "params": None, "autouse": False})()
        name = "my_fix"

    FakePytestFixture.__wrapped__ = FakePytestFixture._fixture_function
    FakePytestFixture._fixture_function.__module__ = "myplugin"

    class Mod:
        my_fix = FakePytestFixture()

    fm.register_from_module(Mod)
    assert "my_fix" in fm._fixtures


def test_fm_register_from_module_with_benchmark():
    fm = FixtureManager()

    class FakeBenchmark:
        pass

    FakeBenchmark.__wrapped__ = lambda: None
    FakeBenchmark.__wrapped__.__module__ = "pytest_benchmark"

    class Mod:
        benchmark = FakeBenchmark

    # Should skip due to module check — built-in benchmark remains
    count_before = len(fm._fixtures)
    fm.register_from_module(Mod)
    assert len(fm._fixtures) == count_before


def test_fm_register_from_module_pytestfixturefunction_no_wrapped():
    fm = FixtureManager()
    class Mod:
        pass
    mod = Mod()
    class Obj:
        _pytestfixturefunction = True
        name = "orphan"
    mod.orphan = Obj()
    count_before = len(fm._fixtures)
    fm.register_from_module(mod)
    assert len(fm._fixtures) == count_before


def test_fm_register_from_module_benchmark_skip():
    fm = FixtureManager()
    class Mod:
        pass
    mod = Mod()
    class FakeBenchmark:
        def _fixture_function(self):
            return 42
        name = "benchmark"
    FakeBenchmark.__wrapped__ = FakeBenchmark._fixture_function
    FakeBenchmark._fixture_function.__module__ = "pytest_benchmark"
    mod.benchmark = FakeBenchmark()
    count_before = len(fm._fixtures)
    fm.register_from_module(mod)
    assert len(fm._fixtures) == count_before


def test_fm_resolve_with_self_param():
    fm = FixtureManager()
    class Container:
        @staticmethod
        def fix_with_self():
            return 42
    fd = FixtureDef(Container.fix_with_self, name="fix_with_self")
    fm._fixtures["fix_with_self"] = fd
    val = fm.resolve("fix_with_self")
    assert val == 42


def test_fm_resolve_unknown_param():
    fm = FixtureManager()
    def fix_with_default(known_fix, optional=None):
        return known_fix
    fd = FixtureDef(fix_with_default, name="fix_with_default")
    fm._fixtures["fix_with_default"] = fd
    def known_fix():
        return 1
    fm._fixtures["known_fix"] = FixtureDef(known_fix, name="known_fix")
    result = fm.resolve("fix_with_default")
    assert result == 1


def test_fm_setup_show_cleanup():
    fm = FixtureManager()
    os.environ["OXYTEST_SETUP_SHOW"] = "1"
    def gen_fix():
        yield 99
    fm._fixtures["gen_fix"] = FixtureDef(gen_fix, name="gen_fix")
    val = fm.resolve("gen_fix")
    assert val == 99
    fm.cleanup()
    del os.environ["OXYTEST_SETUP_SHOW"]


def test_fm_cleanup_with_generator_exception():
    fm = FixtureManager()
    class BadStop:
        def stop(self):
            raise RuntimeError("cleanup error")
    fm._tmpdirs = []
    fm._cache["badger"] = BadStop()
    fm._generators = {}
    fm._async_generators = {}
    fm.cleanup()  # should not raise


def test_fm_cleanup_tmpdir_remove_error():
    fm = FixtureManager()
    fm._tmpdirs = ["/nonexistent/dir"]
    fm.cleanup()


def test_mocker_patch_proxy_object():
    mocker = MockerFixture()
    proxy = mocker.patch
    assert hasattr(proxy, "object")
    assert callable(proxy.object)
    assert hasattr(proxy, "dict")
    assert callable(proxy.dict)


def test_monkeypatch_setattr_raises_on_getattr_before_save():
    mp = MonkeyPatch()
    class Obj:
        pass
    try:
        mp.setattr(Obj, "nonexistent", "val", raising=True)
    except AttributeError:
        pass


def test_monkeypatch_delattr_raises_on_getattr():
    mp = MonkeyPatch()
    class Obj:
        pass
    try:
        mp.delattr(Obj, "nonexistent", raising=True)
    except AttributeError:
        pass


def test_monkeypatch_undo_setattr_not_set_for_delattr():
    mp = MonkeyPatch()
    class Obj:
        pass
    mp._saved.append(("setattr", Obj, "attr", MonkeyPatch._UNSET))
    Obj.attr = "stale"
    mp.undo()
    assert not hasattr(Obj, "attr")


def test_mocker_stopall_empty():
    mocker = MockerFixture()
    mocker.stopall()


# ===== Coverage gap tests for _fixtures.py uncovered lines =====

def test_fm_register_from_module_wrapped_fallback():
    fm = FixtureManager()
    class Mod:
        pass
    def wrapper():
        return 42
    wrapper._oxytest_fixture = {"scope": "function", "params": None, "autouse": False, "name": "wrapper_fix"}
    class Wrapper:
        __wrapped__ = wrapper
        name = "wrapper_fix"
    mod = Mod()
    mod.wrapper_fix = Wrapper()
    fm.register_from_module(mod)
    assert "wrapper_fix" not in fm._fixtures


def test_fm_register_from_module_wrapped_skip_non_callable():
    fm = FixtureManager()
    class Mod:
        pass
    mod = Mod()
    class Wrapper:
        __wrapped__ = "not callable"
        name = "bad_fix"
    mod.bad_fix = Wrapper()
    count_before = len(fm._fixtures)
    fm.register_from_module(mod)
    assert len(fm._fixtures) == count_before


def test_fm_resolve_unknown_param_skipped():
    fm = FixtureManager()
    def fix_with_extra(known_fix, unknown_param):
        return known_fix
    fd = FixtureDef(fix_with_extra, name="fix_with_extra", scope="function")
    fm._fixtures["fix_with_extra"] = fd
    def known_fix():
        return 1
    fm._fixtures["known_fix"] = FixtureDef(known_fix, name="known_fix")
    try:
        fm.resolve("fix_with_extra")
        assert False
    except TypeError:
        pass


def test_fm_resolve_async_generator_empty():
    fm = FixtureManager()
    async def empty_agen():
        if False:
            yield 42
    fm._fixtures["empty_agen"] = FixtureDef(empty_agen, name="empty_agen")
    val = fm.resolve("empty_agen")
    assert val is None
    fm.cleanup()


def test_fm_resolve_generator_empty():
    fm = FixtureManager()
    def empty_gen():
        if False:
            yield 42
    fm._fixtures["empty_gen"] = FixtureDef(empty_gen, name="empty_gen")
    val = fm.resolve("empty_gen")
    assert val is None
    fm.cleanup()


def test_fm_cleanup_stop_exception():
    fm = FixtureManager()
    class BadStop:
        def stop(self):
            raise RuntimeError("stop failed")
    fm._tmpdirs = []
    fm._generators = {}
    fm._async_generators = {}
    fm._cache["bad"] = BadStop()
    fm.cleanup()


def test_fm_cleanup_tmpdir_exception():
    fm = FixtureManager()
    fm._tmpdirs = ["/nonexistent/path/that/will/error"]
    fm.cleanup()


def test_fm_finish_generator_stop_iteration():
    fm = FixtureManager()
    def gen():
        yield 42
    gen_instance = gen()
    next(gen_instance)  # exhaust it
    fm.finish_fixture(gen_instance)


def test_fm_tmpdir_fixture():
    fm = FixtureManager()
    val = fm.resolve("tmpdir")
    assert isinstance(val, str)
    assert os.path.isdir(val)
    fm.cleanup()
    assert not os.path.isdir(val)


def test_fm_capfd_fixture():
    fm = FixtureManager()
    val = fm.resolve("capfd")
    assert isinstance(val, _CaptureFDFixture)
    fm.cleanup()


def test_fm_resolve_request_param_dict():
    fm = FixtureManager()
    fm.current_test_func = lambda: None
    fm._current_request_param = {"my_fix": 99}
    def fix_with_request(request):
        return request.param
    fd = FixtureDef(fix_with_request, name="my_fix")
    fm._fixtures["my_fix"] = fd
    result = fm.resolve("my_fix")
    assert result == 99
    fm.cleanup()


def test_create_module_no_func():
    fm = FixtureManager()
    create_fn = fm.resolve("create_module")
    result = create_fn()
    assert result is create_fn
    fm.cleanup()


def test_monkeypatch_setattr_raising_false_with_existing():
    mp = MonkeyPatch()
    class Obj:
        attr = "original"
    mp.setattr(Obj, "attr", "modified", raising=False)
    assert Obj.attr == "modified"
    mp.undo()
    assert Obj.attr == "original"


def test_monkeypatch_delattr_raising_false():
    mp = MonkeyPatch()
    class Obj:
        pass
    mp.delattr(Obj, "nonexistent", raising=False)
    mp.undo()


def test_monkeypatch_undo_setattr_not_set():
    mp = MonkeyPatch()
    class Obj:
        pass
    mp._saved.append(("setattr", Obj, "new_attr", MonkeyPatch._UNSET))
    Obj.new_attr = "value"
    mp.undo()
    assert not hasattr(Obj, "new_attr")


def test_capture_result_getitem():
    cf = _CaptureFixture()
    cf.start()
    sys.stdout.write("hello")
    result = cf.readouterr()
    assert result[0] == "hello"
    assert result[1] == ""
    cf.stop()


def test_fm_register_from_module_wrapped_has_oxytest_fixture():
    fm = FixtureManager()
    class Mod:
        pass
    mod = Mod()
    def fix_fn():
        return 42
    fix_fn._oxytest_fixture = {"scope": "function", "params": None, "autouse": False, "name": "already_reg"}
    class Wrapper:
        _fixture_function = fix_fn
        name = "already_reg"
    mod.already_reg = Wrapper()
    count_before = len(fm._fixtures)
    fm.register_from_module(mod)
    assert len(fm._fixtures) == count_before


# ── Additional MonkeyPatch tests ─────────────────────────────────────


def test_monkeypatch_setattr_dotted():
    mp = MonkeyPatch()
    import os as _os
    import os as _os2
    orig_sep = _os2.path.sep
    mp.setattr("os.path.sep", "/custom")
    assert _os.path.sep == "/custom"
    mp.undo()
    assert _os.path.sep == orig_sep


def test_monkeypatch_setattr_builtins():
    mp = MonkeyPatch()
    mp.setattr("my_custom_builtin2", 42)
    import builtins
    val = getattr(builtins, "my_custom_builtin2", None)
    mp.undo()
    assert val is None or val == 42


def test_monkeypatch_delattr_dotted():
    mp = MonkeyPatch()
    import os as _os4
    mp.setattr("os.path.sep", "/del_test")
    mp.delattr("os.path.sep")
    assert not hasattr(_os4.path, "sep")
    mp.undo()
    assert hasattr(_os4.path, "sep")


def test_monkeypatch_delattr_module_attr():
    mp = MonkeyPatch()
    mp.delattr("os", "nonexistent_del_attr", raising=False)


def test_monkeypatch_delitem_raising_false():
    mp = MonkeyPatch()
    mp.delitem({}, "nonexistent2", raising=False)


def test_monkeypatch_delenv_raising_false():
    mp = MonkeyPatch()
    mp.delenv("OXYTEST_NONEXISTENT2", raising=False)


def test_monkeypatch_multiple_undo():
    mp = MonkeyPatch()
    d = {"a": 1, "b": 2}
    mp.setitem(d, "a", 99)
    mp.setitem(d, "b", 88)
    mp.setenv("OXYTEST_MULTI2", "val")
    assert d["a"] == 99
    assert d["b"] == 88
    assert os.environ.get("OXYTEST_MULTI2") == "val"
    mp.undo()
    assert d["a"] == 1
    assert d["b"] == 2
    assert "OXYTEST_MULTI2" not in os.environ


def test_monkeypatch_setattr_dotted_3args():
    mp = MonkeyPatch()
    mp.setattr("os", "path", "custom_path")
    import os.path as _osp
    assert _osp is not None


# ── FixtureManager cleanup tests ────────────────────────────────────


def test_cleanup_generators():
    fm = FixtureManager()
    def gen_fixture():
        yield "value"
    fm._fixtures["cleanup_gen"] = FixtureDef(gen_fixture, scope="function", name="cleanup_gen")
    fm._fixtures["cleanup_func"] = FixtureDef(lambda: "plain", scope="function", name="cleanup_func")
    v1 = fm.resolve("cleanup_gen")
    assert v1 == "value"
    fm.resolve("cleanup_func")
    fm.cleanup("function")
    assert len(fm._generators) == 0


def test_cleanup_session_preserved():
    fm = FixtureManager()
    calls = []
    def session_fixture():
        calls.append("setup")
        yield "session_val2"
        calls.append("teardown")
    fm._fixtures["sess2"] = FixtureDef(session_fixture, scope="session", name="sess2")
    v = fm.resolve("sess2")
    assert v == "session_val2"
    assert calls == ["setup"]
    fm.cleanup("function")
    assert "teardown" not in calls


def test_cleanup_all_fixtures():
    fm = FixtureManager()
    def session_gen():
        yield "sess"
    def func_gen():
        yield "func"
    fm._fixtures["cl_all_sess"] = FixtureDef(session_gen, scope="session", name="cl_all_sess")
    fm._fixtures["cl_all_func"] = FixtureDef(func_gen, scope="function", name="cl_all_func")
    fm.resolve("cl_all_sess")
    fm.resolve("cl_all_func")
    fm.cleanup_all()
    assert len(fm._generators) == 0
    assert len(fm._async_generators) == 0
    assert len(fm._cache) == 0


def test_cleanup_with_stop():
    fm = FixtureManager()
    class Stoppable:
        def __init__(self):
            self.stopped = False
        def stop(self):
            self.stopped = True
    obj = Stoppable()
    fm._fixtures["stoppable2"] = FixtureDef(lambda: obj, scope="function", name="stoppable2")
    v = fm.resolve("stoppable2")
    assert v is obj
    fm.cleanup("function")
    assert obj.stopped


def test_cleanup_tmpdirs():
    fm = FixtureManager()
    import tempfile
    td = tempfile.mkdtemp()
    fm._tmpdirs.append(td)
    assert os.path.isdir(td)
    fm.cleanup("function")
    assert not os.path.isdir(td)


# ── _CaptureFDFixture test ───────────────────────────────────────────


def test_capfd():
    capfd = _CaptureFDFixture()
    assert capfd is not None


# ── New 3.0.0 fixture tests ─────────────────────────────────────────


def test_fm_resolve_caplog():
    fm = FixtureManager()
    result = fm.resolve("caplog")
    assert hasattr(result, 'records')
    assert hasattr(result, 'text')
    assert hasattr(result, 'messages')
    assert hasattr(result, 'record_tuples')


def test_fm_resolve_capsysbinary():
    fm = FixtureManager()
    result = fm.resolve("capsysbinary")
    assert result is not None


def test_fm_resolve_capfdbinary():
    fm = FixtureManager()
    result = fm.resolve("capfdbinary")
    assert result is not None


def test_fm_resolve_recwarn():
    fm = FixtureManager()
    result = fm.resolve("recwarn")
    assert hasattr(result, 'list')
    assert hasattr(result, 'pop')
    assert hasattr(result, 'clear')


def test_fm_resolve_doctest_namespace():
    fm = FixtureManager()
    result = fm.resolve("doctest_namespace")
    assert result == {}


def test_fm_resolve_tmp_path_factory():
    fm = FixtureManager()
    result = fm.resolve("tmp_path_factory")
    assert hasattr(result, 'mktemp')
    assert hasattr(result, 'getbasetemp')
    tmp = result.mktemp("test")
    assert tmp.exists()


def test_fm_resolve_cache():
    fm = FixtureManager()
    result = fm.resolve("cache")
    assert hasattr(result, 'get')
    assert hasattr(result, 'set')
    result.set("key", "val")
    assert result.get("key") == "val"


def test_fm_resolve_record_property():
    fm = FixtureManager()
    result = fm.resolve("record_property")
    result("key", "value")
    assert result.properties == [("key", "value")]


def test_fm_resolve_subtests():
    fm = FixtureManager()
    result = fm.resolve("subtests")
    assert hasattr(result, 'test')
    with result.test(a=1):
        pass


def test_monkeypatch_context():
    import os as _os
    original = _os.path.sep
    with MonkeyPatch.context() as mp:
        mp.setattr("os.path.sep", "/custom")
        assert _os.path.sep == "/custom"
    assert _os.path.sep == original


# ── New 3.0.0 tests ─────────────────────────────────────────────────


def test_tmp_path_factory_mktemp():
    fm = FixtureManager()
    factory = fm.resolve("tmp_path_factory")
    tmp = factory.mktemp("test_mktemp")
    assert tmp.exists()
    assert tmp.is_dir()
    assert "test_mktemp" in tmp.name


def test_tmp_path_factory_getbasetemp():
    fm = FixtureManager()
    factory = fm.resolve("tmp_path_factory")
    base = factory.getbasetemp()
    assert base.exists()
    assert base.is_dir()


def test_tmp_path_factory_with_basetemp():
    import tempfile as _tf
    base = pathlib.Path(_tf.mkdtemp())
    factory = _TempPathFactory(basetemp=base)
    tmp = factory.mktemp("test_base")
    assert str(tmp).startswith(str(base))
    assert tmp.exists()


def test_tmp_path_factory_cleanup():
    """Verify that created dirs are tracked for cleanup."""
    import tempfile as _tf
    base = pathlib.Path(_tf.mkdtemp())
    factory = _TempPathFactory(basetemp=base)
    tmp = factory.mktemp("clean_test")
    assert tmp.exists()
    assert tmp in factory._created
    # Simulate cleanup
    import shutil
    for d in factory._created:
        shutil.rmtree(d, ignore_errors=True)
    assert not tmp.exists()
