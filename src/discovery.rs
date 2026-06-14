use crate::types::TestItem;
use pyo3::prelude::*;
use std::path::Path;
use std::sync::Mutex;

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
pub fn discover_tests(_py: Python<'_>, root_dir: &str, pattern: Option<&str>) -> PyResult<Vec<TestItem>> {
    let root = Path::new(root_dir);
    if !root.exists() {
        return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(format!(
            "Directory not found: {}",
            root_dir
        )));
    }

    let all_tests = Mutex::new(Vec::new());

    let walker = walkdir::WalkDir::new(root)
        .follow_links(true)
        .into_iter()
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            !name.starts_with('.')
                && name != "__pycache__"
                && name != ".venv"
                && name != "node_modules"
                && name != "target"
                && name != "site"
        });

    let entries: Vec<_> = walker
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.path().to_string_lossy().to_string())
        .collect();

    let pattern = pattern.map(|p| p.to_lowercase());

    for filepath in &entries {
        if !filepath.ends_with(".py") {
            continue;
        }
        let filename = Path::new(filepath)
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();
        if !is_test_file(&filename) {
            continue;
        }
        if let Some(ref pat) = pattern {
            if !filepath.to_lowercase().contains(pat) {
                continue;
            }
        }

        if let Ok(tests) = discover_tests_in_file(_py, filepath) {
            all_tests.lock().unwrap().extend(tests);
        }
    }

    let mut result = all_tests.into_inner().unwrap();
    result.sort_by(|a, b| a.path.cmp(&b.path).then_with(|| a.line_no.cmp(&b.line_no)));
    Ok(result)
}
