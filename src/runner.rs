use crate::types::{TestItem, TestResult};
use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::Instant;

fn run_single_test(py: Python<'_>, test: &TestItem, nocapture: bool) -> TestResult {
    let test_path = test.path.clone();
    let test_name = test.name.clone();
    let args_json = test.args_json.clone();

    let start = Instant::now();

    struct Capture<'a> {
        stdout: Bound<'a, PyAny>,
        stderr: Bound<'a, PyAny>,
        old_stdout: Option<Bound<'a, PyAny>>,
        old_stderr: Option<Bound<'a, PyAny>>,
    }

    let capture: Option<Capture<'_>> = if !nocapture {
        let sys = match py.import("sys") {
            Ok(s) => s,
            Err(e) => return TestResult::failed(
                test.clone(), String::new(), String::new(), 0,
                format!("Failed to import sys: {}", e), None,
            ),
        };
        let io = match py.import("io") {
            Ok(i) => i,
            Err(e) => return TestResult::failed(
                test.clone(), String::new(), String::new(), 0,
                format!("Failed to import io: {}", e), None,
            ),
        };

        let co = match io.call_method1("StringIO", ()) { Ok(c) => c, Err(e) => return TestResult::failed(
            test.clone(), String::new(), String::new(), 0,
            format!("Failed to create StringIO: {}", e), None,
        )};
        let ce = match io.call_method1("StringIO", ()) { Ok(c) => c, Err(e) => return TestResult::failed(
            test.clone(), String::new(), String::new(), 0,
            format!("Failed to create StringIO: {}", e), None,
        )};

        let old_out = sys.getattr("stdout").ok();
        let old_err = sys.getattr("stderr").ok();
        let _ = sys.setattr("stdout", co.clone());
        let _ = sys.setattr("stderr", ce.clone());

        Some(Capture { stdout: co, stderr: ce, old_stdout: old_out, old_stderr: old_err })
    } else {
        None
    };

    let result = (|| -> PyResult<()> {
        let compat = py.import("oxytest._compat")?;
        let execute = compat.getattr("_execute_test")?;
        execute.call1((test_path, test_name, args_json))?;
        Ok(())
    })();

    let duration = start.elapsed();

    if let Some(ref cap) = capture {
        if let Some(ref old) = cap.old_stdout {
            let _ = py.import("sys").and_then(|s| s.setattr("stdout", old.clone()));
        }
        if let Some(ref old) = cap.old_stderr {
            let _ = py.import("sys").and_then(|s| s.setattr("stderr", old.clone()));
        }
    }

    let out: String = if let Some(ref cap) = capture {
        cap.stdout.call_method0("getvalue")
            .and_then(|v| v.extract::<String>())
            .unwrap_or_default()
    } else {
        String::new()
    };
    let err: String = if let Some(ref cap) = capture {
        cap.stderr.call_method0("getvalue")
            .and_then(|v| v.extract::<String>())
            .unwrap_or_default()
    } else {
        String::new()
    };

    let duration_ms = duration.as_millis() as u64;

    match result {
        Ok(()) => TestResult::passed(test.clone(), out, err, duration_ms),
        Err(py_err) => {
            let error_str = py_err.to_string();
            let traceback_str = py_err
                .traceback(py)
                .and_then(|tb| tb.format().ok())
                .unwrap_or_default();
            TestResult::failed(
                test.clone(), out, err, duration_ms,
                error_str, Some(traceback_str),
            )
        }
    }
}

#[pyfunction]
#[pyo3(signature = (tests, num_workers=None, nocapture=false))]
pub fn run_tests(py: Python<'_>, tests: Vec<TestItem>, num_workers: Option<usize>, nocapture: bool) -> PyResult<Vec<TestResult>> {
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
                        file_results.push(run_single_test(py, test, nocapture));
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
#[pyo3(signature = (tests, nocapture=false))]
pub fn run_tests_sequential(py: Python<'_>, tests: Vec<TestItem>, nocapture: bool) -> PyResult<Vec<TestResult>> {
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
            results.push(run_single_test(py, test, nocapture));
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
