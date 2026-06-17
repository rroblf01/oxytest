# Changelog

## [3.0.0] — 2026-06-17

### Added

#### CLI flags
- `--no-header` — suppress the "oxytest: running tests" banner
- `--capture=<method>` — set capture method (`fd`, `sys`, `tee-sys`, `tee-fd`, `no`)
- `--show-capture` — control which output to show on failures
- `--deselect` — exclude specific tests
- `-W` / `--pythonwarnings` — set warning filters from CLI
- `--import-mode` — control `sys.path` behavior (`prepend`, `append`, `importlib`)
- `--ignore-glob` — ignore test files matching glob patterns
- `--continue-on-collection-errors` — don't abort on collection errors
- `--log-level`, `--log-format`, `--log-cli-level` — logging configuration
- `--color` — force color output (`yes`, `no`, `auto`)
- `--code-highlight` — enable code highlighting in tracebacks
- `--stepwise-skip` — skip the first failure in stepwise mode
- `--full-trace` — show full tracebacks (no truncation)
- `--setup-only`, `--setup-plan` — trace fixture setup without running tests
- `--verbosity` counter (`-vvv`) — fine-grained verbosity

#### Fixtures (built-in)
- `recwarn` — warning recording fixture (`list`, `pop`, `clear`)
- `capsysbinary` — binary stdout/stderr capture
- `capfdbinary` — binary FD-level capture
- `doctest_namespace` — namespace dict for doctests
- `tmp_path_factory` — session-scoped temporary directory factory

#### Plugin hooks
- `pytest_collect_module` — customize test module collection
- `pytest_make_parametrize_id` — generate parametrize IDs
- `pytest_runtest_makereport` — create test reports
- `pytest_report_header` — add lines to terminal header
- `pytest_report_teststatus` — customize short status labels
- `pytest_exception_interact` — handle exceptions interactively
- `pytest_enter_pdb`, `pytest_leave_pdb` — pdb lifecycle hooks

#### Warning hierarchy
- `PytestRemovedIn10Warning`, `PytestExperimentalApiWarning`,
  `PytestAssertRewriteWarning`, `PytestCacheWarning`, `PytestConfigWarning`,
  `PytestCollectionWarning`, `PytestReturnNotNoneWarning`,
  `PytestUnknownMarkWarning`, `PytestUnraisableExceptionWarning`,
  `PytestUnhandledThreadExceptionWarning`, `PytestFDWarning`

#### API
- `MonkeyPatch.context()` — context manager classmethod
- `Config.rootpath` — `pathlib.Path` version of `rootdir`
- `Config.hook` — access to plugin hook system
- `Config.cache` — access to cache fixture
- `ExceptionInfo.type` — exception type from `pytest.raises`
- `pytest.approx` now supports `nan_ok=True`, `Decimal`, `datetime`, `Timedelta`
- `pytest.warns` accepts `re.Pattern` as `match` argument
- `pytest.raises` `.type` property

#### Compatibility
- `pytest_plugins` variable in conftest.py now loads plugins
- `record_property` fixture data emitted in JUnit XML output
- `pytest_terminal_summary` hook called before session finish

### Fixed
- `--trace`: now enters pdb before each test (previously only set env var)
- `--runxfail`: now replaces `pytest.xfail` with no-op (like pytest does)
- `--override-ini`: KEY=VALUE format properly applied to `Config._inicfg`
- `--confcutdir`: now limits conftest.py search to specified directory
- `--strict-config`: option is now properly consumed
- `--import-mode`: now affects `sys.path.insert` vs `append` behavior
- `--capture=no`: now properly sets `nocapture=True`
- `MonkeyPatch.setattr`: descriptor handling via `target.__dict__`
- `_SubTestFixture.__exit__`: catches only `AssertionError` (not all `Exception`)
- `ExitCode` values: renumbered to match pytest exactly

### Performance
- `inspect.signature()` cached per function via `__signature__`
- Module-level imports hoisted out of hot function body
- `_import_lock` conditional — only acquired on cache miss
- `os.path.relpath()` results cached per filepath
- `setrecursionlimit` conditional — only set if not already at target
- Autouse fixture list cached — avoids full fixture scan per test
- Thread-local `FixtureManager` and `_conftest_seen` for safe parallel execution
- `is_test_file()` fixed to reject non-`.py` files

### Removed
- `_NOT_SET` sentinel (replaced by `MonkeyPatch._UNSET`)

## [2.0.0] — 2026-06-07

### Added
- `caplog` fixture with `records`, `text`, `messages`, `record_tuples`
- `pytest.mark.filterwarnings` support with `action:message:category` format
- `pytest.ini` / `setup.cfg` / `tox.ini` parsing
- `--override-ini`, `--confcutdir`, `--basetemp` CLI flags
- `--collect-only` / `--co` support
- `record_property`, `record_xml_attribute`, `record_testsuite_property`, `cache` fixtures
- `pytest_runtest_setup`, `pytest_runtest_teardown`, `pytest_runtest_protocol` hooks
- Import-time assertion rewriting via `_RewriteLoader`
- `register_assert_rewrite()` public API
- Multiprocessing worker pool for parallel execution (`-n` flag)

### Fixed
- `func.pytestmark` detection for `@pytest.mark.parametrize` from real pytest
- Kwargs-style `@pytest.mark.parametrize(argnames=..., argvalues=...)`
- Phase 2 transitive fixture dependency resolution
- `ParameterSet` unwrap for IDs and values
- Session-scoped generator preservation across function cleanup
- `MonkeyPatch.setattr` pytest semantics for dotted strings
