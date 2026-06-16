import os

from oxytest._config import (
    load_config,
    _find_pyproject_toml,
    merge_config_with_opts,
    _parse_and_merge,
)


def test_find_pyproject_toml_none(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = _find_pyproject_toml()
        assert result is None
    finally:
        os.chdir(old_cwd)


def test_find_pyproject_toml_found(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.oxytest]\naddopts = \"-v\"\n")
        result = _find_pyproject_toml()
        assert result is not None
        assert "pyproject.toml" in result
    finally:
        os.chdir(old_cwd)


def test_load_config_no_file(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = load_config()
        assert result == {}
    finally:
        os.chdir(old_cwd)


def test_load_config_with_file(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.oxytest]\naddopts = \"-v\"\ntestpaths = [\"tests/\"]\n")
        result = load_config()
        assert result.get("addopts") == "-v"
        assert result.get("testpaths") == ["tests/"]
    finally:
        os.chdir(old_cwd)


def test_load_config_not_toml(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not valid toml {{{")
        result = load_config()
        assert result == {}
    finally:
        os.chdir(old_cwd)


def test_load_config_empty(tmp_path):
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("")
        result = load_config()
        assert result == {}
    finally:
        os.chdir(old_cwd)


def test_load_config_path_not_found(tmp_path):
    result = load_config(path=str(tmp_path / "nonexistent.toml"))
    assert result == {}


def test_load_config_specific_path(tmp_path):
    pyproject = tmp_path / "mypyproject.toml"
    pyproject.write_text("[tool.oxytest]\nverbose = true\n")
    result = load_config(path=str(pyproject))
    assert result == {"verbose": True}


def test_merge_config_with_opts_empty():
    opts = {"verbose": False, "paths": ["."]}
    result = merge_config_with_opts({}, opts)
    assert result == opts


def test_merge_config_with_opts_addopts():
    config_data = {"addopts": "-v --tb=long"}
    opts = {"verbose": False, "quiet": False, "tb_style": "short", "paths": ["."]}
    result = merge_config_with_opts(config_data, opts)
    assert result["verbose"] is True
    assert result["tb_style"] == "long"


def test_merge_config_with_opts_testpaths():
    config_data = {"testpaths": ["src/tests/"]}
    opts = {"verbose": False, "paths": ["."]}
    result = merge_config_with_opts(config_data, opts)
    assert result["paths"] == ["src/tests/"]


def test_merge_config_with_opts_ignore():
    config_data = {"ignore": ["old/", "legacy/"]}
    opts = {"verbose": False, "ignore": [], "paths": ["."]}
    result = merge_config_with_opts(config_data, opts)
    assert result["ignore"] == ["old/", "legacy/"]


def test_merge_config_with_opts_markers():
    config_data = {"markers": ["slow: marks slow tests"]}
    opts = {"verbose": False, "paths": ["."], "_extra_markers": []}
    result = merge_config_with_opts(config_data, opts)
    assert "_extra_markers" in result
    assert "slow: marks slow tests" in result["_extra_markers"]


def test_parse_and_merge_empty():
    result = _parse_and_merge([], {})
    assert result == {}


def test_parse_and_merge_verbose():
    result = _parse_and_merge(["-v"], {"verbose": False})
    assert result["verbose"] is True


def test_parse_and_merge_quiet():
    result = _parse_and_merge(["-q"], {"quiet": False})
    assert result["quiet"] is True


def test_parse_and_merge_exitfirst():
    result = _parse_and_merge(["-x"], {"exitfirst": False})
    assert result["exitfirst"] is True


def test_parse_and_merge_keyword():
    result = _parse_and_merge(["-k", "test_foo"], {"keyword": None})
    assert result["keyword"] == "test_foo"


def test_parse_and_merge_tb_equals():
    result = _parse_and_merge(["--tb=long"], {"tb_style": "short"})
    assert result["tb_style"] == "long"


def test_parse_and_merge_tb_space():
    result = _parse_and_merge(["--tb", "no"], {"tb_style": "short"})
    assert result["tb_style"] == "no"


def test_parse_and_merge_n_workers():
    result = _parse_and_merge(["-n", "4"], {"num_workers": None})
    assert result["num_workers"] == 4


def test_parse_and_merge_n_auto():
    result = _parse_and_merge(["-n", "auto"], {"num_workers": None})
    assert result["num_workers"] is not None
    assert result["num_workers"] >= 1


def test_parse_and_merge_durations():
    result = _parse_and_merge(["--durations", "5"], {"durations": None})
    assert result["durations"] == 5


def test_parse_and_merge_cov_bare():
    result = _parse_and_merge(["--cov"], {"cov_source": None})
    assert result["cov_source"] is True


def test_parse_and_merge_cov_value():
    result = _parse_and_merge(["--cov", "src/"], {"cov_source": None})
    assert result["cov_source"] == "src/"


def test_parse_and_merge_cov_equals():
    result = _parse_and_merge(["--cov=src/"], {"cov_source": None})
    assert result["cov_source"] == "src/"


def test_parse_and_merge_cov_report():
    result = _parse_and_merge(["--cov-report", "html"], {"cov_report": "term"})
    assert result["cov_report"] == "html"


def test_parse_and_merge_cov_config():
    result = _parse_and_merge(["--cov-config", ".coveragerc"], {"cov_config": None})
    assert result["cov_config"] == ".coveragerc"


def test_parse_and_merge_cov_branch():
    result = _parse_and_merge(["--cov-branch"], {"cov_branch": False})
    assert result["cov_branch"] is True


def test_parse_and_merge_cov_fail_under():
    result = _parse_and_merge(["--cov-fail-under", "80"], {"cov_fail_under": None})
    assert result["cov_fail_under"] == 80.0


def test_parse_and_merge_cov_append():
    result = _parse_and_merge(["--cov-append"], {"cov_append": False})
    assert result["cov_append"] is True


def test_parse_and_merge_report_summary():
    result = _parse_and_merge(["-rA"], {"report_summary": None})
    assert result["report_summary"] == "A"


def test_load_config_tomli_fallback():
    result = load_config(path="/nonexistent/path")
    assert result == {}


def test_find_pyproject_toml_parent_dir(tmp_path):
    old_cwd = os.getcwd()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    os.chdir(subdir)
    try:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.oxytest]\nkey = \"val\"\n")
        result = _find_pyproject_toml()
        assert result is None
    finally:
        os.chdir(old_cwd)
