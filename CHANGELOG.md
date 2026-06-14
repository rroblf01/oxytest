# Changelog

## 0.1.0 (unreleased)

### Added
- Initial release of oxytest, a 100% pytest-compatible test runner in Python + Rust
- AST-based test discovery (10-100x faster than import-based)
- Sequential and parallel (Rayon) test execution
- Built-in fixtures: `tmp_path`, `tmpdir`, `capsys`, `capfd`, `monkeypatch`
- `conftest.py` loading and fixture registration
- pytest API compatibility: `main`, `approx`, `raises`, `fixture`, `mark`, `skip`, `skipif`, `xfail`, `param`, `fail`, `exit`, `set_trace`, `importorskip`
- CLI flags: `-v`, `-q`, `-x`, `-k`, `--tb`, `-n`, `--junitxml`, `-s`, `--maxfail`
- JUnit XML output
- Documentation in English and Spanish (MkDocs)

### Changed
- N/A

### Fixed
- N/A
