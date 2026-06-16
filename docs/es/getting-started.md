# Primeros Pasos

## Instalación

```bash
pip install oxytest

# Para soporte de cobertura
pip install oxytest[cov]
```

## Uso

### Línea de Comandos

Ejecutar tests en el directorio actual:

```bash
oxytest
```

Ejecutar tests en un directorio específico:

```bash
oxytest tests/
```

Ejecutar con salida detallada:

```bash
oxytest -v
```

Ejecutar con paralelismo (4 workers):

```bash
oxytest -n 4
```

Detener en el primer fallo:

```bash
oxytest -x
```

Filtrar por palabra clave (soporta `and`, `or`, `not`, paréntesis):

```bash
oxytest -k "math or string"
oxytest -k "not slow and (math or api)"
```

Medir cobertura de código:

```bash
oxytest --cov=src/ --cov-report=html
```

Depurar fallos:

```bash
oxytest --pdb          # depurador post-mortem
oxytest --trace        # depurador antes de cada test
```

### Configuración via pyproject.toml

Crea un archivo `pyproject.toml` en la raíz de tu proyecto:

```toml
[tool.oxytest]
addopts = "-v --tb=short"
testpaths = ["tests/"]
ignore = ["tests/legacy/"]
markers = ["slow: marks slow tests"]
cov_source = "src/"
cov_report = "html"
```

### Integración con VSCode

Oxytest incluye un plugin integrado para VSCode — no necesita configuración adicional. Solo activa `"python.testing.pytestEnabled": true` en los ajustes de VSCode.

### Como Reemplazo de pytest

```python
# Usar oxytest como reemplazo directo de pytest
import oxytest as pytest

# Toda la API estándar de pytest está disponible
pytest.main(["-v", "tests/"])

# Usar approx
assert 0.1 + 0.2 == pytest.approx(0.3)

# Usar raises
with pytest.raises(ValueError):
    int("no es un número")

# Usar fixtures
@pytest.fixture
def my_data():
    return {"key": "value"}

# Usar marcadores
@pytest.mark.parametrize("x,expected", [(1, 2), (3, 4)])
def test_double(x, expected):
    assert x * 2 == expected
```

### Integración en CI

Reemplaza pytest por oxytest en tu configuración de CI:

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
