# Migrating from pytest to oxytest

Oxytest is designed as a **drop-in replacement** for pytest. In most cases, migrating is as simple as changing one line of code.

## Quick Migration

### 1. Install oxytest

```bash
pip install oxytest
```

### 2. Replace the import

**Before (pytest):**
```python
import pytest
```

**After (oxytest):**
```python
import oxytest as pytest
```

That's it. Your existing tests should work without changes.

### 3. Update your CI/CD

Replace `pytest` with `oxytest` in your CI configuration:

```yaml
# GitHub Actions
- name: Run tests
  run: oxytest -v -n auto
```

### 4. Update your `main.py` entry points

```python
# Before
import pytest
pytest.main(["-v", "tests/"])

# After
import oxytest as pytest
pytest.main(["-v", "tests/"])
```

### 5. Automated migration with `oxytest migrate`

Oxytest includes a built-in migration tool that automatically rewrites your imports:

```bash
# Preview changes (dry run)
oxytest migrate src/ --dry-run

# Perform migration (pytest → oxytest)
oxytest migrate src/

# Reverse migration (oxytest → pytest)
oxytest migrate src/ --reverse

# Check-only — exits with code 1 if any pytest imports remain
oxytest migrate src/ --check
```

The tool handles:
- `import pytest` → `import oxytest as pytest`
- `from pytest import ...` → `from oxytest import ...`
- `from pytest import approx, raises` → (multi-module imports)
- Aliases (`import pytest as pt` → `import oxytest as pt`)
- Skips comments and strings

## What Works Out of the Box

| Feature | Status |
|---------|--------|
| `pytest.main()` | ✅ |
| `pytest.approx()` | ✅ |
| `pytest.raises()` | ✅ |
| `pytest.fixture()` | ✅ |
| `pytest.mark.parametrize()` | ✅ |
| `pytest.mark.skip()` | ✅ |
| `pytest.mark.skipif()` | ✅ |
| `pytest.mark.xfail()` | ✅ |
| `pytest.mark.usefixtures()` | ✅ |
| `pytest.skip()` | ✅ |
| `pytest.fail()` | ✅ |
| `pytest.importorskip()` | ✅ |
| `pytest.set_trace()` | ✅ |
| `tmp_path` fixture | ✅ |
| `capsys` fixture | ✅ |
| `capfd` fixture | ✅ |
| `monkeypatch` fixture | ✅ |
| `conftest.py` | ✅ |
| Test classes | ✅ |
| Yield fixtures with teardown | ✅ |
| `autouse=True` fixtures | ✅ |
| Assert rewriting with comparison diffs | ✅ |
| Plugin system (pytest_addoption, pytest_configure, etc.) | ✅ |
| `-v`, `-q`, `-x` flags | ✅ |
| `-k` keyword filter | ✅ |
| `-n` parallel execution (built-in) | ✅ |
| JUnit XML output | ✅ |
| `-s` stdout capture control | ✅ |

## What's Different

### 1. Parallel execution is built-in

No need for `pytest-xdist`:

```bash
# pytest (requires plugin)
pip install pytest-xdist
pytest -n 4

# oxytest (built-in)
oxytest -n 4
```

### 2. Faster test discovery

Oxytest uses AST (Abstract Syntax Tree) scanning instead of importing modules. This means discovery is **10-100x faster** for large codebases. The trade-off is that some dynamic test generation patterns (like `__test__` attributes set in `__init__`) may not be discovered.

### 3. No `--coverage` flag

The `--coverage` flag is not implemented. Use `pytest-cov` with pytest for coverage, or use a coverage tool directly.

## CLI Flag Comparison

| pytest | oxytest | Notes |
|--------|---------|-------|
| `pytest` | `oxytest` | Same behavior |
| `-v` | `-v` | ✅ |
| `-q` | `-q` | ✅ |
| `-x` | `-x` | ✅ |
| `-k` | `-k` | ✅ |
| `--tb=short` | `--tb=short` | ✅ |
| `--tb=long` | `--tb=long` | ✅ |
| `--tb=native` | `--tb=native` | ✅ |
| `--tb=no` | `--tb=no` | ✅ |
| `--junitxml` | `--junitxml` | ✅ |
| `-s` | `-s` | ✅ |
| `--maxfail` | `--maxfail` | ✅ |
| `-n` | `-n` | Built-in, no plugin required |
| `--ignore` | `--ignore` | ✅ |
| `--collect-only` | `--collect-only` (+ `--co`) | ✅ |
| `--durations` | `--durations` | ✅ |
| `-r` | `-r` | ✅ |
| `--showlocals` | `--showlocals` | ✅ |
| `--strict-markers` | `--strict-markers` | ✅ |
| `--rootdir` | `--rootdir` | ✅ |
| `--fixtures` | `--fixtures` | ✅ |
| `--markers` | `--markers` | ✅ |
| `--setup-show` | `--setup-show` | ✅ |
| `--cache-clear` | `--cache-clear` | ✅ |
| `--lf` | `--lf` | ✅ |
| `--ff` | `--ff` | ✅ |
| `-p` plugins | `-p` plugins | ✅ Built-in, no plugin required |
| `--coverage` | — | Not supported |
| `--pdb` | — | Use `pytest.set_trace()` |

## Troubleshooting

### Test not found?
Make sure your test files follow the convention: `test_*.py` or `*_test.py`.

### Fixture not found?
Oxytest supports built-in fixtures (`tmp_path`, `capsys`, `monkeypatch`) and fixtures defined with `@pytest.fixture`. Ensure your conftest.py is in the correct directory.

### Import error?
Oxytest runs tests in the same process. If you have module-level side effects in your test files, they may behave differently. Use `conftest.py` for shared setup.
