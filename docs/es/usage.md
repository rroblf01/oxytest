# Uso

## Línea de Comandos

```
uso: oxytest [opciones] [rutas]

Opciones:
  -v, --verbose       Aumentar verbosidad
  -q, --quiet         Salida silenciosa
  -x, --exitfirst     Detener en el primer fallo
  -k EXPRESIÓN        Filtrar tests por expresión clave (soporta and/or/not)
  --tb=estilo         Estilo de traceback (short, long, native, no)
  -n WORKERS          Número de workers paralelos (por defecto: CPUs)
  --junitxml=RUTA     Generar reporte JUnit XML
  -s                  No capturar stdout/stderr
  --maxfail=N         Detener después de N fallos
  -p PLUGIN           Cargar plugin (puede usarse múltiples veces)
  --ignore=RUTA       Ignorar ruta de test (puede usarse múltiples veces)
  --collect-only, --co  Solo recolectar tests, no ejecutar
  --durations=N       Mostrar N tests más lentos
  -r[caracteres]      Mostrar resumen extra (-rA, -rf, -rs, ...)
  --showlocals        Mostrar variables locales en tracebacks
  --strict-markers    Marcadores desconocidos causan error
  --rootdir=RUTA      Establecer directorio raíz para descubrimiento
  --fixtures          Listar fixtures disponibles
  --markers           Listar marcadores registrados
  --setup-show        Imprimir setup/teardown de fixtures
  --cache-clear       Limpiar caché antes de ejecutar
  --lf, --last-failed  Ejecutar solo tests que fallaron la última vez
  --ff, --failed-first Ejecutar tests fallidos primero, luego el resto
  --pdb               Entrar al depurador al fallar
  --trace             Entrar al depurador antes de cada test
  --cov[=FUENTE]      Medir cobertura de código
  --cov-report=TIPO   Tipo de reporte (term, html, xml)
  --cov-config=ARCH   Archivo de configuración para coverage
  --cov-branch        Habilitar cobertura de ramas
  --cov-fail-under=N  Fallar si cobertura menor a N%
  --cov-append        Añadir a datos de cobertura existentes
  --version           Mostrar versión
  -h, --help          Mostrar ayuda

Subcomandos:
  migrate             Migrar automáticamente imports entre pytest y oxytest
                      (ej: `oxytest migrate --dry-run`)
```

## Ejemplos

```bash
# Ejecutar todos los tests en el directorio actual
oxytest

# Ejecutar tests en un directorio específico
oxytest tests/

# Salida detallada
oxytest -v

# Modo silencioso (solo puntos)
oxytest -q

# Ejecutar en paralelo con 8 workers
oxytest -n 8

# Auto-detectar número de CPUs
oxytest -n auto

# Detener tras el primer fallo
oxytest -x

# Ejecutar tests que coincidan con una expresión clave
oxytest -k "user or auth"
oxytest -k "not slow and (math or api)"

# Generar reporte JUnit XML
oxytest --junitxml report.xml

# Tracebacks cortos (por defecto)
oxytest --tb=short

# Tracebacks completos
oxytest --tb=long

# Suprimir tracebacks
oxytest --tb=no

# Mostrar variables locales al fallar
oxytest --showlocals

# Mostrar setup/teardown de fixtures
oxytest --setup-show

# Solo recolectar tests (no ejecutar)
oxytest --collect-only
oxytest --co

# Mostrar 5 tests más lentos
oxytest --durations 5

# Resumen extra (-rA = todos, -rf = fallos, -rs = saltados)
oxytest -rA

# Ignorar rutas específicas
oxytest --ignore=tests/legacy

# Solo tests que fallaron antes
oxytest --lf
oxytest --last-failed

# Fallos primero, luego el resto
oxytest --ff
oxytest --failed-first

# Listar fixtures disponibles
oxytest --fixtures

# Listar marcadores registrados
oxytest --markers

# Entrar al depurador al fallar
oxytest --pdb

# Entrar al depurador antes de cada test
oxytest --trace

# Medir cobertura (requiere: pip install coverage)
oxytest --cov=src/                         # reporte en terminal
oxytest --cov=src/ --cov-report=html        # reporte HTML
oxytest --cov=src/ --cov-branch             # cobertura de ramas
oxytest --cov=src/ --cov-fail-under=80      # exigir mínimo

# Cargar un plugin
oxytest -p miplugin

# Combinar flags
oxytest -v -n 4 -x tests/

# Migrar imports de pytest a oxytest
oxytest migrate src/
oxytest migrate --dry-run             # solo previsualizar
oxytest migrate --reverse             # oxytest → pytest
oxytest migrate --check               # error si encuentra imports
```

## Configuración via pyproject.toml

Oxytest lee la configuración de la sección `[tool.oxytest]` en `pyproject.toml`:

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

Las flags de CLI tienen prioridad sobre los valores del archivo de configuración.

## Integración con VSCode

Oxytest incluye un plugin integrado que habla el protocolo de tests de la extensión de Python de VSCode mediante JSON-RPC 2.0 sobre un pipe nominal. No se necesitan dependencias adicionales.

### Configuración

1. Instala oxytest en tu entorno de VSCode.
2. En `.vscode/settings.json`, asegúrate de tener:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "oxytest"
}
```

### Cómo funciona

Cuando VSCode ejecuta pytest con `-p vscode_pytest`, oxytest intercepta esto y carga su propio plugin `_vscode.py`. Este plugin:

- Descubre tests y construye un árbol con nodos de carpeta/archivo/clase/función/parametrizados
- Envía resultados de ejecución en tiempo real (pass/fail/skip/error) mediante un pipe nominal
- Soporta tests parametrizados y tests basados en clases
- Se integra con informes de cobertura

### Características soportadas

- ✅ Descubrimiento de tests con árbol completo
- ✅ Resultados en tiempo real
- ✅ Trazas y mensajes de error por test
- ✅ Nodos parametrizados
- ✅ Integración con cobertura
- ✅ Estados: error, fallo, salto, xfail

## API de Python

```python
import oxytest as pytest

# Ejecutar tests programáticamente
exit_code = pytest.main(["-v", "tests/"])
print(f"Código de salida: {exit_code}")

# pytest.approx
resultado = 0.1 + 0.2
assert resultado == pytest.approx(0.3)

# pytest.raises
with pytest.raises(ValueError, match="inválido"):
    int("literal inválido")

# pytest.mark.parametrize
@pytest.mark.parametrize("a,b,esperado", [
    (1, 2, 3),
    (4, 5, 9),
    (10, 20, 30),
])
def test_sumar(a, b, esperado):
    assert a + b == esperado

# pytest.mark.skip
@pytest.mark.skip(reason="no implementado")
def test_pendiente():
    pass

# pytest.mark.xfail
@pytest.mark.xfail(reason="bug conocido")
def test_inestable():
    assert False

# pytest.fixture
@pytest.fixture
def base_datos():
    db = crear_base_datos()
    yield db
    db.cerrar()

def test_consulta(base_datos):
    assert base_datos.consultar("SELECT 1") == 1

# yield fixture con teardown
@pytest.fixture
def recurso():
    obj = adquirir()
    yield obj
    obj.liberar()

# autouse fixture
@pytest.fixture(autouse=True)
def setup():
    print("ejecuta antes de cada test")

# API de plugins
from oxytest import hookimpl, hookspec

@hookimpl
def pytest_addoption(parser):
    parser.addoption("--mi-flag", action="store_true", help="Mi flag personalizado")

@hookimpl
def pytest_configure(config):
    value = config.getoption("--mi-flag")
    if value:
        print("¡Flag personalizado activado!")
```

## Códigos de Salida

| Código | Significado |
|--------|-------------|
| 0 | Todos los tests pasaron |
| 1 | Algunos tests fallaron |
| 2 | Error de ejecución de tests |
