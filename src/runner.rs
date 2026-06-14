use crate::types::{TestItem, TestResult};
use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Instant;

fn ensure_sys_path(py: Python<'_>, dirpath: &str) -> PyResult<()> {
    let sys = py.import("sys")?;
    let path = sys.getattr("path")?;
    let dir = dirpath.to_string();
    let contains: bool = path.call_method1("__contains__", (dir,))?.extract()?;
    if !contains {
        path.call_method1("insert", (0, dirpath.to_string()))?;
    }
    Ok(())
}

fn import_test_module<'py>(py: Python<'py>, test_path: &str) -> PyResult<Bound<'py, PyModule>> {
    let dir = std::path::Path::new(test_path)
        .parent()
        .unwrap_or(std::path::Path::new("."))
        .to_string_lossy()
        .to_string();
    ensure_sys_path(py, &dir)?;

    let module_name = test_path
        .replace('/', ".")
        .replace('\\', ".")
        .trim_end_matches(".py")
        .to_string();
    let module_name = module_name.trim_start_matches('.').to_string();

    let sys = py.import("sys")?;
    let modules = sys.getattr("modules")?;
    if let Ok(m) = modules.get_item(&module_name) {
        if let Ok(pymod) = m.cast::<PyModule>() {
            return Ok(pymod.clone());
        }
    }

    let importlib = py.import("importlib.util")?;
    let spec = importlib.call_method1(
        "spec_from_file_location",
        (module_name.clone(), test_path.to_string()),
    )?;

    if spec.is_none() {
        return Err(PyErr::new::<pyo3::exceptions::PyImportError, _>(format!(
            "Could not find module spec for {}",
            test_path
        )));
    }

    let module = importlib.call_method1("module_from_spec", (spec.clone(),))?;
    modules.set_item(&module_name, module.clone())?;

    let loader = spec.getattr("loader")?;
    loader.call_method1("exec_module", (module,))?;

    let sys = py.import("sys")?;
    let modules = sys.getattr("modules")?;
    if let Ok(m) = modules.get_item(&module_name) {
        if let Ok(pymod) = m.cast::<PyModule>() {
            return Ok(pymod.clone());
        }
    }

    Err(PyErr::new::<pyo3::exceptions::PyImportError, _>(format!(
        "Module {} not found after import",
        module_name
    )))
}

fn run_single_test(py: Python<'_>, test: &TestItem) -> TestResult {
    let io = match py.import("io") {
        Ok(i) => i,
        Err(e) => {
            return TestResult::failed(
                test.clone(),
                String::new(),
                String::new(),
                0,
                format!("Failed to import io: {}", e),
                None,
            );
        }
    };

    let captured_out = match io.call_method1("StringIO", ()) {
        Ok(c) => c,
        Err(e) => {
            return TestResult::failed(
                test.clone(),
                String::new(),
                String::new(),
                0,
                format!("Failed to create StringIO: {}", e),
                None,
            );
        }
    };
    let captured_err = match io.call_method1("StringIO", ()) {
        Ok(c) => c,
        Err(e) => {
            return TestResult::failed(
                test.clone(),
                String::new(),
                String::new(),
                0,
                format!("Failed to create StringIO: {}", e),
                None,
            );
        }
    };

    let test_path = test.path.clone();
    let test_name = test.name.clone();

    let start = Instant::now();

    let result = (|| -> PyResult<()> {
        let module = import_test_module(py, &test_path)?;

        if test_name.contains("::") {
            let parts: Vec<&str> = test_name.split("::").collect();
            let cls = module.getattr(parts[0])?;
            let instance = cls.call0()?;
            let method = instance.getattr(parts[1])?;
            method.call0()?;
        } else {
            let func = module.getattr(&test_name)?;
            func.call0()?;
        }

        Ok(())
    })();

    let duration = start.elapsed();

    let out: String = captured_out
        .call_method0("getvalue")
        .and_then(|v| v.extract::<String>())
        .unwrap_or_default();
    let err: String = captured_err
        .call_method0("getvalue")
        .and_then(|v| v.extract::<String>())
        .unwrap_or_default();

    let duration_ms = duration.as_millis() as u64;

    match result {
        Ok(()) => TestResult::passed(test.clone(), out, err, duration_ms),
        Err(py_err) => {
            let error_str = py_err.to_string();
            let traceback_str = py
                .import("traceback")
                .and_then(|tb| tb.call_method1("format_exc", ()))
                .and_then(|v| v.extract::<String>())
                .unwrap_or_default();
            TestResult::failed(
                test.clone(),
                out,
                err,
                duration_ms,
                error_str,
                Some(traceback_str),
            )
        }
    }
}

#[pyfunction]
#[pyo3(signature = (tests, num_workers=None))]
pub fn run_tests(py: Python<'_>, tests: Vec<TestItem>, num_workers: Option<usize>) -> PyResult<Vec<TestResult>> {
    let workers = num_workers.unwrap_or_else(|| {
        std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(4)
    });

    let mut grouped: HashMap<String, Vec<TestItem>> = HashMap::new();
    for test in tests {
        grouped
            .entry(test.path.clone())
            .or_default()
            .push(test);
    }

    let results = Mutex::new(Vec::new());

    py.detach(|| {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(workers)
            .build()
            .unwrap();

        let groups: Vec<_> = grouped.into_iter().collect();

        pool.install(|| {
            groups.par_iter().for_each(|(_path, file_tests)| {
                Python::attach(|py| {
                    let mut file_results: Vec<TestResult> = Vec::new();
                    for test in file_tests {
                        file_results.push(run_single_test(py, test));
                    }
                    results.lock().unwrap().extend(file_results);
                });
            });
        });
    });

    let mut final_results = results.into_inner().unwrap();
    final_results.sort_by(|a, b| {
        a.test
            .path
            .cmp(&b.test.path)
            .then_with(|| a.test.line_no.cmp(&b.test.line_no))
    });
    Ok(final_results)
}

#[pyfunction]
pub fn run_tests_sequential(py: Python<'_>, tests: Vec<TestItem>) -> PyResult<Vec<TestResult>> {
    let mut grouped: HashMap<String, Vec<TestItem>> = HashMap::new();
    for test in tests {
        grouped
            .entry(test.path.clone())
            .or_default()
            .push(test);
    }

    let mut results = Vec::new();
    for (_path, file_tests) in grouped {
        for test in &file_tests {
            results.push(run_single_test(py, test));
        }
    }

    results.sort_by(|a, b| {
        a.test
            .path
            .cmp(&b.test.path)
            .then_with(|| a.test.line_no.cmp(&b.test.line_no))
    });
    Ok(results)
}
