use crate::types::TestItem;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::path::Path;

fn is_test_file(filename: &str) -> bool {
    filename.starts_with("test_") || filename.ends_with("_test.py")
}

fn collect_class_methods(
    body: &Bound<'_, PyAny>,
    filepath: &str,
    class_name: &str,
    tests: &mut Vec<TestItem>,
) -> PyResult<()> {
    for item_result in body.try_iter()? {
        let item = item_result?;
        let item_type = item
            .getattr("__class__")?
            .getattr("__name__")?
            .extract::<String>()?;
        if item_type == "FunctionDef" || item_type == "AsyncFunctionDef" {
            let method_name = item.getattr("name")?.extract::<String>()?;
            if method_name.starts_with("test_") {
                let lineno = item.getattr("lineno")?.extract::<u32>()?;
                    tests.push(TestItem {
                        path: filepath.to_string(),
                        name: format!("{}::{}", class_name, method_name),
                        line_no: lineno,
                        args_json: String::new(),
                    });
            }
        }
    }
    Ok(())
}

fn discover_tests_in_file(py: Python<'_>, filepath: &str) -> PyResult<Vec<TestItem>> {
    let ast = py.import("ast")?;
    let source = std::fs::read_to_string(filepath).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!(
            "Cannot read {}: {}",
            filepath, e
        ))
    })?;

    let tree = ast.call_method1("parse", (source,))?;
    let body = tree.getattr("body")?;

    let mut tests = Vec::new();

    for node_result in body.try_iter()? {
        let node = node_result?;
        let node_type = node
            .getattr("__class__")?
            .getattr("__name__")?
            .extract::<String>()?;

        match node_type.as_str() {
            "FunctionDef" | "AsyncFunctionDef" => {
                let name = node.getattr("name")?.extract::<String>()?;
                if name.starts_with("test_") {
                    let lineno = node.getattr("lineno")?.extract::<u32>()?;
                    tests.push(TestItem {
                        path: filepath.to_string(),
                        name,
                        line_no: lineno,
                        args_json: String::new(),
                    });
                }
            }
            "ClassDef" => {
                let class_name = node.getattr("name")?.extract::<String>()?;
                if class_name.starts_with("Test") {
                    if let Ok(body) = node.getattr("body") {
                        collect_class_methods(&body, filepath, &class_name, &mut tests)?;
                    }
                }
            }
            _ => {}
        }
    }

    Ok(tests)
}

#[pyfunction]
#[pyo3(signature = (root_dir, pattern=None))]
pub fn discover_tests(py: Python<'_>, root_dir: &str, pattern: Option<&str>) -> PyResult<Vec<TestItem>> {
    let root = Path::new(root_dir);
    if !root.exists() {
        return Ok(Vec::new());
    }

    let pattern = pattern.map(|p| p.to_lowercase());

    let test_files: Vec<String> = walkdir::WalkDir::new(root)
        .follow_links(true)
        .into_iter()
        .filter_entry(|e| {
            if e.depth() == 0 {
                return true;
            }
            let name = e.file_name().to_string_lossy();
            !name.starts_with('.')
                && name != "__pycache__"
                && name != ".venv"
                && name != "node_modules"
                && name != "target"
                && name != "site"
        })
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "py"))
        .filter(|e| {
            let name = e.file_name().to_string_lossy();
            is_test_file(&name)
        })
        .map(|e| e.path().to_string_lossy().to_string())
        .collect();

    let all_tests: Vec<TestItem> = py.detach(|| {
        test_files
            .par_iter()
            .map(|filepath| {
                Python::try_attach(|py| {
                    discover_tests_in_file(py, filepath).ok()
                })
            })
            .filter_map(|result| result.flatten())
            .flatten()
            .collect()
    });

    let mut result = all_tests;
    if let Some(ref pat) = pattern {
        result.retain(|t| t.name.to_lowercase().contains(pat) || t.path.to_lowercase().contains(pat));
    }
    result.sort_by(|a, b| a.path.cmp(&b.path).then_with(|| a.line_no.cmp(&b.line_no)));
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_test_file_prefix() {
        assert!(is_test_file("test_foo.py"));
        assert!(is_test_file("test_bar.py"));
    }

    #[test]
    fn test_is_test_file_suffix() {
        assert!(is_test_file("foo_test.py"));
        assert!(is_test_file("bar_test.py"));
    }

    #[test]
    fn test_is_test_file_negative() {
        assert!(!is_test_file("regular.py"));
        assert!(!is_test_file("test.txt"));
        assert!(!is_test_file("setup.py"));
        assert!(!is_test_file("conftest.py"));
    }

    #[test]
    fn test_is_test_file_edge_cases() {
        assert!(is_test_file("test_.py"));
        assert!(is_test_file("_test.py"));
        assert!(!is_test_file(""));
        assert!(!is_test_file(".py"));
    }

    #[test]
    fn test_is_test_file_path_with_dir() {
        // is_test_file receives only the basename, not the full path
        assert!(is_test_file("test_foo.py"));
        assert!(is_test_file("bar_test.py"));
        assert!(!is_test_file("helper.py"));
    }

    #[test]
    fn test_test_item_new_no_args() {
        let item = TestItem::new_no_args(
            "/path/test.py".into(),
            "test_hello".into(),
            10,
        );
        assert_eq!(item.path, "/path/test.py");
        assert_eq!(item.name, "test_hello");
        assert_eq!(item.line_no, 10);
    }
}
