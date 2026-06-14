from typing import List, Optional

class TestItem:
    path: str
    name: str
    line_no: int
    def __repr__(self) -> str: ...

class TestResult:
    test: TestItem
    passed: bool
    output: str
    error_output: str
    duration_ms: int
    error: Optional[str]
    traceback: Optional[str]
    def __repr__(self) -> str: ...

def discover_tests(root_dir: str, pattern: Optional[str] = ...) -> List[TestItem]: ...
def run_tests(tests: List[TestItem], num_workers: Optional[int] = ...) -> List[TestResult]: ...
def run_tests_sequential(tests: List[TestItem]) -> List[TestResult]: ...
