import os
import importlib


def load_config(path=None):
    if path is None:
        path = _find_pyproject_toml()
    if path is None or not os.path.isfile(path):
        return {}
    tomllib = None
    for mod_name in ("tomllib", "tomli"):
        try:
            tomllib = importlib.import_module(mod_name)
            break
        except ImportError:
            continue
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}
    tool_oxytest = data.get("tool", {}).get("oxytest", {})
    return tool_oxytest


def _find_pyproject_toml():
    cwd = os.getcwd()
    path = os.path.join(cwd, "pyproject.toml")
    if os.path.isfile(path):
        return path
    parent = os.path.dirname(cwd)
    if parent and parent != cwd:
        path = os.path.join(cwd, "pyproject.toml")
        if os.path.isfile(path):
            return path
    return None


def merge_config_with_opts(config_data, opts):
    merged = dict(opts)
    if not config_data:
        return merged
    addopts = config_data.get("addopts", "")
    if addopts:
        extra_args = addopts.split()
        merged = _parse_and_merge(extra_args, merged)
    if "testpaths" in config_data and (not merged.get("paths") or merged.get("paths") == ["."]):
        merged["paths"] = config_data["testpaths"]
    if "ignore" in config_data:
        existing = merged.get("ignore", [])
        merged["ignore"] = existing + list(config_data["ignore"])
    if "markers" in config_data:
        markers = merged.get("_extra_markers", [])
        markers.extend(config_data["markers"])
        merged["_extra_markers"] = markers
    return merged


def _parse_and_merge(args, opts):
    result = dict(opts)
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-v", "--verbose"):
            result["verbose"] = True
        elif arg in ("-q", "--quiet"):
            result["quiet"] = True
        elif arg in ("-x", "--exitfirst"):
            result["exitfirst"] = True
        elif arg == "-k" and i + 1 < len(args):
            i += 1
            result["keyword"] = args[i]
        elif arg.startswith("--tb="):
            result["tb_style"] = arg[5:]
        elif arg == "--tb" and i + 1 < len(args):
            i += 1
            result["tb_style"] = args[i]
        elif arg == "-n" and i + 1 < len(args):
            i += 1
            if args[i] == "auto":
                import os
                result["num_workers"] = os.cpu_count() or 1
            else:
                result["num_workers"] = int(args[i])
        elif arg == "--durations" and i + 1 < len(args):
            i += 1
            result["durations"] = int(args[i])
        elif arg.startswith("-r") and len(arg) > 2:
            result["report_summary"] = arg[2:]
        elif arg == "--cov":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 1
                result["cov_source"] = args[i]
            else:
                result["cov_source"] = True
        elif arg.startswith("--cov="):
            result["cov_source"] = arg[6:]
        elif arg == "--cov-report" and i + 1 < len(args):
            i += 1
            result["cov_report"] = args[i]
        elif arg == "--cov-config" and i + 1 < len(args):
            i += 1
            result["cov_config"] = args[i]
        elif arg == "--cov-branch":
            result["cov_branch"] = True
        elif arg == "--cov-fail-under" and i + 1 < len(args):
            i += 1
            result["cov_fail_under"] = float(args[i])
        elif arg == "--cov-append":
            result["cov_append"] = True
        i += 1
    return result
