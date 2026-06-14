use pyo3::prelude::*;

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct TestItem {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub line_no: u32,
}

#[pymethods]
impl TestItem {
    fn __repr__(&self) -> String {
        format!("TestItem({}:{}: {})", self.path, self.line_no, self.name)
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
