# Uso

## Línea de Comandos

```
uso: oxytest [opciones] [rutas]

Opciones:
  -v, --verbose       Aumentar verbosidad
  -q, --quiet         Salida silenciosa
  -x, --exitfirst     Detener en el primer fallo
  -k EXPRESIÓN        Filtrar tests por expresión clave
  --tb=estilo         Estilo de traceback (short, long, native, no)
  -n WORKERS          Número de workers paralelos (por defecto: CPUs)
  --junitxml=RUTA     Generar reporte JUnit XML
  -s                  No capturar stdout/stderr
  --maxfail=N         Detener después de N fallos
  --version           Mostrar versión
  -h, --help          Mostrar ayuda
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

# Detener tras el primer fallo
oxytest -x

# Ejecutar tests que coincidan con una palabra clave
oxytest -k "user or auth"

# Generar reporte JUnit XML
oxytest --junitxml report.xml

# Combinar flags
oxytest -v -n 4 -x tests/
```

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
```

## Códigos de Salida

| Código | Significado |
|--------|-------------|
| 0 | Todos los tests pasaron |
| 1 | Algunos tests fallaron |
| 2 | Error de ejecución de tests |
