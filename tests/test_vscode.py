import os

from oxytest._core import TestItem

from oxytest._vscode import (
    _send_jsonrpc,
    _build_test_tree,
    hook_oxytest_discovery,
    hook_oxytest_execution,
    pytest_addoption,
    pytest_configure,
    pytest_sessionfinish,
)


def _make_test(path, name, line_no=1):
    t = TestItem()
    t.path = path
    t.name = name
    t.line_no = line_no
    t.args_json = ""
    return t


def test_build_test_tree_simple():
    tests = [_make_test("test_foo.py", "test_bar")]
    tree = _build_test_tree(tests, path_base="/project", id_base="/project")
    assert tree["type_"] == "folder"
    assert len(tree["children"]) == 1
    file_node = tree["children"][0]
    assert "test_foo.py" in file_node["name"]
    assert file_node["type_"] == "file"
    assert len(file_node["children"]) == 1
    test_node = file_node["children"][0]
    assert test_node["name"] == "test_bar"
    assert test_node["type_"] == "test"
    assert "runID" in test_node


def test_build_test_tree_class_method():
    tests = [_make_test("test_cls.py", "TestClass::test_method")]
    tree = _build_test_tree(tests)
    file_node = tree["children"][0]
    assert file_node["type_"] == "file"
    class_node = file_node["children"][0]
    assert class_node["name"] == "TestClass"
    assert class_node["type_"] == "class"
    test_node = class_node["children"][0]
    assert "test_method" in test_node["name"]
    assert test_node["type_"] == "test"


def test_build_test_tree_parametrized():
    tests = [_make_test("test_param.py", "test_add[3+5-8]")]
    tree = _build_test_tree(tests)
    file_node = tree["children"][0]
    func_node = file_node["children"][0]
    assert func_node["type_"] == "function"
    assert func_node["name"] == "test_add"
    param_node = func_node["children"][0]
    assert "[3+5-8]" in param_node["id_"]


def test_build_test_tree_parametrized_class():
    tests = [_make_test("test_param.py", "TestClass::test_add[1+2-3]")]
    tree = _build_test_tree(tests)
    file_node = tree["children"][0]
    class_node = file_node["children"][0]
    assert class_node["type_"] == "class"
    func_node = class_node["children"][0]
    assert func_node["type_"] == "function"
    assert func_node["name"] == "test_add"
    param_node = func_node["children"][0]
    assert "[1+2-3]" in param_node["name"]


def test_build_test_tree_multiple_files():
    tests = [
        _make_test("a_test.py", "test_a"),
        _make_test("b_test.py", "test_b"),
    ]
    tree = _build_test_tree(tests, path_base="/root", id_base="/root")
    assert len(tree["children"]) == 2
    assert any("a_test.py" in c["name"] for c in tree["children"])
    assert any("b_test.py" in c["name"] for c in tree["children"])


def test_send_jsonrpc_pipe_error():
    _send_jsonrpc("/nonexistent/pipe", {"test": "data"})


def test_hook_oxytest_discovery():
    tests = [_make_test("test_x.py", "test_y")]
    hook_oxytest_discovery(tests, "/nonexistent/pipe", "/cwd")


def test_hook_oxytest_execution_passed():
    class FakeResult:
        passed = True
        error = None
        traceback = None

        class test:
            path = "test_x.py"
            name = "test_y"

    results = [FakeResult()]
    hook_oxytest_execution(results, "/nonexistent/pipe", "/cwd")


def test_hook_oxytest_execution_failed():
    class FakeResult:
        passed = False
        error = "AssertionError: assert 1 == 2"
        traceback = "Traceback ..."

        class test:
            path = "test_x.py"
            name = "test_y"

    results = [FakeResult()]
    hook_oxytest_execution(results, "/nonexistent/pipe", "/cwd", status="failure")


def test_hook_oxytest_execution_skipped():
    class FakeResult:
        passed = False
        error = "SKIPPED: reason"
        traceback = None

        class test:
            path = "test_x.py"
            name = "test_y"

    results = [FakeResult()]
    hook_oxytest_execution(results, "/nonexistent/pipe", "/cwd")


def test_hook_oxytest_execution_xfail():
    class FakeResult:
        passed = False
        error = "XFAIL: known bug"
        traceback = None

        class test:
            path = "test_x.py"
            name = "test_y"

    results = [FakeResult()]
    hook_oxytest_execution(results, "/nonexistent/pipe", "/cwd")


def test_pytest_addoption():
    class FakeParser:
        def __init__(self):
            self.options = {}

        def addoption(self, *args, **kwargs):
            self.options[kwargs.get("dest", args[0])] = kwargs

    parser = FakeParser()
    pytest_addoption(parser)
    assert "vscode_pipe" in parser.options


def test_pytest_configure_no_pipe():
    class FakeConfig:
        def __init__(self):
            self._opts = {}
            self._collected_items = []

        def getoption(self, name, default=None):
            return self._opts.get(name, default)

    config = FakeConfig()
    pytest_configure(config)


def test_pytest_sessionfinish_no_pipe():
    class FakeSession:
        def __init__(self):
            self._opts = {}

    pytest_sessionfinish(FakeSession(), 0)


def test_pytest_sessionfinish_with_pipe_discovery():
    import os
    os.environ["TEST_RUN_PIPE"] = "/nonexistent/pipe"

    class FakeSession:
        _opts = {"vscode_pipe": "/nonexistent/pipe"}
        _collected_items = []

    def cleanup():
        os.environ.pop("TEST_RUN_PIPE", None)

    pytest_sessionfinish(FakeSession(), 0)
    cleanup()


def test_pytest_sessionfinish_with_pipe_execution():
    os.environ["TEST_RUN_PIPE"] = "/nonexistent/pipe"

    class FakeSession:
        _opts = {"vscode_pipe": "/nonexistent/pipe"}
        _test_results = []

    def cleanup():
        os.environ.pop("TEST_RUN_PIPE", None)

    pytest_sessionfinish(FakeSession(), 0)
    cleanup()


# ===== Coverage gap tests for _vscode.py =====

def test_pytest_configure_env_pipe():
    os.environ["TEST_RUN_PIPE"] = "/tmp/test_pipe"
    class FakeConfig:
        def __init__(self):
            self._opts = {}
        def getoption(self, name, default=None):
            return self._opts.get(name, default)
    config = FakeConfig()
    pytest_configure(config)
    os.environ.pop("TEST_RUN_PIPE", None)


def test_pytest_sessionfinish_discovery():
    os.environ["TEST_RUN_PIPE"] = "/nonexistent/discovery"
    import oxytest._vscode as _vscode_mod
    _vscode_mod._IS_DISCOVERY = True
    class FakeSession:
        _opts = {"vscode_pipe": "/nonexistent/discovery"}
        _collected_items = []
    pytest_sessionfinish(FakeSession(), 0)
    _vscode_mod._IS_DISCOVERY = False
    os.environ.pop("TEST_RUN_PIPE", None)
