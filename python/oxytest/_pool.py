"""Multiprocessing worker pool for parallel test execution.

Each worker runs tests sequentially in a separate process with its own GIL.
Results are collected via multiprocessing.Queue as serialized dicts.
"""

import multiprocessing
import os
import sys
from typing import Any, Dict, List, Tuple


def _worker_main(task_queue: multiprocessing.Queue, result_queue: multiprocessing.Queue):
    """Worker process: receives batches of tests, executes them, sends results back."""
    # Each worker has its own Python process → own GIL, own caches
    from oxytest._core import run_tests_sequential, TestItem

    while True:
        task = task_queue.get()
        if task is None:
            break
        batch_id, cwd, tests_data = task

        # Change to the project directory so relative paths resolve
        old_cwd = os.getcwd()
        if cwd:
            os.chdir(cwd)

        try:
            # Reconstruct TestItem objects from serialized data
            tests = []
            for td in tests_data:
                t = TestItem()
                t.path = td["path"]
                t.name = td["name"]
                t.line_no = td["line_no"]
                t.args_json = td.get("args_json", "")
                tests.append(t)

            results = run_tests_sequential(tests, False)

            # Serialize results to plain dicts for transport
            result_data = []
            for r in results:
                rd = {
                    "path": r.test.path,
                    "name": r.test.name,
                    "line_no": r.test.line_no,
                    "args_json": r.test.args_json,
                    "passed": r.passed,
                    "output": r.output,
                    "error_output": r.error_output,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                    "traceback": r.traceback,
                }
                result_data.append(rd)
            result_queue.put((batch_id, result_data, None))
        except BaseException as exc:
            result_queue.put((batch_id, None, str(exc)))
        finally:
            os.chdir(old_cwd)


def run_tests_parallel(
    tests: List[Any],
    num_workers: int,
    nocapture: bool = False,
) -> List[Any]:
    """Run tests in parallel using a multiprocessing worker pool.

    Args:
        tests: List of TestItem objects
        num_workers: Number of worker processes (1 = sequential)
        nocapture: If True, don't capture stdout/stderr

    Returns:
        List of TestResult objects (sorted by path then line_no)
    """

    if num_workers <= 1:
        from oxytest._core import run_tests_sequential
        return run_tests_sequential(tests, nocapture=nocapture)

    # Use 'spawn' method for clean process isolation
    multiprocessing.set_start_method("spawn", force=True)

    # Group tests by file to minimize module reimports across workers
    from collections import defaultdict
    grouped: Dict[str, List[Any]] = defaultdict(list)
    for t in tests:
        grouped[t.path].append(t)

    # Create balanced batches: one file's tests stay together
    file_groups = list(grouped.items())
    batches: List[List[Dict[str, Any]]] = [[] for _ in range(num_workers)]
    batch_sizes = [0] * num_workers
    for path, file_tests in file_groups:
        # Assign to the least-loaded worker
        target = min(range(num_workers), key=lambda i: batch_sizes[i])
        batch_data = [
            {
                "path": t.path,
                "name": t.name,
                "line_no": t.line_no,
                "args_json": t.args_json,
            }
            for t in file_tests
        ]
        batches[target].extend(batch_data)
        batch_sizes[target] += len(batch_data)

    # Create queues
    task_queue: multiprocessing.Queue = multiprocessing.Queue()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start worker processes
    workers = []
    cwd = os.getcwd()
    for i in range(num_workers):
        p = multiprocessing.Process(target=_worker_main, args=(task_queue, result_queue))
        p.start()
        workers.append(p)

    # Send batch tasks
    for i, batch in enumerate(batches):
        if batch:
            task_queue.put((i, cwd, batch))

    # Send termination signals
    for _ in range(num_workers):
        task_queue.put(None)

    # Collect results
    pending = sum(1 for b in batches if b)
    all_results: List[Tuple[int, List[Dict[str, Any]]]] = []
    errors = []
    for _ in range(pending):
        batch_id, result_data, error = result_queue.get()
        if error:
            errors.append(f"Worker batch {batch_id}: {error}")
        elif result_data is not None:
            all_results.append((batch_id, list(result_data)))

    # Wait for workers
    for p in workers:
        p.join(timeout=30)
        if p.is_alive():
            p.terminate()
            p.join()

    if errors:
        for e in errors:
            print(f"oxytest: worker error — {e}", file=sys.stderr)

    # Reconstruct TestResult objects from serialized data
    from oxytest._core import test_result_passed, test_result_failed, TestItem  # type: ignore

    reconstructed = []
    for batch_id, data in all_results:
        for rd in data:
            t = TestItem()
            t.path = rd["path"]
            t.name = rd["name"]
            t.line_no = rd["line_no"]
            t.args_json = rd.get("args_json", "")
            if rd["passed"]:
                r = test_result_passed(
                    t, rd["output"], rd["error_output"], rd["duration_ms"]
                )
            else:
                r = test_result_failed(
                    t, rd["output"], rd["error_output"], rd["duration_ms"],
                    rd.get("error") or "", rd.get("traceback"),
                )
            reconstructed.append(r)

    # Sort by path then line_no
    reconstructed.sort(key=lambda r: (r.test.path, r.test.line_no))
    return reconstructed
