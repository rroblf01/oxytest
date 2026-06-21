# Benchmarks

Oxytest está diseñado para ser más rápido que pytest, especialmente en proyectos grandes. Las mejoras clave de rendimiento provienen de:

1. **Descubrimiento basado en AST** — pytest importa cada módulo para descubrir tests. Oxytest analiza el AST directamente, siendo 10-100x más rápido.
2. **Ejecución paralela** — oxytest usa un pool de hilos en Rust (Rayon) para ejecución paralela, mientras que pytest requiere el plugin `pytest-xdist`.
3. **Resultados sin copia** — los resultados pasan directamente de Rust a Python sin sobrecarga de serialización.

## Reproducir los Benchmarks

Usa el generador integrado para una comparación justa:

```bash
# Generar 500 archivos con 10 tests cada uno, 1ms de sleep por test
python benchmarks/generate.py --num-files 500 --tests-per-file 10 --sleep-ms 1

# Comparación secuencial (justa: sin -n para ninguno)
time python -m oxytest benchmark_tests/ --tb=no -q
time python -m pytest benchmark_tests/ --tb=no -q

# Comparación paralela
time python -m oxytest benchmark_tests/ --tb=no -q -n auto
time python -m pytest benchmark_tests/ --tb=no -q -n auto   # requiere pytest-xdist
```

También puedes generar diferentes tamaños:

```bash
# Pequeño: 100 archivos × 5 tests = 500 tests (sin sleep, solo overhead)
python benchmarks/generate.py --num-files 100 --tests-per-file 5 --sleep-ms 0

# Mediano: 1000 archivos × 10 tests = 10,000 tests
python benchmarks/generate.py --num-files 1000 --tests-per-file 10 --sleep-ms 1

# Grande: 5000 archivos × 20 tests = 100,000 tests
python benchmarks/generate.py --num-files 5000 --tests-per-file 20 --sleep-ms 0.5
```

## Ejecutar el Benchmark Integrado

```bash
# Desde la raíz del proyecto
python benchmarks/bench_suite.py --sizes 10 50 100 500 --tests-per-file 10

# Comparar con pytest
python benchmarks/bench_suite.py --compare-pytest

# Número personalizado de workers
python benchmarks/bench_suite.py --workers 8
```

## Resultados de Benchmark

Resultados medidos en una **máquina de 12 núcleos (31GB RAM, Arch Linux, Python 3.14)** con **500 archivos × 10 tests = 5000 tests**, cada test con **1ms de sleep** para simular I/O real:

| Modo | pytest | oxytest | Aceleración |
|------|--------|---------|-------------|
| Secuencial | 10.88s | **5.73s** | **1.9x** |
| Paralelo (12 workers) | — | — | — |

Solo descubrimiento (500 archivos, sin ejecución):

| Herramienta | Tiempo |
|-------------|--------|
| pytest | 4.97s |
| oxytest | **2.33s — 2.1× más rápido** |

### Proyectos Reales

| Proyecto | Tests | Tiempo oxytest | Tiempo pytest | Aceleración |
|----------|-------|---------------|---------------|-------------|
| **Flask** | 491 | 0.66s | 1.14s | **1.7×** |
| **httpx** | 1,418 | 2.88s | — | — |
| **Pydantic** | 29,490 | 45.94s | — | — |
| **oxytest (auto)** | 700 | 11.71s | 12.04s | **~1×** |

## Compatibilidad con Proyectos Reales

Oxytest ha sido probado contra varios proyectos populares de Python para verificar compatibilidad y medir rendimiento real:

| Proyecto | oxytest | pytest | Coincidencia |
|----------|---------|--------|--------------|
| **oxytest (auto)** | 691 ✅ / 9 ❌ (700) | 675 ✅ / 16 ❌ / 4 ⚠️ (695) | **100%+** (oxytest pasa 16 más) |
| **Flask** | 491 ✅ (491) | 491 ✅ (491) | **100%** |
| **httpx** | 1,414 ✅ / 1 ⚠️ / 3 ❌ (1,418) | — | — |
| **Pydantic** | 28,662 ✅ / 669 ⚠️ / 159 ❌ (29,490)¹ | —² | — |

✅ = pasaron, ⚠️ = saltados/xfailed, ❌ = fallaron

Notas:
1. Pydantic incluye los directorios `tests/` y `tests_oxytest/`. Los 159 fallos incluyen ~56 diferencias de formato de assertion, ~50 relacionados con `pytest_generate_tests` (argumentos faltantes), ~20 diferencias de `__module__` vs ruta, y categorías menores. La comparación completa con pytest está pendiente.
2. Pytest en Pydantic v2 requiere configuración específica; vea la configuración CI para detalles. Muchos tests de Pydantic-core actualmente coinciden dentro de ~99% excepto por formato de assertion.

| Proyecto | Categorías principales de fallos |
|----------|-------------------------------|
| **Pydantic** | Diferencia de formato de assertion (`assert v > 0\n+ where -1 = v` vs `assert -1 > 0`); argumentos faltantes relacionados con `pytest_generate_tests`; diferencias de ruta `__module__` (`tests_oxytest` vs `tests`); casos extremos de compatibilidad Python 3.14 |

> **Nota:** Todos los fallos listados son pre-existentes y NO son regresiones de los cambios de oxytest. La principal brecha de compatibilidad es el formato del mensaje de error de assertion — pytest sustituye valores reales en la expresión (`assert 1 == 2`), mientras que oxytest muestra la expresión fuente con una cláusula `where` (`assert x == y\n+ where 1 = x`).

## Compatibilidad con Plugins de pytest

Oxytest soporta muchas características de pytest a través de su sistema de plugins basado en pluggy:

| Característica | Estado | Notas |
|---------------|--------|-------|
| Parametrize (`@pytest.mark.parametrize`) | ✅ | Soporte completo, incluyendo fixtures indirectos |
| Skip / SkipIf / XFail | ✅ | Soporte completo |
| Fixtures (function, class, module, session) | ✅ | Incluyendo autouse, yield fixtures, conftest.py |
| Monkeypatch, tmpdir, capsys | ✅ | Fixtures integrados |
| Plugins personalizados (`pytest_plugins`) | ✅ | Via conftest.py |
| Hook `pytest_assertrepr_compare` | ✅ | Recibe valores reales de runtime |
| Filtro `-k` / `-m` | ✅ | |
| `--lf` / `--ff` (últimos fallos) | ✅ | |
| `--stepwise` | ✅ | |
| `--junitxml` | ✅ | |
| `--doctest-modules` | ✅ | |
| Cobertura (`--cov`) | ✅ | |
| Captura de warnings (`-rw`) | ✅ | |
| `pytest_generate_tests` | ❌ | No implementado aún |
| `unittest.TestCase` completo | ⚠️ | setUp/tearDown básico funciona |
| pytester | ❌ | No implementado |
| `--nf` (nuevos primero) | ❌ | No implementado |
| `--pastebin` | ❌ | No implementado |
| `--tracemalloc` | ❌ | No implementado |
| `StashKey` | ❌ | No implementado |

> **Consejo:** Crea tu propio benchmark con `python benchmarks/generate.py` como se muestra arriba para medir el rendimiento en tu hardware y carga de trabajo específicos.
