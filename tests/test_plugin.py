
from oxytest._plugin import (
    PluginManager,
    get_plugin_manager,
    hookimpl,
    hookspec,
    HookimplMarker,
    HookspecMarker,
    pytest_addoption,
    pytest_configure,
    pytest_sessionstart,
    pytest_sessionfinish,
    pytest_collection_modifyitems,
    pytest_runtest_call,
)


def test_plugin_manager_singleton():
    pm1 = get_plugin_manager()
    pm2 = get_plugin_manager()
    assert pm1 is pm2


def test_plugin_manager_register():
    pm = PluginManager()

    class MyPlugin:
        pass

    name = pm.register(MyPlugin())
    assert name is not None


def test_plugin_manager_unregister():
    pm = PluginManager()

    class MyPlugin:
        pass

    plugin = MyPlugin()
    pm.register(plugin)
    result = pm.unregister(plugin)
    assert result is not None


def test_plugin_manager_load_conftest_with_hooks():
    pm = PluginManager()

    class ConftestPlugin:
        def pytest_addoption(self, parser):
            pass

    result = pm.load_conftest_plugins(ConftestPlugin(), "/path")
    assert result is True


def test_plugin_manager_load_conftest_without_hooks():
    pm = PluginManager()

    class NoHooks:
        pass

    result = pm.load_conftest_plugins(NoHooks(), "/path")
    assert result is False


def test_plugin_manager_load_conftest_partial_hooks():
    pm = PluginManager()

    class PartialHooks:
        def pytest_sessionstart(self, session):
            pass

    result = pm.load_conftest_plugins(PartialHooks(), "/path")
    assert result is True


def test_plugin_manager_load_entry_point_plugins(monkeypatch):
    pm = PluginManager()

    class FakeEntryPoint:
        name = "fake_plugin"

        def load(self):
            class FakePlugin:
                pass

            return FakePlugin()

    def fake_entry_points(group="pytest11"):
        return [FakeEntryPoint()]

    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    pm.load_entry_point_plugins()


def test_plugin_manager_load_entry_point_plugins_error(monkeypatch):
    pm = PluginManager()

    class FakeEntryPoint:
        name = "bad_plugin"

        def load(self):
            raise ImportError("not found")

    def fake_entry_points(group="pytest11"):
        return [FakeEntryPoint()]

    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    pm.load_entry_point_plugins()


def test_plugin_manager_load_plugin_by_name_existing(monkeypatch):
    pm = PluginManager()
    pm.load_plugin_by_name("sys")
    assert any("sys" in str(p) for p in pm._plugins)


def test_plugin_manager_load_plugin_by_name_missing():
    pm = PluginManager()
    pm.load_plugin_by_name("nonexistent_module_xyz")


def test_plugin_manager_load_vscode_pytest(monkeypatch):
    pm = PluginManager()
    pm.load_plugin_by_name("vscode_pytest")


def test_plugin_manager_hook_property():
    pm = PluginManager()
    hook = pm.hook
    assert hasattr(hook, "pytest_addoption")
    assert hasattr(hook, "pytest_configure")
    assert hasattr(hook, "pytest_sessionstart")
    assert hasattr(hook, "pytest_sessionfinish")


def test_hookimpl_decorator_bare():

    @hookimpl
    def my_hook():
        pass

    assert callable(my_hook)


def test_hookimpl_decorator_with_args():

    @hookimpl(tryfirst=True)
    def my_hook2():
        pass

    assert callable(my_hook2)


def test_hookspec_decorator_bare():

    @hookspec
    def my_spec():
        pass

    assert callable(my_spec)


def test_hookspec_decorator_with_args():

    @hookspec(tryfirst=True)
    def my_spec2():
        pass

    assert callable(my_spec2)


def test_hookimpl_marker():
    assert HookimplMarker is not None


def test_hookspec_marker():
    assert HookspecMarker is not None


def test_hookspec_wrapper():

    @hookspec(hookwrapper=True)
    def my_wrapper():
        pass

    assert callable(my_wrapper)


def test_hookimpl_wrapper():

    @hookimpl(wrapper=True)
    def my_impl_wrapper():
        pass

    assert callable(my_impl_wrapper)


def test_hookimpl_optionalhook():

    @hookimpl(optionalhook=True)
    def my_optional():
        pass

    assert callable(my_optional)


def test_pytest_addoption_spec():
    assert callable(pytest_addoption)


def test_pytest_configure_spec():
    assert callable(pytest_configure)


def test_pytest_sessionstart_spec():
    assert callable(pytest_sessionstart)


def test_pytest_sessionfinish_spec():
    assert callable(pytest_sessionfinish)


def test_pytest_collection_modifyitems_spec():
    assert callable(pytest_collection_modifyitems)


def test_pytest_runtest_call_spec():
    assert callable(pytest_runtest_call)


def test_plugin_manager_entry_points_import_error(monkeypatch):
    pm = PluginManager()
    import importlib.metadata
    def broken_entry_points(**kwargs):
        raise RuntimeError("metadata broken")
    monkeypatch.setattr(importlib.metadata, "entry_points", broken_entry_points)
    pm.load_entry_point_plugins()


def test_plugin_manager_register_none():
    pm = PluginManager()
    result = pm.register(None)
    assert result is None
