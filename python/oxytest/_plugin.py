"""Plugin system for oxytest using pluggy.

Hook specification (implemented by plugins):

- ``pytest_addoption(parser)`` – register custom CLI flags.
- ``pytest_configure(config)`` – called after CLI parsing, before test
  collection.
- ``pytest_sessionstart(session)`` – called before test execution.
- ``pytest_sessionfinish(session, exitstatus)`` – called after all tests
  run.
- ``pytest_collection_modifyitems(session, config, items)`` – called
  after test discovery, before execution.
- ``pytest_runtest_call(item)`` – called for each test item.

Plugin discovery order:
  1. Built-in hooks (none yet).
  2. ``conftest.py`` modules (loaded per-directory).
  3. Entry points registered via ``pytest11``.
  4. Explicit ``-p PLUGIN`` CLI arguments.
"""

import sys
import pluggy
from typing import Any


_hook_spec = pluggy.HookspecMarker("oxytest")
_hook_impl = pluggy.HookimplMarker("oxytest")


# ---------------------------------------------------------------------------
# Hook specifications
# ---------------------------------------------------------------------------

@_hook_spec
def pytest_addoption(parser: Any):
    """Register custom CLI flags. Called before ``pytest_configure``."""


@_hook_spec
def pytest_configure(config: Any):
    """Called after CLI parsing, before test collection / execution."""


@_hook_spec
def pytest_sessionstart(session: Any):
    """Called before test execution begins."""


@_hook_spec
def pytest_sessionfinish(session: Any, exitstatus: int):
    """Called after all tests have finished."""


@_hook_spec
def pytest_collection_modifyitems(session: Any, config: Any, items: list):
    """Called after test discovery, before execution. Can modify items."""


@_hook_spec
def pytest_runtest_call(item: Any):
    """Called for each test item (before the actual test call)."""


# ---------------------------------------------------------------------------
# Plugin manager
# ---------------------------------------------------------------------------

class PluginManager:
    """Manages plugin registration and hook invocation."""

    def __init__(self):
        self._pm = pluggy.PluginManager("oxytest")
        import sys
        self._pm.add_hookspecs(sys.modules[__name__])
        self._plugins: list[str] = []

    @property
    def hook(self):
        return self._pm.hook

    def register(self, plugin: Any, name: str | None = None) -> str | None:
        return self._pm.register(plugin, name=name)

    def unregister(self, plugin: Any) -> Any:
        return self._pm.unregister(plugin)

    def load_conftest_plugins(self, module: Any, path: str):
        """Register a conftest module as a plugin."""
        if hasattr(module, "pytest_addoption") or \
           hasattr(module, "pytest_configure") or \
           hasattr(module, "pytest_sessionstart") or \
           hasattr(module, "pytest_sessionfinish") or \
           hasattr(module, "pytest_collection_modifyitems") or \
           hasattr(module, "pytest_runtest_call"):
            self.register(module, name=f"conftest:{path}")
            return True
        return False

    def load_entry_point_plugins(self):
        """Discover and load plugins registered via ``pytest11`` entry points."""
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="pytest11")
        except Exception:
            return

        for ep in eps:
            try:
                plugin = ep.load()
                self.register(plugin, name=ep.name)
                # Also register any fixtures defined in the plugin module
                from oxytest._fixtures import get_fixture_manager
                get_fixture_manager().register_from_module(plugin)
            except Exception as exc:
                print(f"oxytest: warning – could not load plugin {ep.name}: {exc}", file=sys.stderr)

    def load_plugin_by_name(self, name: str):
        """Load a single plugin by module name (``-p PLUGIN``)."""
        try:
            __import__(name)
            mod = sys.modules[name]
            self.register(mod, name=name)
        except Exception as exc:
            print(f"oxytest: warning – could not load plugin {name!r}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    return _plugin_manager


def hookspec(tryfirst=False, trylast=False, hookwrapper=False):
    """Decorator for plugin hook specifications.

    Can be used as ``@hookspec`` or ``@hookspec(tryfirst=True)``.
    """
    if callable(tryfirst):
        return _hook_spec(tryfirst)
    return _hook_spec(tryfirst=tryfirst, trylast=trylast,  # ty: ignore
                      hookwrapper=hookwrapper)


def hookimpl(tryfirst=False, trylast=False,
             hookwrapper=False, optionalhook=False,
             wrapper=False):
    """Decorator for plugin hook implementations.

    Can be used as ``@hookimpl`` or ``@hookimpl(tryfirst=True)``.
    ``wrapper`` is an alias for ``hookwrapper`` (compatibility with pluggy >=1.7).
    """
    # Allow bare @hookimpl usage (without parentheses)
    if callable(tryfirst):
        return _hook_impl(tryfirst)
    return _hook_impl(tryfirst=tryfirst, trylast=trylast,
                      hookwrapper=hookwrapper or wrapper,
                      optionalhook=optionalhook)


# Re-export the raw markers for advanced use
HookimplMarker = _hook_impl
HookspecMarker = _hook_spec


__all__ = [
    "PluginManager",
    "get_plugin_manager",
    "hookimpl",
    "hookspec",
    "pytest_addoption",
    "pytest_configure",
    "pytest_sessionstart",
    "pytest_sessionfinish",
    "pytest_collection_modifyitems",
    "pytest_runtest_call",
    "HookimplMarker",
    "HookspecMarker",
]
