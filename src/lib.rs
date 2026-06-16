pub mod types;
pub mod discovery;
pub mod runner;

use pyo3::prelude::*;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<types::TestItem>()?;
    m.add_class::<types::TestResult>()?;
    m.add_function(wrap_pyfunction!(discovery::discover_tests, m)?)?;
    m.add_function(wrap_pyfunction!(runner::run_tests, m)?)?;
    m.add_function(wrap_pyfunction!(runner::run_tests_sequential, m)?)?;
    Ok(())
}
