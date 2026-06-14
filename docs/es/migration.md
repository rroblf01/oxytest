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
| `pytest.skip()` | ✅ |
| `pytest.fail()` | ✅ |
| `pytest.importorskip()` | ✅ |
| `pytest.set_trace()` | ✅ |
| Fixture `tmp_path` | ✅ |
| Fixture `capsys` | ✅ |
| Fixture `monkeypatch` | ✅ |
| `conftest.py` | ✅ |
| Clases de tests | ✅ |
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

### 3. Sin sistema de plugins aún

Los plugins de pytest (como `pytest-cov`, `pytest-django`) aún no son soportados. Planeamos añadir soporte para plugins en una versión futura.

### 4. Sin flag `--coverage`

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
| `--junitxml` | `--junitxml` | ✅ |
| `-s` | `-s` | ✅ |
| `--maxfail` | `--maxfail` | ✅ |
| `-n` | `-n` | Integrado, sin plugin |
| `--coverage` | — | No soportado |
| `-p` plugins | — | Aún no soportado |
| `--pdb` | — | Usar `pytest.set_trace()` |

## Solución de Problemas

### ¿Test no encontrado?
Asegúrate de que tus archivos de test sigan la convención: `test_*.py` o `*_test.py`.

### ¿Fixture no encontrado?
Oxytest soporta fixtures integrados (`tmp_path`, `capsys`, `monkeypatch`) y fixtures definidos con `@pytest.fixture`. Asegúrate de que tu `conftest.py` esté en el directorio correcto.

### ¿Error de importación?
Oxytest ejecuta tests en el mismo proceso. Si tienes efectos secundario a nivel de módulo en tus archivos de test, pueden comportarse de manera diferente. Usa `conftest.py` para configuración compartida.
