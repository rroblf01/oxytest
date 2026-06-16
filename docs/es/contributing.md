# Contribuir

## Configuración de Desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/rroblf01/oxytest
cd oxytest

# Instalar dependencias
uv sync

# Construir la extensión Rust en modo desarrollo
uv pip install -e .

# Ejecutar tests
oxytest tests/
```

## Estructura del Proyecto

```
oxytest/
├── src/                    # Código fuente Rust
│   ├── lib.rs             # Punto de entrada del módulo PyO3
│   ├── types.rs           # Clases TestItem y TestResult
│   ├── discovery.rs       # Descubrimiento de tests basado en AST
│   └── runner.rs          # Ejecución de tests (secuencial + paralela)
├── python/
│   └── oxytest/
│       ├── __init__.py     # Exportaciones del paquete
│       ├── __main__.py     # Punto de entrada python -m oxytest
│       ├── _compat.py      # Capa de compatibilidad con API de pytest
│       ├── _core.pyi       # Type stubs para el módulo Rust
│       ├── _fixtures.py    # Sistema de fixtures (tmp_path, capsys, etc.)
│       ├── _plugin.py      # Sistema de plugins (hooks basados en pluggy)
│       ├── _assert.py      # Reescritura de asserts para diffs de comparación
│       └── _migrate.py     # Herramienta de migración de imports (pytest ↔ oxytest)
├── tests/                  # Suite de tests para oxytest
│   └── sample_tests/       # Tests de muestra para integración
├── docs/                   # Documentación
│   ├── en/                 # Documentación en inglés
│   └── es/                 # Documentación en español
├── benchmarks/             # Benchmarks de rendimiento
├── pyproject.toml          # Configuración del paquete Python
├── Cargo.toml              # Configuración del crate Rust
└── mkdocs.yml              # Configuración del sitio de documentación
```

## Construcción

La extensión Rust se construye automáticamente al instalar el paquete:

```bash
# Instalación de desarrollo
uv pip install -e .

# Instalación de producción
uv pip install .
```

Para compilar Rust manualmente:

```bash
cargo build --release
```

## Testing

```bash
# Ejecutar tests de muestra (30 tests, 9 fallos esperados)
oxytest tests/sample_tests/ -v

# Ejecutar la suite de tests de oxytest
uv run python -m oxytest tests/ -v --tb=no

# Ejecutar tests de Rust
cargo test

# Probar salida de fallos (9 tests, todos deben fallar)
oxytest tests/sample_tests/test_failures.py --tb=short
```

## Estilo de Código

- Python: seguir PEP 8
- Rust: seguir sugerencias de `cargo clippy`
- Mantener la capa de compatibilidad con pytest lo más delgada posible
- Preferir lógica en Rust para rutas críticas de rendimiento

## Proceso de Pull Request

1. Haz un fork del repositorio
2. Crea una rama de funcionalidad
3. Realiza tus cambios
4. Ejecuta la suite de tests
5. Envía un pull request

## Proceso de Release

1. Actualizar versión en `pyproject.toml` y `Cargo.toml`
2. Ejecutar suite completa de tests y benchmarks
3. Crear un tag firmado
4. Subir el tag para lanzar release a PyPI via GitHub Actions
