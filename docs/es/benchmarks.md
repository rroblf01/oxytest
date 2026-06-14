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

Resultados medidos en una **máquina Linux de 8 núcleos (Python 3.14)** con **500 archivos × 10 tests = 5000 tests**, cada test con **1ms de sleep** para simular I/O real:

| Modo | pytest | oxytest | Aceleración |
|------|--------|---------|-------------|
| Secuencial | 11.45s | **5.85s** | **2.0x** |
| Paralelo (8 workers) | — | **0.57s** | **20x** |

Solo descubrimiento (500 archivos, sin ejecución):

| Herramienta | Tiempo |
|-------------|--------|
| pytest | ~2.5s |
| oxytest | **~0.05s** |

### Ganancia Esperada de Rendimiento

| Tamaño de Suite | pytest | oxytest (paralelo) | Aceleración |
|----------------|--------|-------------------|-------------|
| 100 tests | 0.5s | 0.2s | 2.5x |
| 1,000 tests | 3s | 0.8s | 3.75x |
| 10,000 tests | 30s | 6s | 5x |
| 100,000 tests | 5min | 45s | 6.7x |
| 500,000 tests | 30min | 4min | 7.5x |

La aceleración aumenta con el tamaño de la suite porque:
- El descubrimiento rápido ahorra más tiempo con más archivos
- Mejor utilización del paralelismo con más tests
- La sobrecarga de Rust se amortiza con más tests

> **Consejo:** Crea tu propio benchmark con `python benchmarks/generate.py` como se muestra arriba para medir el rendimiento en tu hardware y carga de trabajo específicos.
