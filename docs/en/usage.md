# Usage

## Command Line

```
usage: oxytest [options] [paths]

Options:
  -v, --verbose       Increase verbosity
  -q, --quiet         Quiet output
  -x, --exitfirst     Exit on first failure
  -k EXPRESSION       Filter tests by keyword expression (supports and/or/not)
  --tb=style          Traceback style (short, long, native, no)
  -n WORKERS          Number of parallel workers (default: CPU count)
  --junitxml=PATH     Generate JUnit XML report
  -s                  Don't capture stdout/stderr
  --maxfail=N         Stop after N failures
  -p PLUGIN           Load plugin (can be used multiple times)
  --ignore=PATH       Ignore test path (can be used multiple times)
  --collect-only, --co  Only collect tests, don't run
  --durations=N       Show N slowest tests
  -r[chars]           Show extra test summary (-rA, -rf, -rs, ...)
  --showlocals        Show local variables in tracebacks
  --strict-markers    Unknown markers cause errors
  --rootdir=PATH      Set root directory for discovery
  --fixtures          List available fixtures
  --markers           List registered markers
  --setup-show        Print fixture setup/teardown
  --cache-clear       Clear cache before run
  --lf, --last-failed  Run only tests that failed last time
  --ff, --failed-first Run failed tests first, then rest
  --pdb               Drop into debugger on failure
  --trace             Drop into debugger before each test
  --cov[=SOURCE]      Measure code coverage
  --cov-report=TYPE   Coverage report type (term, html, xml)
  --cov-config=FILE   Config file for coverage
  --cov-branch        Enable branch coverage
  --cov-fail-under=N  Fail if coverage below N%
  --cov-append        Append to existing coverage data
  --version           Show version
  -h, --help          Show this help message

Subcommands:
  migrate             Automatically migrate imports between pytest and oxytest
                      (e.g., `oxytest migrate --dry-run`)
```

## Examples

```bash
# Run all tests in current directory
oxytest

# Run tests in a specific directory
oxytest tests/

# Verbose output
oxytest -v

# Quiet mode (dots only)
oxytest -q

# Run in parallel with 8 workers
oxytest -n 8

# Auto-detect CPU count
oxytest -n auto

# Stop after first failure
oxytest -x

# Run tests matching a keyword expression
oxytest -k "user or auth"
oxytest -k "not slow and (math or api)"

# Generate JUnit XML report
oxytest --junitxml report.xml

# Run with short tracebacks (default)
oxytest --tb=short

# Full tracebacks
oxytest --tb=long

# Suppress traceback output
oxytest --tb=no

# Show local variables on failure
oxytest --showlocals

# Show fixture setup/teardown
oxytest --setup-show

# Only collect tests (don't run)
oxytest --collect-only
oxytest --co                         # shorthand

# Show 5 slowest tests
oxytest --durations 5

# Show extra summary (-rA = all, -rf = failures, -rs = skipped)
oxytest -rA

# Ignore specific paths
oxytest --ignore=tests/legacy

# Run only previously failed tests
oxytest --lf
oxytest --last-failed

# Run failed tests first, then the rest
oxytest --ff
oxytest --failed-first

# List available fixtures
oxytest --fixtures

# List registered markers
oxytest --markers

# Drop into debugger on failure
oxytest --pdb

# Drop into debugger before each test
oxytest --trace

# Measure coverage (requires: pip install coverage)
oxytest --cov=src/                         # terminal report
oxytest --cov=src/ --cov-report=html        # HTML report
oxytest --cov=src/ --cov-branch             # branch coverage
oxytest --cov=src/ --cov-fail-under=80      # enforce minimum

# Load a plugin
oxytest -p myplugin

# Combine flags
oxytest -v -n 4 -x tests/

# Migrate imports from pytest to oxytest
oxytest migrate src/
oxytest migrate --dry-run             # preview only
oxytest migrate --reverse             # oxytest → pytest
oxytest migrate --check               # error if any imports found
```

## Configuration via pyproject.toml

Oxytest reads settings from `[tool.oxytest]` in `pyproject.toml`:

```toml
[tool.oxytest]
addopts = "-v --tb=short"
testpaths = ["tests/"]
ignore = ["tests/legacy/"]
markers = [
    "slow: marks slow tests",
    "integration: marks integration tests",
]
cov_source = "src/"
cov_report = "html"
cov_branch = true
cov_fail_under = 80.0
```

CLI flags take precedence over config file values. You can also use `testpaths` to override the default discovery directory.

## VSCode Integration

Oxytest includes a built-in plugin that speaks the VSCode Python extension's test protocol via JSON-RPC 2.0 over a named pipe. No extra dependencies are needed.

### Setup

1. Install oxytest in your VSCode environment.
2. In `.vscode/settings.json`, ensure:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "oxytest"
}
```

Or set `"python.testing.pytestEnabled": true` and ensure oxytest is your default test provider.

### How it works

When VSCode runs pytest with `-p vscode_pytest`, oxytest intercepts this and loads its own `_vscode.py` plugin. This plugin:

- Discovers tests and builds a tree with folder/file/class/function/parametrized nodes
- Sends real-time execution results (pass/fail/skip/error) over a named pipe
- Supports parametrized tests and class-based tests
- Integrates with coverage reporting (if `COVERAGE_ENABLED=True`)

### Supported features

- ✅ Test discovery with full tree structure
- ✅ Real-time execution results
- ✅ Per-test tracebacks and error messages
- ✅ Parametrized test nodes
- ✅ Coverage integration
- ✅ Error, failure, skip, and xfail statuses

## Python API

```python
import oxytest as pytest

# Run tests programmatically
exit_code = pytest.main(["-v", "tests/"])
print(f"Exit code: {exit_code}")

# pytest.approx
result = 0.1 + 0.2
assert result == pytest.approx(0.3)

# pytest.raises
with pytest.raises(ValueError, match="invalid"):
    int("invalid literal")

# pytest.mark.parametrize
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (4, 5, 9),
    (10, 20, 30),
])
def test_add(a, b, expected):
    assert a + b == expected

# pytest.mark.skip
@pytest.mark.skip(reason="not implemented")
def test_todo():
    pass

# pytest.mark.xfail
@pytest.mark.xfail(reason="known bug")
def test_flaky():
    assert False

# pytest.fixture
@pytest.fixture
def database():
    db = create_database()
    yield db
    db.close()

def test_query(database):
    assert database.query("SELECT 1") == 1

# yield fixture with teardown
@pytest.fixture
def resource():
    obj = acquire()
    yield obj
    obj.release()

# autouse fixture
@pytest.fixture(autouse=True)
def setup():
    print("runs before every test")

# Plugin API
from oxytest import hookimpl, hookspec

@hookimpl
def pytest_addoption(parser):
    parser.addoption("--my-flag", action="store_true", help="My custom flag")

@hookimpl
def pytest_configure(config):
    value = config.getoption("--my-flag")
    if value:
        print("Custom flag enabled!")
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
| 2 | Test execution error |
