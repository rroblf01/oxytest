SHELL := /bin/bash
VENV := .venv
export PATH := $(VENV)/bin:$(PATH)
PYTHON := python
RUFF := ruff
TY := ty
CARGO := cargo
COVERAGE := coverage

.PHONY: all python-test rust-test test lint ty-check ruff-check clean help

all: lint
	@$(MAKE) --no-print-directory test

# ── Python ──────────────────────────────────────────────────────────

python-test:
	$(PYTHON) -m oxytest tests/ --tb=no

python-test-verbose:
	$(PYTHON) -m oxytest tests/ -v

python-test-fast:
	$(PYTHON) -m oxytest tests/ -q

python-coverage:
	$(COVERAGE) run -m oxytest tests/ --tb=no
	$(COVERAGE) report -m --include="python/oxytest/*" --sort=Cover

python-coverage-html:
	$(COVERAGE) run -m oxytest tests/ --tb=no
	$(COVERAGE) html --include="python/oxytest/*"
	@echo "Open htmlcov/index.html in your browser"

# ── Rust ────────────────────────────────────────────────────────────

rust-test:
	@printf "Rust tests: "
	@$(CARGO) test --lib 2>&1 | grep -oP 'test result: ok\. \d+ passed' | tr -d '\n'; echo

rust-bench:
	$(CARGO) bench

rust-build:
	$(CARGO) build --release

# ── Combined ────────────────────────────────────────────────────────

test:
	@echo "=============================="
	@echo " Python Tests"
	@echo "=============================="
	@$(MAKE) --no-print-directory python-test-soft
	@echo ""
	@echo "=============================="
	@echo " Rust Tests"
	@echo "=============================="
	@$(MAKE) --no-print-directory rust-test

test-verbose: python-test-verbose rust-test

python-test-soft:
	@printf "Python tests: "
	@$(PYTHON) -m oxytest tests/ --tb=no 2>&1 | tee /tmp/oxytest_out.txt | grep -oP 'Results: \d+ tests|  passed: \d+|  failed: \d+|  skipped: \d+' | tr '\n' ' '; echo
	@rm -f /tmp/oxytest_out.txt; true

# ── Lint ────────────────────────────────────────────────────────────

ruff-check:
	$(RUFF) check .

ruff-fix:
	$(RUFF) check --fix .

ty-check:
	$(TY) check python/oxytest/

lint: ruff-check ty-check

# ── Housekeeping ────────────────────────────────────────────────────

clean:
	$(CARGO) clean
	rm -rf htmlcov/ .coverage .coverage.*
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete

help:
	@echo "Available targets:"
	@echo "  all               - lint + test"
	@echo "  lint              - run ruff + ty (type check)"
	@echo "  test              - python (soft) + rust tests"
	@echo "  python-test       - run Python tests"
	@echo "  python-test-soft  - run Python tests (ignores exit code)"
	@echo "  rust-test         - run Rust unit tests"
	@echo "  python-coverage   - run with coverage report"
	@echo "  rust-bench        - run Rust benchmarks"
	@echo "  rust-build        - build Rust release"
	@echo "  ruff-check        - lint Python with ruff"
	@echo "  ty-check          - type check Python with ty"
	@echo "  clean             - remove build artifacts"
