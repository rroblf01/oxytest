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

### Reescritura de Asserts
Oxytest reescribe automáticamente los `assert` para producir mensajes detallados:

```python
# En vez de: AssertionError
# Obtienes: AssertionError: assert 1 == 2
#                               1 == 2
assert x == y

# Con --showlocals:
#   AssertionError: assert 1 == 2
#                   1 == 2
#
#   Locals:
#     x = 1
#     y = 2
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

@pytest.fixture(scope="module", autouse=True)
def setup_once():
    print("ejecuta una vez por módulo")
```

### Yield Fixtures
Los yield fixtures ejecutan teardown automáticamente:

```python
@pytest.fixture
def recurso():
    print("setup")
    yield valor
    print("teardown")  # se ejecuta después del test
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

### `pytest.mark.usefixtures(*names)`
Aplica fixtures a un test o clase sin inyectarlos como parámetros.

```python
@pytest.mark.usefixtures("base_datos")
class TestSuite:
    def test_consulta(self):
        ...  # fixture base_datos está activo

@pytest.mark.usefixtures("setup")
def test_con_setup():
    ...
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

### `pytest.param(values, id=None, marks=None)`
Crea un argumento parametrizado con id o marcas personalizadas.

```python
@pytest.mark.parametrize("x", [
    pytest.param(1, id="uno"),
    pytest.param(2, marks=pytest.mark.skip),
])
def test_valores(x):
    ...
```

## Sistema de Plugins

### `hookimpl(tryfirst=False, trylast=False, hookwrapper=False)`
Decorador para implementaciones de hooks de plugins.

```python
from oxytest import hookimpl

@hookimpl
def pytest_addoption(parser):
    parser.addoption("--mi-flag", action="store_true")

@hookimpl(tryfirst=True)
def pytest_configure(config):
    value = config.getoption("--mi-flag")
```

### `hookspec(tryfirst=False, trylast=False)`
Decorador para definir especificaciones de hooks.

### `Config`
Contiene opciones CLI parseadas y estado del plugin.

```python
from oxytest import Config
config = Config(opts)
value = config.getoption("--mi-flag")
```

### `Parser`
Interfaz tipo argparse para hooks `pytest_addoption`.

```python
parser.addoption("--mi-flag", action="store_true", help="...")
```

### `PluginManager`
Gestiona registro de plugins y llamadas a hooks.

```python
from oxytest import get_plugin_manager
pm = get_plugin_manager()
pm.load_entry_point_plugins()
```

### `get_plugin_manager()`
Obtiene la instancia singleton del gestor de plugins.

## Herramienta de Migración

```bash
# Previsualizar migración de pytest → oxytest
oxytest migrate src/ --dry-run

# Realizar migración
oxytest migrate src/

# Reversa: oxytest → pytest
oxytest migrate src/ --reverse

# Solo verificar (código 1 si encuentra imports de pytest)
oxytest migrate src/ --check
```

## Flags de CLI

| Flag | Descripción |
|------|-------------|
| `-v`, `--verbose` | Aumentar verbosidad |
| `-q`, `--quiet` | Salida silenciosa |
| `-x`, `--exitfirst` | Detener en el primer fallo |
| `-k EXPR` | Filtrar tests por expresión clave |
| `--tb=estilo` | Estilo de traceback (short, long, native, no) |
| `-n WORKERS` | Número de workers paralelos (`auto` = CPUs) |
| `--junitxml=RUTA` | Generar reporte JUnit XML |
| `-s` | No capturar stdout/stderr |
| `--maxfail=N` | Detener después de N fallos |
| `-p PLUGIN` | Cargar plugin (repetible) |
| `--ignore=RUTA` | Ignorar ruta de test (repetible) |
| `--collect-only`, `--co` | Solo recolectar tests |
| `--durations=N` | Mostrar N tests más lentos |
| `-r[caracteres]` | Resumen extra (-rA, -rf, -rs) |
| `--showlocals` | Mostrar variables locales en tracebacks |
| `--strict-markers` | Marcadores desconocidos causan error |
| `--rootdir=RUTA` | Directorio raíz para descubrimiento |
| `--fixtures` | Listar fixtures disponibles |
| `--markers` | Listar marcadores registrados |
| `--setup-show` | Imprimir setup/teardown de fixtures |
| `--cache-clear` | Limpiar caché antes de ejecutar |
| `--lf`, `--last-failed` | Solo tests que fallaron antes |
| `--ff`, `--failed-first` | Fallos primero, luego el resto |
| `--pdb` | Depurador post-mortem al fallar |
| `--trace` | Depurador antes de cada test |
| `--cov[=FUENTE]` | Medir cobertura de código |
| `--cov-report=TIPO` | Tipo de reporte (term, html, xml) |
| `--cov-config=ARCHIVO` | Archivo de configuración para coverage |
| `--cov-branch` | Habilitar cobertura de ramas |
| `--cov-fail-under=N` | Fallar si cobertura menor a N% |
| `--cov-append` | Añadir a datos de cobertura existentes |
| `--version` | Mostrar versión |
| `-h`, `--help` | Mostrar ayuda |

## Códigos de Salida

| Código | Significado |
|--------|-------------|
| 0 | Todos los tests pasaron |
| 1 | Algunos tests fallaron |
| 2 | Error de ejecución de tests |
| 4 | No se recolectaron tests |
