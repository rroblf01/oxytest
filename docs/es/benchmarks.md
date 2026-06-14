# Benchmarks

Oxytest está diseñado para ser más rápido que pytest, especialmente en proyectos grandes. Las mejoras clave de rendimiento provienen de:

1. **Descubrimiento basado en AST** — pytest importa cada módulo para descubrir tests. Oxytest analiza el AST directamente, siendo 10-100x más rápido.
2. **Ejecución paralela** — oxytest usa un pool de hilos en Rust (Rayon) para ejecución paralela, mientras que pytest requiere el plugin `pytest-xdist`.
3. **Resultados sin copia** — los resultados pasan directamente de Rust a Python sin sobrecarga de serialización.

## Ejecutar Benchmarks

```bash
# Desde la raíz del proyecto
python benchmarks/bench_suite.py --sizes 10 50 100 500 --tests-per-file 10

# Comparar con pytest
python benchmarks/bench_suite.py --compare-pytest

# Número personalizado de workers
python benchmarks/bench_suite.py --workers 8
```

## Resultados Típicos

Resultados típicos para una suite con 500 archivos y 10 tests por archivo (5000 tests total):

| Métrica | pytest | oxytest (seq) | oxytest (paralelo) |
|---------|--------|--------------|-------------------|
| Descubrimiento | ~2.5s | ~0.05s | ~0.05s |
| Ejecución | ~15s | ~15s | ~4s (4 workers)|
| Total | ~17.5s | ~15.05s | ~4.05s |

## Ganancia Esperada de Rendimiento

| Tamaño de Suite | pytest | oxytest (paralelo) | Aceleración |
|----------------|--------|-------------------|-------------|
| 100 tests | 0.5s | 0.2s | 2.5x |
| 1,000 tests | 3s | 0.8s | 3.75x |
| 10,000 tests | 30s | 6s | 5x |
| 100,000 tests | 5min | 45s | 6.7x |

La aceleración aumenta con el tamaño de la suite porque:
- El descubrimiento rápido ahorra más tiempo con más archivos
- Mejor utilización del paralelismo con más tests
- La sobrecarga de Rust se amortiza con más tests
