# Contributing

## Development Setup

```bash
# Clone the repository
git clone https://github.com/rroblf01/oxytest
cd oxytest

# Install dependencies
uv sync

# Build the Rust extension in development mode
uv pip install -e .

# Run tests
oxytest tests/
```

## Project Structure

```
oxytest/
├── src/                    # Rust source code
│   ├── lib.rs             # PyO3 module entry point
│   ├── types.rs           # TestItem and TestResult classes
│   ├── discovery.rs       # AST-based test discovery
│   └── runner.rs          # Test execution (sequential + parallel)
├── python/
│   └── oxytest/
│       ├── __init__.py     # Package exports
│       ├── __main__.py     # python -m oxytest entry point
│       ├── _compat.py      # pytest API compatibility layer
│       ├── _core.pyi       # Type stubs for Rust module
│       └── _fixtures.py    # Fixture system (tmp_path, capsys, etc.)
├── tests/                  # Test suite for oxytest itself
├── docs/                   # Documentation
│   ├── en/                 # English documentation
│   └── es/                 # Spanish documentation
├── benchmarks/             # Performance benchmarks
├── pyproject.toml          # Python package configuration
├── Cargo.toml              # Rust crate configuration
└── mkdocs.yml              # Documentation site configuration
```

## Building

The Rust extension is built automatically when installing the package:

```bash
# Development install
uv pip install -e .

# Production build
uv pip install .
```

To run the Rust build manually:

```bash
cargo build --release
```

## Testing

```bash
# Run sample tests
oxytest tests/sample_tests/ -v

# Run oxytest's own test suite
python -m pytest tests/

# Run Rust tests
cargo test
```

## Code Style

- Python: follow PEP 8
- Rust: follow `cargo clippy` suggestions
- Keep the pytest API compatibility layer as thin as possible
- Prefer pushing logic into Rust for performance-critical paths

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## Release Process

1. Update version in `pyproject.toml` and `Cargo.toml`
2. Run full test suite and benchmarks
3. Create a signed tag
4. Push tag to trigger PyPI release via GitHub Actions
