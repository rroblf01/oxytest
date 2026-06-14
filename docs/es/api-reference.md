# Referencia de API

## Ejecutor de Tests

### `pytest.main(args=None)`
Ejecuta tests con los argumentos dados. Retorna código de salida (0 = todos pasaron).

```python
import oxytest as pytest
exit_code = pytest.main(["-v", "tests/"])
```

### `pytest.discover_tests(root_dir, pattern=None)`
Descubre tests en un directorio. Retorna lista de objetos `TestItem`.

```python
from oxytest import discover_tests
tests = discover_tests("tests/")
```

### `pytest.run_tests(tests, num_workers=None, nocapture=False)`
Ejecuta tests en paralelo usando el pool de hilos Rayon.

### `pytest.run_tests_sequential(tests, nocapture=False)`
Ejecuta tests secuencialmente en el hilo actual.

## Aserciones

### `pytest.approx(expected, rel=None, abs=None, nan_ok=False)`
Aserta igualdad aproximada para números de punto flotante.

```python
assert 0.1 + 0.2 == pytest.approx(0.3)
```

### `pytest.raises(expected_exception, match=None)`
Aserta que un bloque lanza una excepción.

```python
with pytest.raises(ValueError, match="inválido"):
    int("literal inválido")
```

## Fixtures

### `pytest.fixture(scope="function", params=None, autouse=False, name=None)`
Decorador para definir un fixture.

```python
@pytest.fixture
def base_datos():
    db = crear_base_datos()
    yield db
    db.cerrar()
```

### Fixtures Integrados

| Fixture | Descripción |
|---------|-------------|
| `tmp_path` | Directorio temporal (`pathlib.Path`), limpiado tras el test |
| `tmpdir` | Directorio temporal (`str`), legado |
| `capsys` | Capturar stdout/stderr durante el test |
| `capfd` | Capturar descriptores de archivo durante el test |
| `monkeypatch` | Modificar atributos, entorno y diccionarios |

```python
def test_con_tmp_path(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    assert d.exists()

def test_captura(capsys):
    print("hola")
    out, err = capsys.readouterr()
    assert "hola" in out
```

## Marcadores

### `pytest.mark.parametrize(argnames, argvalues)`
Ejecuta un test múltiples veces con diferentes argumentos.

```python
@pytest.mark.parametrize("x,esperado", [(1, 2), (3, 6)])
def test_doble(x, esperado):
    assert x * 2 == esperado
```

### `pytest.mark.skip(reason=None)`
Salta un test.

```python
@pytest.mark.skip(reason="no implementado")
def test_pendiente():
    pass
```

### `pytest.mark.skipif(condition, reason=None)`
Salta un test condicionalmente.

```python
import sys
@pytest.mark.skipif(sys.version_info < (3, 10), reason="necesita 3.10+")
def test_nueva_funcionalidad():
    pass
```

### `pytest.mark.xfail(reason=None, condition=None, raises=None, strict=None)`
Marca un test como que se espera que falle.

```python
@pytest.mark.xfail(reason="problema conocido")
def test_inestable():
    assert False
```

## Utilidades

### `pytest.skip(reason)`
Salta el test actual de forma imperativa.

### `pytest.fail(reason)`
Falla el test actual de forma imperativa.

### `pytest.importorskip(modname, minversion=None, reason=None)`
Importa un módulo o salta si no está disponible.

### `pytest.set_trace()`
Inicia un depurador (usa `pdb`).

### `pytest.exit(exit_code=0)`
Sale de la sesión de tests.

## Flags de CLI

| Flag | Descripción |
|------|-------------|
| `-v`, `--verbose` | Aumentar verbosidad |
| `-q`, `--quiet` | Salida silenciosa |
| `-x`, `--exitfirst` | Detener en el primer fallo |
| `-k EXPR` | Filtrar tests por expresión clave |
| `--tb=estilo` | Estilo de traceback (short, long, native, no) |
| `-n WORKERS` | Número de workers paralelos |
| `--junitxml=RUTA` | Generar reporte JUnit XML |
| `-s` | No capturar stdout/stderr |
| `--maxfail=N` | Detener después de N fallos |
| `--version` | Mostrar versión |
| `-h`, `--help` | Mostrar ayuda |

## Códigos de Salida

| Código | Significado |
|--------|-------------|
| 0 | Todos los tests pasaron |
| 1 | Algunos tests fallaron |
