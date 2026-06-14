# Oxytest

**Oxytest** es un ejecutor de tests 100% compatible con pytest, escrito en Python y Rust mediante PyO3 y Maturin. Está diseñado para ser más rápido que pytest en proyectos grandes gracias a:

- **Descubrimiento de tests basado en AST** — encuentra tests sin importar módulos (10-100x más rápido)
- **Ejecución paralela** — ejecuta tests concurrentemente usando un pool de hilos en Rust (Rayon)
- **Ejecución en el mismo proceso** — sobrecarga mínima, sin crear subprocesos

## ¿Por qué Oxytest?

Si tienes una suite de tests grande y pytest se está volviendo lento, oxytest ofrece:

| Característica | Oxytest | pytest |
|----------------|---------|--------|
| Método de descubrimiento | AST (sin imports) | Basado en imports |
| Ejecución paralela | Integrada (Rayon) | Mediante plugin `pytest-xdist` |
| Lenguaje | Python + Rust | Python |
| Compatibilidad | 100% API compatible | — |

## Inicio Rápido

```bash
# Instalar oxytest
pip install oxytest

# Ejecutar tus tests existentes (¡sin cambios!)
oxytest

# O usar como reemplazo directo de pytest
python -c "import oxytest as pytest; pytest.main()"
```

## Estado del Proyecto

Oxytest está en desarrollo activo. El MVP es funcional con:

- ✅ Descubrimiento de tests (basado en AST)
- ✅ Ejecución de tests (secuencial y paralela)
- ✅ API compatible con pytest (`main`, `approx`, `raises`, `fixture`, `mark`, etc.)
- ✅ CLI con flags comunes (`-v`, `-x`, `-k`, `--tb`, `-n`, etc.)
- ✅ Salida JUnit XML
- ✅ Fixtures (`tmp_path`, `capsys`, `monkeypatch` + `conftest.py`)
- ❌ Plugins (próximamente)
