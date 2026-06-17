use pyo3::prelude::*;

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct TestItem {
    #[pyo3(get, set)]
    pub path: String,
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub line_no: u32,
    #[pyo3(get, set)]
    pub args_json: String,
}

#[pymethods]
impl TestItem {
    #[new]
    fn py_new() -> Self {
        TestItem {
            path: String::new(),
            name: String::new(),
            line_no: 0,
            args_json: String::new(),
        }
    }

    fn __repr__(&self) -> String {
        if self.args_json.is_empty() {
            format!("TestItem({}:{}: {})", self.path, self.line_no, self.name)
        } else {
            format!("TestItem({}:{}: {} [args={}])", self.path, self.line_no, self.name, self.args_json)
        }
    }
}

impl TestItem {
    pub fn new_no_args(path: String, name: String, line_no: u32) -> Self {
        TestItem { path, name, line_no, args_json: String::new() }
    }
}

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct TestResult {
    #[pyo3(get)]
    pub test: TestItem,
    #[pyo3(get)]
    pub passed: bool,
    #[pyo3(get)]
    pub output: String,
    #[pyo3(get)]
    pub error_output: String,
    #[pyo3(get)]
    pub duration_ms: u64,
    #[pyo3(get)]
    pub error: Option<String>,
    #[pyo3(get)]
    pub traceback: Option<String>,
}

#[pymethods]
impl TestResult {
    fn __repr__(&self) -> String {
        let status = if self.passed { "PASSED" } else { "FAILED" };
        format!(
            "TestResult({} {} in {}ms)",
            status, self.test.name, self.duration_ms
        )
    }
}

#[pyfunction]
pub fn test_result_passed(test: TestItem, output: String, error_output: String, duration_ms: u64) -> TestResult {
    TestResult {
        test,
        passed: true,
        output,
        error_output,
        duration_ms,
        error: None,
        traceback: None,
    }
}

#[pyfunction]
pub fn test_result_failed(
    test: TestItem,
    output: String,
    error_output: String,
    duration_ms: u64,
    error: String,
    traceback: Option<String>,
) -> TestResult {
    TestResult {
        test,
        passed: false,
        output,
        error_output,
        duration_ms,
        error: Some(error),
        traceback,
    }
}

impl TestResult {
    pub fn passed(test: TestItem, output: String, error_output: String, duration_ms: u64) -> Self {
        TestResult {
            test,
            passed: true,
            output,
            error_output,
            duration_ms,
            error: None,
            traceback: None,
        }
    }

    pub fn failed(
        test: TestItem,
        output: String,
        error_output: String,
        duration_ms: u64,
        error: String,
        traceback: Option<String>,
    ) -> Self {
        TestResult {
            test,
            passed: false,
            output,
            error_output,
            duration_ms,
            error: Some(error),
            traceback,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_test_item_new_no_args() {
        let item = TestItem::new_no_args(
            "/path/to/test.py".into(),
            "test_foo".into(),
            42,
        );
        assert_eq!(item.path, "/path/to/test.py");
        assert_eq!(item.name, "test_foo");
        assert_eq!(item.line_no, 42);
        assert!(item.args_json.is_empty());
    }

    #[test]
    fn test_test_item_py_new() {
        let item = TestItem::py_new();
        assert!(item.path.is_empty());
        assert!(item.name.is_empty());
        assert_eq!(item.line_no, 0);
        assert!(item.args_json.is_empty());
    }

    #[test]
    fn test_test_item_repr_no_args() {
        let item = TestItem::new_no_args("t.py".into(), "test_a".into(), 10);
        let repr = item.__repr__();
        assert!(repr.contains("t.py"));
        assert!(repr.contains("test_a"));
        assert!(repr.contains("10"));
        assert!(!repr.contains("args"));
    }

    #[test]
    fn test_test_item_repr_with_args() {
        let item = TestItem {
            path: "t.py".into(),
            name: "test_b".into(),
            line_no: 5,
            args_json: "[1, 2]".into(),
        };
        let repr = item.__repr__();
        assert!(repr.contains("args"));
        assert!(repr.contains("[1, 2]"));
    }

    #[test]
    fn test_test_result_passed() {
        let test = TestItem::new_no_args("t.py".into(), "test_ok".into(), 1);
        let result = TestResult::passed(test, "out".into(), "err".into(), 100);
        assert!(result.passed);
        assert_eq!(result.output, "out");
        assert_eq!(result.error_output, "err");
        assert_eq!(result.duration_ms, 100);
        assert!(result.error.is_none());
        assert!(result.traceback.is_none());
    }

    #[test]
    fn test_test_result_failed() {
        let test = TestItem::new_no_args("t.py".into(), "test_fail".into(), 2);
        let result = TestResult::failed(
            test, "".into(), "".into(), 50,
            "AssertionError".into(), Some("trace".into()),
        );
        assert!(!result.passed);
        assert_eq!(result.error.unwrap(), "AssertionError");
        assert_eq!(result.traceback.unwrap(), "trace");
        assert_eq!(result.duration_ms, 50);
    }

    #[test]
    fn test_test_result_repr_passed() {
        let test = TestItem::new_no_args("t.py".into(), "test_ok".into(), 1);
        let result = TestResult::passed(test, String::new(), String::new(), 42);
        let repr = result.__repr__();
        assert!(repr.contains("PASSED"));
        assert!(repr.contains("test_ok"));
        assert!(repr.contains("42"));
    }

    #[test]
    fn test_test_result_repr_failed() {
        let test = TestItem::new_no_args("t.py".into(), "test_bad".into(), 1);
        let result = TestResult::failed(
            test, String::new(), String::new(), 99,
            "error".into(), None,
        );
        let repr = result.__repr__();
        assert!(repr.contains("FAILED"));
        assert!(repr.contains("test_bad"));
        assert!(repr.contains("99"));
    }

    #[test]
    fn test_test_item_clone() {
        let item = TestItem::new_no_args("a.py".into(), "test".into(), 7);
        let cloned = item.clone();
        assert_eq!(item.path, cloned.path);
        assert_eq!(item.name, cloned.name);
        assert_eq!(item.line_no, cloned.line_no);
    }

    #[test]
    fn test_test_result_clone() {
        let test = TestItem::new_no_args("t.py".into(), "test".into(), 1);
        let result = TestResult::passed(test, "o".into(), "e".into(), 5);
        let cloned = result.clone();
        assert_eq!(result.passed, cloned.passed);
        assert_eq!(result.output, cloned.output);
    }
}
