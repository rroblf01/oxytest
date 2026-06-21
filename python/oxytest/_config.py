import os
import importlib
import configparser


def load_config(path=None):
    only_path = path is not None
    if path is None:
        path = _find_pyproject_toml()
    result = {}
    if path and os.path.isfile(path):
        tomllib = None
        for mod_name in ("tomllib", "tomli"):
            try:
                tomllib = importlib.import_module(mod_name)
                break
            except ImportError:
                continue
        if tomllib is not None:
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
            except Exception:
                import traceback as _tb
                _tb.print_exc()
                data = {}
            tool_oxytest = data.get("tool", {}).get("oxytest", {})
            if tool_oxytest:
                result.update(tool_oxytest)
        # Read [tool.pytest.ini_options] from pyproject.toml (pytest's recommended config location)
        tool_pytest = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
        if tool_pytest:
            if "testpaths" in tool_pytest:
                result.setdefault("testpaths", tool_pytest["testpaths"])
            if "markers" in tool_pytest:
                _extra = result.get("_extra_markers")
                if _extra is None:
                    _extra = []
                    result["_extra_markers"] = _extra
                _extra.extend(tool_pytest["markers"] if isinstance(tool_pytest["markers"], list) else [tool_pytest["markers"]])
            if "filterwarnings" in tool_pytest:
                result.setdefault("filterwarnings", tool_pytest["filterwarnings"] if isinstance(tool_pytest["filterwarnings"], list) else [tool_pytest["filterwarnings"]])
            if "norecursedirs" in tool_pytest:
                _ign = result.get("ignore")
                if _ign is None:
                    _ign = []
                    result["ignore"] = _ign
                _ign.extend(tool_pytest["norecursedirs"])
            if "addopts" in tool_pytest:
                result.setdefault("addopts", tool_pytest["addopts"])
    # Merge pytest.ini / setup.cfg / tox.ini only when auto-detecting config
    if not only_path:
        ini_config = _read_ini_config()
        result = _merge_ini_config(ini_config, result)
    return result


def _read_ini_config():
    """Read pytest config from pytest.ini, setup.cfg, or tox.ini."""
    parser = configparser.ConfigParser()
    candidates = ["pytest.ini", "setup.cfg", "tox.ini"]
    for fname in candidates:
        path = os.path.join(os.getcwd(), fname)
        if os.path.isfile(path):
            parser.read(path)
            for section in ("pytest", "tool:pytest"):
                if parser.has_section(section):
                    return dict(parser[section])
    return {}


def _merge_ini_config(ini_data, result):
    """Merge INI config values into the result dict."""
    if "addopts" in ini_data:
        result.setdefault("addopts", ini_data["addopts"])
    if "testpaths" in ini_data:
        result.setdefault("testpaths", ini_data["testpaths"].split())
    if "markers" in ini_data:
        markers = result.setdefault("_extra_markers", [])
        markers.extend(ini_data["markers"].split("\n"))
    if "filterwarnings" in ini_data:
        result.setdefault("filterwarnings", ini_data["filterwarnings"].split("\n"))
    if "ignore" in ini_data:
        result.setdefault("ignore", [])
        result["ignore"].extend(ini_data["ignore"].split())
    if "norecursedirs" in ini_data:
        result.setdefault("ignore", [])
        result["ignore"].extend(ini_data["norecursedirs"].split())
    return result


def _find_pyproject_toml():
    cwd = os.getcwd()
    path = os.path.join(cwd, "pyproject.toml")
    if os.path.isfile(path):
        return path
    parent = os.path.dirname(cwd)
    if parent and parent != cwd:
        parent_path = os.path.join(parent, "pyproject.toml")
        if os.path.isfile(parent_path):
            return parent_path
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


__all__ = [
    "load_config",
    "merge_config_with_opts",
]


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
        elif arg == "-m" and i + 1 < len(args):
            i += 1
            result["marker_expr"] = args[i]
        elif arg.startswith("--tb="):
            result["tb_style"] = arg[5:]
        elif arg == "--tb" and i + 1 < len(args):
            i += 1
            result["tb_style"] = args[i]
        elif arg == "-s":
            result["nocapture"] = True
        elif arg == "--maxfail" and i + 1 < len(args):
            i += 1
            result["maxfail"] = int(args[i])
        elif arg == "--no-header":
            result["no_header"] = True
        elif arg == "--capture" and i + 1 < len(args):
            i += 1
            result["capture"] = args[i]
        elif arg == "--show-capture" and i + 1 < len(args):
            i += 1
            result["show_capture"] = args[i]
        elif arg == "--durations" and i + 1 < len(args):
            i += 1
            result["durations"] = int(args[i])
        elif arg.startswith("-r") and len(arg) > 2:
            result["report_summary"] = arg[2:]
        elif arg == "--showlocals":
            result["showlocals"] = True
        elif arg == "--strict-markers":
            result["strict_markers"] = True
        elif arg == "--rootdir" and i + 1 < len(args):
            i += 1
            result["rootdir"] = args[i]
        elif arg == "--fixtures":
            result["fixtures_list"] = True
        elif arg == "--markers":
            result["markers_list"] = True
        elif arg == "--setup-show":
            result["setup_show"] = True
        elif arg == "--setup-only":
            result["setup_only"] = True
        elif arg == "--setup-plan":
            result["setup_plan"] = True
        elif arg in ("--lf", "--last-failed"):
            result["lf"] = True
        elif arg in ("--ff", "--failed-first"):
            result["ff"] = True
        elif arg == "--cache-clear":
            result["cache_clear"] = True
        elif arg == "--pdb":
            result["pdb"] = True
        elif arg == "--trace":
            result["trace"] = True
        elif arg == "--full-trace":
            result["full_trace"] = True
        elif arg == "-n" and i + 1 < len(args):
            i += 1
            if args[i] == "auto":
                import os as _os
                result["num_workers"] = _os.cpu_count() or 1
            else:
                result["num_workers"] = int(args[i])
        elif arg in ("-o", "--override-ini") and i + 1 < len(args):
            i += 1
            result.setdefault("override_ini", []).append(args[i])
        elif arg.startswith("--override-ini="):
            result.setdefault("override_ini", []).append(arg.split("=", 1)[1])
        elif arg == "--deselect" and i + 1 < len(args):
            i += 1
            result.setdefault("deselect", []).append(args[i])
        elif arg == "--confcutdir" and i + 1 < len(args):
            i += 1
            result["confcutdir"] = args[i]
        elif arg == "--noconftest":
            result["noconftest"] = True
        elif arg == "--runxfail":
            result["runxfail"] = True
        elif arg == "--strict-config":
            result["strict_config"] = True
        elif arg == "--basetemp" and i + 1 < len(args):
            i += 1
            result["basetemp"] = args[i]
        elif arg == "-W" and i + 1 < len(args):
            i += 1
            result.setdefault("filterwarnings", []).append(args[i])
        elif arg == "--import-mode" and i + 1 < len(args):
            i += 1
            result["import_mode"] = args[i]
        elif arg == "--ignore" and i + 1 < len(args):
            i += 1
            result.setdefault("ignore", []).append(args[i])
        elif arg == "--ignore-glob" and i + 1 < len(args):
            i += 1
            result.setdefault("ignore_glob", []).append(args[i])
        elif arg in ("--collect-only", "--co"):
            result["collect_only"] = True
        elif arg == "--continue-on-collection-errors":
            result["continue_on_collection_errors"] = True
        elif arg == "--color" and i + 1 < len(args):
            i += 1
            result["color"] = args[i]
        elif arg == "--code-highlight":
            result["code_highlight"] = True
        elif arg == "--stepwise":
            result["stepwise"] = True
        elif arg == "--stepwise-skip":
            result["stepwise_skip"] = True
        elif arg == "--doctest-modules":
            result["doctest_modules"] = True
        elif arg == "--doctest-glob" and i + 1 < len(args):
            i += 1
            result.setdefault("doctest_glob", []).append(args[i])
        elif arg == "--doctest-continue-on-error":
            result["doctest_continue_on_error"] = True
        elif arg == "--log-level" and i + 1 < len(args):
            i += 1
            result["log_level"] = args[i]
        elif arg == "--log-format" and i + 1 < len(args):
            i += 1
            result["log_format"] = args[i]
        elif arg == "--log-cli-level" and i + 1 < len(args):
            i += 1
            result["log_cli_level"] = args[i]
        elif arg == "--junitxml" and i + 1 < len(args):
            i += 1
            result["junitxml"] = args[i]
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
