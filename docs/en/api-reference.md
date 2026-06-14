# API Reference

## Test Runner

### `pytest.main(args=None)`
Run tests with the given arguments. Returns exit code (0 = all passed).

```python
import oxytest as pytest
exit_code = pytest.main(["-v", "tests/"])
```

### `pytest.discover_tests(root_dir, pattern=None)`
Discover tests in a directory. Returns list of `TestItem` objects.

```python
from oxytest import discover_tests
tests = discover_tests("tests/")
```

### `pytest.run_tests(tests, num_workers=None, nocapture=False)`
Run tests in parallel using Rayon thread pool.

### `pytest.run_tests_sequential(tests, nocapture=False)`
Run tests sequentially in the current thread.

## Assertions

### `pytest.approx(expected, rel=None, abs=None, nan_ok=False)`
Assert approximate equality for floating-point numbers.

```python
assert 0.1 + 0.2 == pytest.approx(0.3)
```

### `pytest.raises(expected_exception, match=None)`
Assert that a block raises an exception.

```python
with pytest.raises(ValueError, match="invalid"):
    int("invalid")
```

## Fixtures

### `pytest.fixture(scope="function", params=None, autouse=False, name=None)`
Decorator to define a fixture.

```python
@pytest.fixture
def database():
    db = create_database()
    yield db
    db.close()
```

### Built-in Fixtures

| Fixture | Description |
|---------|-------------|
| `tmp_path` | Temporary directory (`pathlib.Path`), cleaned after test |
| `tmpdir` | Temporary directory (`str`), legacy |
| `capsys` | Capture stdout/stderr during test |
| `capfd` | Capture file descriptors during test |
| `monkeypatch` | Monkey-patch attributes, environment, and dicts |

```python
def test_with_tmp_path(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    assert d.exists()

def test_capture(capsys):
    print("hello")
    out, err = capsys.readouterr()
    assert "hello" in out
```

## Markers

### `pytest.mark.parametrize(argnames, argvalues)`
Run a test multiple times with different arguments.

```python
@pytest.mark.parametrize("x,expected", [(1, 2), (3, 6)])
def test_double(x, expected):
    assert x * 2 == expected
```

### `pytest.mark.skip(reason=None)`
Skip a test.

```python
@pytest.mark.skip(reason="not implemented")
def test_todo():
    pass
```

### `pytest.mark.skipif(condition, reason=None)`
Skip a test conditionally.

```python
import sys
@pytest.mark.skipif(sys.version_info < (3, 10), reason="needs 3.10+")
def test_new_feature():
    pass
```

### `pytest.mark.xfail(reason=None, condition=None, raises=None, strict=None)`
Mark a test as expected to fail.

```python
@pytest.mark.xfail(reason="known issue")
def test_flaky():
    assert False
```

## Utilities

### `pytest.skip(reason)`
Skip the current test imperatively.

### `pytest.fail(reason)`
Fail the current test imperatively.

### `pytest.importorskip(modname, minversion=None, reason=None)`
Import a module or skip if not available.

### `pytest.set_trace()`
Drop into a debugger (uses `pdb`).

### `pytest.exit(exit_code=0)`
Exit the test session.

## CLI Flags

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Increase verbosity |
| `-q`, `--quiet` | Quiet output |
| `-x`, `--exitfirst` | Stop on first failure |
| `-k EXPR` | Filter tests by keyword |
| `--tb=style` | Traceback style (short, long, native, no) |
| `-n WORKERS` | Number of parallel workers |
| `--junitxml=PATH` | Generate JUnit XML report |
| `-s` | Don't capture stdout/stderr |
| `--maxfail=N` | Stop after N failures |
| `--version` | Show version |
| `-h`, `--help` | Show help |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
