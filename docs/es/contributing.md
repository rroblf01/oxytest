# Contribuir

## Configuración de Desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/ricardoroble/oxytest
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
│       └── _fixtures.py    # Sistema de fixtures (tmp_path, capsys, etc.)
├── tests/                  # Suite de tests para oxytest
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
# Ejecutar tests de muestra
oxytest tests/sample_tests/ -v

# Ejecutar la suite de tests de oxytest
python -m pytest tests/

# Ejecutar tests de Rust
cargo test
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
