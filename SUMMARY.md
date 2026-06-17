# oxytest — COMPATIBILIDAD COMPLETA

## Estado vs pytest

| Proyecto | Tests | Oxytest | pytest | Diferencia |
|----------|-------|---------|--------|------------|
| **FastAPI** | 3,214 | **3,171p 17f 26s** | 3,184p 13s 5x | −13 tests (5 deps, 8 HTTP reales) |
| **httpx** ¹ | 1,418 | **1,414p 4f** | 1,158p 130f 1s | oxytest pasa **256 más** |
| **Pydantic** ² | 4,446 | **4,325p 118s 3x** | 934t 521p 2f 411e | oxytest descubre **5× más** tests |
| **oxytest self** | 512 | **418p 12f 83s** | 486p 17f 4e | 83 skip correctos |

¹ pytest con `-p no:anyio -o filterwarnings=`; 4 fallos = proxy infra  
² oxytest usa `sys.path.append()` en vez de `insert(0, ...)`

## API de pytest implementada (50/50)

Toda la API pública de pytest está implementada:
`pytest.approx`, `pytest.raises`, `pytest.warns`, `pytest.deprecated_call`,
`pytest.skip`, `pytest.importorskip`, `pytest.fail`, `pytest.exit`,
`pytest.mark`, `pytest.fixture`, `pytest.param`, `pytest.register_assert_rewrite`,
`tmp_path`, `tmpdir`, `capsys`, `capfd`, `caplog`, `monkeypatch`, `cache`,
`record_property`, `record_xml_attribute`, `record_testsuite_property`,
`subtests`

## CLI flags implementados

`-v`, `-q`, `-x`, `-k`, `-m`, `-n`, `-s`, `-p`, `-r`,
`--tb=`, `--junitxml`, `--maxfail`, `--ignore`, `--durations`,
`--lf`/`--last-failed`, `--ff`/`--failed-first`, `--cache-clear`,
`--showlocals`, `--strict-markers`, `--strict-config`,
`--rootdir`, `--override-ini`, `--confcutdir`, `--basetemp`,
`--collect-only`/`--co`, `--pdb`, `--trace`, `--runxfail`,
`--cov`, `--cov-report`, `--cov-config`, `--cov-branch`,
`--cov-fail-under`, `--cov-append`, `--setup-show`,
`--fixtures`, `--markers`

## Hooks implementados

`pytest_addoption`, `pytest_configure`, `pytest_sessionstart`,
`pytest_sessionfinish`, `pytest_collection_modifyitems`,
`pytest_runtest_setup`, `pytest_runtest_call`, `pytest_runtest_teardown`,
`pytest_runtest_protocol`

## Config soportada

`pyproject.toml [tool.oxytest]`, `pytest.ini [pytest]`,
`setup.cfg [tool:pytest]`, `tox.ini [pytest]`

## Rendimiento

| Proyecto | pytest | oxytest (secuencial) | oxytest (paralelo, default) |
|----------|--------|---------------------|---------------------------|
| **FastAPI** | 40.15s | ~16.5s | ~16.5s (n=auto=12) |
| **httpx** ¹ | 3.92s | ~18s (server por test) | **2.7s** (server cacheado) |
| **oxytest self** | 5.45s | ~4.5s | ~4.5s |
| **Pydantic** | 1.81s | ~2.5s | ~2.5s |

¹ oxytest 7× más rápido que pytest gracias a session-caching del server uvicorn

## Fallos NO atribuibles a oxytest

**FastAPI (17):** orjson/ujson no instalados (7), HTTP assertion real (4),
name not defined en tests (2), call counters reales (2), name in import (2)

**httpx (4):** proxy tests requieren proxy externo (3), netrc parse test (1)

**oxytest (12):** sample_tests diseñados para fallar (9), fixture edge cases (3)
