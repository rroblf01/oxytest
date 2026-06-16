# Getting Started

## Installation

```bash
pip install oxytest

# For coverage support
pip install oxytest[cov]
```

## Usage

### Command Line

Run tests in the current directory:

```bash
oxytest
```

Run tests in a specific directory:

```bash
oxytest tests/
```

Run with verbose output:

```bash
oxytest -v
```

Run with parallel execution (4 workers):

```bash
oxytest -n 4
```

Stop on first failure:

```bash
oxytest -x
```

Filter by keyword (supports `and`, `or`, `not`, parentheses):

```bash
oxytest -k "math or string"
oxytest -k "not slow and (math or api)"
```

Measure code coverage:

```bash
oxytest --cov=src/ --cov-report=html
```

Debug failures:

```bash
oxytest --pdb          # post-mortem on failure
oxytest --trace        # debugger before every test
```

### Configuration via pyproject.toml

Create a `pyproject.toml` file in your project root:

```toml
[tool.oxytest]
addopts = "-v --tb=short"
testpaths = ["tests/"]
ignore = ["tests/legacy/"]
markers = ["slow: marks slow tests"]
cov_source = "src/"
cov_report = "html"
```

### VSCode Integration

Oxytest includes a built-in VSCode plugin — no extra setup needed. Just set `"python.testing.pytestEnabled": true` in your VSCode settings and oxytest will be detected automatically.

### As a pytest Replacement

```python
# Use oxytest as a drop-in replacement for pytest
import oxytest as pytest

# All standard pytest API is available
pytest.main(["-v", "tests/"])

# Use approx
assert 0.1 + 0.2 == pytest.approx(0.3)

# Use raises
with pytest.raises(ValueError):
    int("not a number")

# Use fixtures
@pytest.fixture
def my_data():
    return {"key": "value"}

# Use markers
@pytest.mark.parametrize("x,expected", [(1, 2), (3, 4)])
def test_double(x, expected):
    assert x * 2 == expected
```

### CI Integration

Replace pytest with oxytest in your CI configuration:

**GitHub Actions:**

```yaml
- name: Run tests
  run: oxytest -v -n auto
```

**GitLab CI:**

```yaml
test:
  script:
    - oxytest -v -n auto
```

**Makefile:**

```makefile
test:
    oxytest -v -n auto
```
