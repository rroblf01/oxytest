# Migración de pytest a oxytest

Oxytest está diseñado como un **reemplazo directo** de pytest. En la mayoría de los casos, migrar es tan simple como cambiar una línea de código.

## Migración Rápida

### 1. Instalar oxytest

```bash
pip install oxytest
```

### 2. Reemplazar el import

**Antes (pytest):**
```python
import pytest
```

**Después (oxytest):**
```python
import oxytest as pytest
```

Eso es todo. Tus tests existentes deberían funcionar sin cambios.

### 3. Actualizar tu CI/CD

Reemplaza `pytest` por `oxytest` en tu configuración de CI:

```yaml
# GitHub Actions
- name: Run tests
  run: oxytest -v -n auto
```

### 4. Actualizar puntos de entrada

```python
# Antes
import pytest
pytest.main(["-v", "tests/"])

# Después
import oxytest as pytest
pytest.main(["-v", "tests/"])
```

### 5. Migración automática con `oxytest migrate`

Oxytest incluye una herramienta de migración integrada que reescribe tus imports automáticamente:

```bash
# Previsualizar cambios (dry run)
oxytest migrate src/ --dry-run

# Realizar migración (pytest → oxytest)
oxytest migrate src/

# Migración reversa (oxytest → pytest)
oxytest migrate src/ --reverse

# Solo verificar — código 1 si quedan imports de pytest
oxytest migrate src/ --check
```

La herramienta maneja:
- `import pytest` → `import oxytest as pytest`
- `from pytest import ...` → `from oxytest import ...`
- `from pytest import approx, raises` → (imports multi-módulo)
- Aliases (`import pytest as pt` → `import oxytest as pt`)
- Omite comentarios y strings

## Qué Funciona de Inmediato

| Característica | Estado |
|----------------|--------|
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
| Fixture `tmp_path` | ✅ |
| Fixture `capsys` | ✅ |
| Fixture `capfd` | ✅ |
| Fixture `monkeypatch` | ✅ |
| `conftest.py` | ✅ |
| Clases de tests | ✅ |
| Yield fixtures con teardown | ✅ |
| Fixtures `autouse=True` | ✅ |
| Reescritura de asserts con diffs | ✅ |
| Sistema de plugins (pytest_addoption, pytest_configure, etc.) | ✅ |
| Flags `-v`, `-q`, `-x` | ✅ |
| Filtro `-k` | ✅ |
| Ejecución paralela `-n` (integrada) | ✅ |
| Salida JUnit XML | ✅ |
| Control de captura `-s` | ✅ |

## Diferencias

### 1. Ejecución paralela integrada

No necesitas `pytest-xdist`:

```bash
# pytest (requiere plugin)
pip install pytest-xdist
pytest -n 4

# oxytest (integrado)
oxytest -n 4
```

### 2. Descubrimiento de tests más rápido

Oxytest usa escaneo AST (Árbol de Sintaxis Abstracta) en lugar de importar módulos. Esto hace que el descubrimiento sea **10-100x más rápido** para proyectos grandes. La desventaja es que algunos patrones de generación dinámica de tests (como atributos `__test__` en `__init__`) pueden no ser descubiertos.

### 3. Sin flag `--coverage`

El flag `--coverage` no está implementado. Usa `pytest-cov` con pytest para cobertura, o una herramienta de cobertura directamente.

## Comparación de Flags CLI

| pytest | oxytest | Notas |
|--------|---------|-------|
| `pytest` | `oxytest` | Mismo comportamiento |
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
| `-n` | `-n` | Integrado, sin plugin |
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
| `-p` plugins | `-p` plugins | ✅ Integrado, sin plugin |
| `--coverage` | — | No soportado |
| `--pdb` | — | Usar `pytest.set_trace()` |

## Solución de Problemas

### ¿Test no encontrado?
Asegúrate de que tus archivos de test sigan la convención: `test_*.py` o `*_test.py`.

### ¿Fixture no encontrado?
Oxytest soporta fixtures integrados (`tmp_path`, `capsys`, `monkeypatch`) y fixtures definidos con `@pytest.fixture`. Asegúrate de que tu `conftest.py` esté en el directorio correcto.

### ¿Error de importación?
Oxytest ejecuta tests en el mismo proceso. Si tienes efectos secundarios a nivel de módulo en tus archivos de test, pueden comportarse de manera diferente. Usa `conftest.py` para configuración compartida.
