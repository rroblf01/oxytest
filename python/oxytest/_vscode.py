import os
import sys
import json
import socket


_IS_DISCOVERY = False


def _send_jsonrpc(pipe_path, payload):
    data = json.dumps({"jsonrpc": "2.0", "params": payload})
    header = f"content-length: {len(data)}\r\ncontent-type: application/json\r\n\r\n"
    try:
        if sys.platform == "win32":
            import win32pipe
            handle = win32pipe.CreateFile(
                pipe_path,
                win32pipe.GENERIC_WRITE,
                0,
                None,
                win32pipe.OPEN_EXISTING,
                0,
                None,
            )
            win32pipe.WriteFile(handle, (header + data).encode())
            win32pipe.CloseHandle(handle)
        else:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(pipe_path)
                sock.sendall((header + data).encode())
    except Exception as exc:
        print(f"oxytest: vscode pipe error: {exc}", file=sys.stderr)


def _build_test_tree(tests, path_base="", id_base=""):
    root = {
        "name": os.path.basename(path_base) if path_base else "oxytest",
        "path": path_base or ".",
        "type_": "folder",
        "id_": id_base or os.getcwd(),
        "children": {},
    }
    for test in tests:
        rel_path = os.path.relpath(test.path, path_base) if path_base else test.path
        parts = test.name.split("::")
        mname = parts[0] if len(parts) > 1 else None
        tname = parts[-1]
        param_suffix = ""
        if "[" in tname and tname.endswith("]"):
            base_name, bracket = tname.split("[", 1)
            tname = base_name
            param_suffix = "[" + bracket
        file_node = root["children"].setdefault(rel_path, {
            "name": rel_path,
            "path": rel_path,
            "type_": "file",
            "id_": os.path.join(id_base, rel_path) if id_base else test.path,
            "children": {},
        })
        if mname:
            class_node = file_node["children"].setdefault(mname, {
                "name": mname,
                "path": rel_path,
                "type_": "class",
                "id_": f"{file_node['id_']}::{mname}",
                "children": {},
            })
            if param_suffix:
                func_key = tname
                func_node = class_node["children"].setdefault(func_key, {
                    "name": tname,
                    "path": rel_path,
                    "type_": "function",
                    "id_": f"{class_node['id_']}::{tname}",
                    "children": {},
                })
                test_id = f"{func_node['id_']}{param_suffix}"
                func_node["children"][param_suffix] = {
                    "name": param_suffix,
                    "path": rel_path,
                    "lineno": str(test.line_no),
                    "type_": "test",
                    "id_": test_id,
                    "runID": test_id,
                }
            else:
                test_id = f"{class_node['id_']}::{tname}"
                class_node["children"][tname] = {
                    "name": tname,
                    "path": rel_path,
                    "lineno": str(test.line_no),
                    "type_": "test",
                    "id_": test_id,
                    "runID": test_id,
                }
        else:
            if param_suffix:
                func_key = tname
                func_node = file_node["children"].setdefault(func_key, {
                    "name": tname,
                    "path": rel_path,
                    "type_": "function",
                    "id_": f"{file_node['id_']}::{tname}",
                    "children": {},
                })
                test_id = f"{func_node['id_']}{param_suffix}"
                func_node["children"][param_suffix] = {
                    "name": param_suffix,
                    "path": rel_path,
                    "lineno": str(test.line_no),
                    "type_": "test",
                    "id_": test_id,
                    "runID": test_id,
                }
            else:
                test_id = f"{file_node['id_']}::{tname}"
                file_node["children"][tname] = {
                    "name": tname,
                    "path": rel_path,
                    "lineno": str(test.line_no),
                    "type_": "test",
                    "id_": test_id,
                    "runID": test_id,
                }

    def _to_list(node_dict):
        result = []
        for key, child in sorted(node_dict.items()):
            if "children" in child and child["children"]:
                child["children"] = _to_list(child["children"])
            result.append(child)
        return result

    root["children"] = _to_list(root["children"])
    return root


def hook_oxytest_discovery(tests, pipe_path, cwd):
    tree = _build_test_tree(tests, path_base=cwd, id_base=cwd)
    payload = {
        "cwd": cwd,
        "status": "success",
        "payloadVersion": 2,
        "tests": tree,
        "error": None,
    }
    _send_jsonrpc(pipe_path, payload)


def hook_oxytest_execution(results, pipe_path, cwd, status="success", error=None):
    result_map = {}
    for r in results:
        outcome = "success"
        message = None
        traceback = None
        if not r.passed:
            err = r.error or ""
            if "SKIPPED:" in err:
                outcome = "skipped"
            elif "XFAIL:" in err:
                outcome = "success"
            else:
                outcome = "failure"
                message = err
                traceback = getattr(r, "traceback", None)
        test_id = f"{r.test.path}::{r.test.name}"
        result_map[test_id] = {
            "test": test_id,
            "outcome": outcome,
            "message": message,
            "traceback": traceback,
            "subtest": None,
        }
    payload = {
        "cwd": cwd,
        "status": status,
        "result": result_map,
        "not_found": None,
        "error": error,
    }
    _send_jsonrpc(pipe_path, payload)


def pytest_addoption(parser):
    parser.addoption("--vscode-pipe", action="store", dest="vscode_pipe", default=None)


def pytest_configure(config):
    global _IS_DISCOVERY
    pipe = os.environ.get("TEST_RUN_PIPE")
    if pipe:
        import atexit
        from oxytest._compat import Config as _OxyConfig
        if isinstance(config, _OxyConfig):
            config._opts["vscode_pipe"] = pipe
        atexit.register(_send_jsonrpc, pipe, {
            "cwd": os.getcwd(),
            "status": "error",
            "result": None,
            "not_found": None,
            "error": ["oxytest: vscode session ended"],
        })
    if hasattr(config, "getoption") and config.getoption("collect_only", False):
        _IS_DISCOVERY = True


def pytest_sessionfinish(session, exitstatus):
    pipe = None
    if hasattr(session, "_opts"):
        pipe = session._opts.get("vscode_pipe")
    if not pipe:
        pipe = os.environ.get("TEST_RUN_PIPE")
    if not pipe:
        return
    cwd = os.getcwd()
    if _IS_DISCOVERY:
        items = getattr(session, "_collected_items", [])
        from oxytest._compat import _expand_parametrize
        expanded = _expand_parametrize(items)
        hook_oxytest_discovery(expanded, pipe, cwd)
    else:
        results = getattr(session, "_test_results", [])
        hook_oxytest_execution(results, pipe, cwd,
                                status="success" if exitstatus == 0 else "failure",
                                error=None if exitstatus == 0 else ["Some tests failed"])
