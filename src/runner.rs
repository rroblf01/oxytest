use crate::types::{TestItem, TestResult};
use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::HashMap;
use std::time::Instant;

fn run_single_test(py: Python<'_>, test: &TestItem, nocapture: bool) -> TestResult {
    let test_path = &test.path;
    let test_name = &test.name;
    let args_json = &test.args_json;

    let start = Instant::now();

    struct Capture<'a> {
        stdout: Bound<'a, PyAny>,
        stderr: Bound<'a, PyAny>,
        old_stdout: Option<Bound<'a, PyAny>>,
        old_stderr: Option<Bound<'a, PyAny>>,
    }

    let cap: Option<Capture<'_>> = if !nocapture {
        let sys = match py.import("sys") {
            Ok(s) => s,
            Err(e) => return fail_fast(test, 0, format!("Failed to import sys: {}", e)),
        };
        let io = match py.import("io") {
            Ok(i) => i,
            Err(e) => return fail_fast(test, 0, format!("Failed to import io: {}", e)),
        };

        let co = match io.call_method1("StringIO", ()) {
            Ok(c) => c,
            Err(e) => return fail_fast(test, 0, format!("Failed to create StringIO: {}", e)),
        };
        let ce = match io.call_method1("StringIO", ()) {
            Ok(c) => c,
            Err(e) => return fail_fast(test, 0, format!("Failed to create StringIO: {}", e)),
        };

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

    if let Some(ref cap) = cap {
        if let Some(ref old) = cap.old_stdout {
            let _ = py.import("sys").and_then(|s| s.setattr("stdout", old.clone()));
        }
        if let Some(ref old) = cap.old_stderr {
            let _ = py.import("sys").and_then(|s| s.setattr("stderr", old.clone()));
        }
    }

    let out: String = if let Some(ref cap) = cap {
        cap.stdout.call_method0("getvalue")
            .and_then(|v| v.extract::<String>())
            .unwrap_or_default()
    } else {
        String::new()
    };
    let err: String = if let Some(ref cap) = cap {
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
            let tb_str = py_err
                .traceback(py)
                .and_then(|tb| tb.format().ok())
                .unwrap_or_default();
            TestResult::failed(
                test.clone(), out, err, duration_ms,
                error_str, Some(tb_str),
            )
        }
    }
}

fn fail_fast(test: &TestItem, duration_ms: u64, error: String) -> TestResult {
    TestResult::failed(test.clone(), String::new(), String::new(), duration_ms, error, None)
}

fn group_tests_by_path(tests: Vec<TestItem>) -> HashMap<String, Vec<TestItem>> {
    let mut grouped: HashMap<String, Vec<TestItem>> = HashMap::new();
    for test in tests {
        grouped
            .entry(test.path.clone())
            .or_default()
            .push(test);
    }
    grouped
}

fn sort_results(results: &mut [TestResult]) {
    results.sort_by(|a, b| {
        a.test.path.cmp(&b.test.path)
            .then_with(|| a.test.line_no.cmp(&b.test.line_no))
    });
}

#[pyfunction]
#[pyo3(signature = (tests, num_workers=None, nocapture=false))]
pub fn run_tests(py: Python<'_>, tests: Vec<TestItem>, num_workers: Option<usize>, nocapture: bool) -> PyResult<Vec<TestResult>> {
    let _ = num_workers;
    let grouped = group_tests_by_path(tests);

    let results = Mutex::new(Vec::new());
    let groups: Vec<_> = grouped.into_iter().collect();

    py.detach(|| {
        groups.par_iter().for_each(|(_path, file_tests)| {
            Python::attach(|py| {
                let mut file_results: Vec<TestResult> = Vec::with_capacity(file_tests.len());
                for test in file_tests {
                    file_results.push(run_single_test(py, test, nocapture));
                }
                results.lock().unwrap().extend(file_results);
            });
        });
    });

    let mut final_results = results.into_inner().unwrap();
    sort_results(&mut final_results);
    Ok(final_results)
}

#[pyfunction]
#[pyo3(signature = (tests, nocapture=false))]
pub fn run_tests_sequential(py: Python<'_>, tests: Vec<TestItem>, nocapture: bool) -> PyResult<Vec<TestResult>> {
    let grouped = group_tests_by_path(tests);

    let mut results = Vec::new();
    for (_path, file_tests) in grouped {
        for test in &file_tests {
            results.push(run_single_test(py, test, nocapture));
        }
    }

    sort_results(&mut results);
    Ok(results)
}

use std::sync::Mutex;

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test(path: &str, name: &str, line: u32) -> TestItem {
        TestItem::new_no_args(path.into(), name.into(), line)
    }

    #[test]
    fn test_group_tests_by_path_single() {
        let tests = vec![make_test("a.py", "test_a", 1)];
        let grouped = group_tests_by_path(tests);
        assert_eq!(grouped.len(), 1);
        assert_eq!(grouped["a.py"].len(), 1);
    }

    #[test]
    fn test_group_tests_by_path_multiple() {
        let tests = vec![
            make_test("a.py", "test_a1", 1),
            make_test("a.py", "test_a2", 2),
            make_test("b.py", "test_b", 1),
        ];
        let grouped = group_tests_by_path(tests);
        assert_eq!(grouped.len(), 2);
        assert_eq!(grouped["a.py"].len(), 2);
        assert_eq!(grouped["b.py"].len(), 1);
    }

    #[test]
    fn test_group_tests_by_path_empty() {
        let grouped = group_tests_by_path(vec![]);
        assert!(grouped.is_empty());
    }

    #[test]
    fn test_sort_results_by_path_then_line() {
        let mut results = vec![
            TestResult::passed(make_test("b.py", "test_b", 10), String::new(), String::new(), 0),
            TestResult::passed(make_test("a.py", "test_a", 5), String::new(), String::new(), 0),
            TestResult::passed(make_test("a.py", "test_a", 3), String::new(), String::new(), 0),
        ];
        sort_results(&mut results);
        assert_eq!(results[0].test.path, "a.py");
        assert_eq!(results[0].test.line_no, 3);
        assert_eq!(results[1].test.line_no, 5);
        assert_eq!(results[2].test.path, "b.py");
    }

    #[test]
    fn test_sort_results_empty() {
        let mut results: Vec<TestResult> = vec![];
        sort_results(&mut results);
        assert!(results.is_empty());
    }

    #[test]
    fn test_fail_fast() {
        let test = make_test("t.py", "test_err", 1);
        let result = fail_fast(&test, 0, "IO error".into());
        assert!(!result.passed);
        assert_eq!(result.error.unwrap(), "IO error");
    }
}
