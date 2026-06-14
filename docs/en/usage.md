# Usage

## Command Line

```
usage: oxytest [options] [paths]

Options:
  -v, --verbose       Increase verbosity
  -q, --quiet         Quiet output
  -x, --exitfirst     Exit on first failure
  -k EXPRESSION       Filter tests by keyword expression
  --tb=style          Traceback style (short, long, native, no)
  -n WORKERS          Number of parallel workers (default: CPU count)
  --junitxml=PATH     Generate JUnit XML report
  -s                  Don't capture stdout/stderr
  --maxfail=N         Stop after N failures
  --coverage          Enable coverage (experimental)
  --version           Show version
  -h, --help          Show this help message
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

# Stop after first failure
oxytest -x

# Run tests matching a keyword
oxytest -k "user or auth"

# Generate JUnit XML report
oxytest --junitxml report.xml

# Run with short tracebacks (default)
oxytest --tb=short

# Suppress traceback output
oxytest --tb=no

# Combine flags
oxytest -v -n 4 -x tests/
```

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
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
| 2 | Test execution error |
