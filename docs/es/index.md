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

## Características

- ✅ Descubrimiento de tests basado en AST (10-100x más rápido que pytest)
- ✅ Ejecución secuencial y paralela (Rayon integrado)
- ✅ API compatible con pytest (`main`, `approx`, `raises`, `fixture`, `mark`, etc.)
- ✅ Fixtures (`tmp_path`, `capsys`, `monkeypatch`, `capfd` + `conftest.py`)
- ✅ Yield fixtures con teardown automático
- ✅ Fixtures `autouse=True`
- ✅ Marcador `usefixtures` en clases
- ✅ Salida JUnit XML con `<system-out>`, `<system-err>`, `timestamp`
- ✅ Reescritura de asserts con diffs de comparación
- ✅ `--showlocals` — muestra variables locales al fallar
- ✅ `--setup-show` — traza setup/teardown de fixtures
- ✅ Sistema de plugins (basado en pluggy, soporta `pytest_addoption`, `pytest_configure`, conftest, entry points)
- ✅ Herramienta de migración (`oxytest migrate`) — migración automática de imports entre pytest y oxytest
- ✅ Sistema de caché (`--lf`/`--last-failed`, `--ff`/`--failed-first`, `--cache-clear`)
- ✅ Expresiones de palabras clave (`-k "not slow and (math or api)"`)
- ✅ Cobertura de código integrada (`--cov`, `--cov-report`, `--cov-branch`, `--cov-fail-under`)
- ✅ Depurador post-mortem (`--pdb`) y ejecución traza (`--trace`)
- ✅ Integración con VSCode (JSON-RPC 2.0 sobre pipe nominal, auto-detectado)
- ✅ Configuración via `pyproject.toml` (sección `[tool.oxytest]`)
- ✅ Flags CLI: `-v`, `-q`, `-x`, `-k`, `--tb`, `-n`, `--junitxml`, `-s`, `--maxfail`, `--ignore`, `--collect-only`, `--durations`, `-r`, `--showlocals`, `--strict-markers`, `--rootdir`, `--fixtures`, `--markers`, `--setup-show`, `--cache-clear`, `--lf`, `--ff`, `-p`, `--cov`, `--cov-report`, `--cov-branch`, `--cov-fail-under`, `--cov-append`, `--pdb`, `--trace`
