"""Tests for CLI argument parsing (_parse_args)."""

from oxytest._compat import _parse_args


def test_parse_defaults():
    opts = _parse_args([])
    assert opts["verbose"] is False
    assert opts["quiet"] is False
    assert opts["exitfirst"] is False
    assert opts["keyword"] is None
    assert opts["tb_style"] == "short"
    assert opts["nocapture"] is False
    assert opts["collect_only"] is False
    assert opts["runxfail"] is False
    assert opts["strict_config"] is False
    assert opts["basetemp"] is None


def test_parse_verbose():
    opts = _parse_args(["-v"])
    assert opts["verbose"] is True


def test_parse_quiet():
    opts = _parse_args(["-q"])
    assert opts["quiet"] is True


def test_parse_exitfirst():
    opts = _parse_args(["-x"])
    assert opts["exitfirst"] is True


def test_parse_keyword():
    opts = _parse_args(["-k", "test_foo"])
    assert opts["keyword"] == "test_foo"


def test_parse_marker_expr():
    opts = _parse_args(["-m", "slow"])
    assert opts["marker_expr"] == "slow"


def test_parse_tb_short():
    opts = _parse_args(["--tb=short"])
    assert opts["tb_style"] == "short"
    opts2 = _parse_args(["--tb", "long"])
    assert opts2["tb_style"] == "long"


def test_parse_num_workers():
    opts = _parse_args(["-n", "4"])
    assert opts["num_workers"] == 4


def test_parse_num_workers_auto():
    opts = _parse_args(["-n", "auto"])
    assert isinstance(opts["num_workers"], int)
    assert opts["num_workers"] > 0


def test_parse_junitxml():
    opts = _parse_args(["--junitxml", "report.xml"])
    assert opts["junitxml"] == "report.xml"


def test_parse_nocapture():
    opts = _parse_args(["-s"])
    assert opts["nocapture"] is True


def test_parse_maxfail():
    opts = _parse_args(["--maxfail", "5"])
    assert opts["maxfail"] == 5


def test_parse_plugin():
    opts = _parse_args(["-p", "no:anyio"])
    assert "plugins" not in opts or opts["plugins"] is not None  # should not crash


def test_parse_ignore():
    opts = _parse_args(["--ignore", "tests/foo"])
    assert opts["ignore"] == ["tests/foo"]
    opts2 = _parse_args(["--ignore", "a", "--ignore", "b"])
    assert opts2["ignore"] == ["a", "b"]


def test_parse_collect_only():
    opts = _parse_args(["--collect-only"])
    assert opts["collect_only"] is True
    opts2 = _parse_args(["--co"])
    assert opts2["collect_only"] is True


def test_parse_durations():
    opts = _parse_args(["--durations", "10"])
    assert opts["durations"] == 10


def test_parse_report_summary():
    opts = _parse_args(["-rA"])
    assert opts["report_summary"] == "A"
    opts2 = _parse_args(["-rf"])
    assert opts2["report_summary"] == "f"


def test_parse_showlocals():
    opts = _parse_args(["--showlocals"])
    assert opts["showlocals"] is True


def test_parse_strict_markers():
    opts = _parse_args(["--strict-markers"])
    assert opts["strict_markers"] is True


def test_parse_rootdir():
    opts = _parse_args(["--rootdir", "/tmp"])
    assert opts["rootdir"] == "/tmp"


def test_parse_fixtures():
    opts = _parse_args(["--fixtures"])
    assert opts["fixtures_list"] is True


def test_parse_markers():
    opts = _parse_args(["--markers"])
    assert opts["markers_list"] is True


def test_parse_setup_show():
    opts = _parse_args(["--setup-show"])
    assert opts["setup_show"] is True


def test_parse_last_failed():
    opts = _parse_args(["--lf"])
    assert opts["lf"] is True
    opts2 = _parse_args(["--last-failed"])
    assert opts2["lf"] is True


def test_parse_failed_first():
    opts = _parse_args(["--ff"])
    assert opts["ff"] is True


def test_parse_cache_clear():
    opts = _parse_args(["--cache-clear"])
    assert opts["cache_clear"] is True


def test_parse_pdb():
    opts = _parse_args(["--pdb"])
    assert opts["pdb"] is True


def test_parse_trace():
    opts = _parse_args(["--trace"])
    assert opts["trace"] is True
    assert opts["pdb"] is True  # --trace implies --pdb


def test_parse_override_ini():
    opts = _parse_args(["--override-ini", "filterwarnings=error"])
    assert opts["override_ini"] == "filterwarnings=error"


def test_parse_confcutdir():
    opts = _parse_args(["--confcutdir", "src"])
    assert opts["confcutdir"] == "src"


def test_parse_runxfail():
    opts = _parse_args(["--runxfail"])
    assert opts["runxfail"] is True


def test_parse_strict_config():
    opts = _parse_args(["--strict-config"])
    assert opts["strict_config"] is True


def test_parse_basetemp():
    opts = _parse_args(["--basetemp", "/tmp/oxytest_base"])
    assert opts["basetemp"] == "/tmp/oxytest_base"


def test_parse_cov():
    opts = _parse_args(["--cov"])
    assert opts["cov_source"] is True
    opts2 = _parse_args(["--cov", "src/"])
    assert opts2["cov_source"] == "src/"


def test_parse_cov_report():
    opts = _parse_args(["--cov-report", "html"])
    assert opts["cov_report"] == "html"


def test_parse_help():
    opts = _parse_args(["-h"])
    assert opts["help"] is True


def test_parse_version():
    opts = _parse_args(["--version"])
    assert opts["version"] is True


def test_parse_paths():
    opts = _parse_args(["tests/"])
    assert opts["paths"] == ["tests/"]


def test_parse_multiple_paths():
    opts = _parse_args(["tests/", "other/"])
    assert opts["paths"] == ["tests/", "other/"]


def test_parse_combined():
    opts = _parse_args(["-v", "-x", "--tb=long", "tests/"])
    assert opts["verbose"] is True
    assert opts["exitfirst"] is True
    assert opts["tb_style"] == "long"
    assert opts["paths"] == ["tests/"]


def test_parse_ignore_unknown():
    opts = _parse_args(["--unknown-flag"])
    assert opts is not None


# ── New 3.0.0 CLI flag tests ────────────────────────────────────────


def test_parse_no_header():
    opts = _parse_args(["--no-header"])
    assert opts["no_header"] is True


def test_parse_capture():
    opts = _parse_args(["--capture", "fd"])
    assert opts["capture"] == "fd"
    opts2 = _parse_args(["--capture", "no"])
    assert opts2["capture"] == "no"


def test_parse_show_capture():
    opts = _parse_args(["--show-capture", "all"])
    assert opts["show_capture"] == "all"


def test_parse_deselect():
    opts = _parse_args(["--deselect", "test_foo.py"])
    assert "test_foo.py" in opts["deselect"]


def test_parse_W():
    opts = _parse_args(["-W", "ignore"])
    assert "ignore" in opts["pythonwarnings"]


def test_parse_import_mode():
    opts = _parse_args(["--import-mode", "prepend"])
    assert opts["import_mode"] == "prepend"


def test_parse_ignore_glob():
    opts = _parse_args(["--ignore-glob", "*.pyc"])
    assert "*.pyc" in opts["ignore_glob"]


def test_parse_continue_on_collection_errors():
    opts = _parse_args(["--continue-on-collection-errors"])
    assert opts["continue_on_collection_errors"] is True


def test_parse_log_level():
    opts = _parse_args(["--log-level", "DEBUG"])
    assert opts["log_level"] == "DEBUG"


def test_parse_log_format():
    opts = _parse_args(["--log-format", "%(message)s"])
    assert opts["log_format"] == "%(message)s"


def test_parse_log_cli_level():
    opts = _parse_args(["--log-cli-level", "INFO"])
    assert opts["log_cli_level"] == "INFO"


def test_parse_color():
    opts = _parse_args(["--color", "yes"])
    assert opts["color"] == "yes"


def test_parse_code_highlight():
    opts = _parse_args(["--code-highlight"])
    assert opts["code_highlight"] is True


def test_parse_stepwise_skip():
    opts = _parse_args(["--stepwise-skip"])
    assert opts["stepwise_skip"] is True


def test_parse_full_trace():
    opts = _parse_args(["--full-trace"])
    assert opts["full_trace"] is True


def test_parse_setup_only():
    opts = _parse_args(["--setup-only"])
    assert opts["setup_only"] is True


def test_parse_setup_plan():
    opts = _parse_args(["--setup-plan"])
    assert opts["setup_plan"] is True


def test_parse_cov_config():
    opts = _parse_args(["--cov-config", ".coveragerc"])
    assert opts["cov_config"] == ".coveragerc"


def test_parse_cov_branch():
    opts = _parse_args(["--cov-branch"])
    assert opts["cov_branch"] is True


def test_parse_cov_fail_under():
    opts = _parse_args(["--cov-fail-under", "80"])
    assert opts["cov_fail_under"] == 80.0


def test_parse_cov_append():
    opts = _parse_args(["--cov-append"])
    assert opts["cov_append"] is True


def test_parse_override_ini_equals():
    opts = _parse_args(["--override-ini=filterwarnings=error"])
    assert opts["override_ini"] == "filterwarnings=error"
