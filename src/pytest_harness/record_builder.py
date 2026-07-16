"""
record_builder.py

A pytest-based framework for unit pytest_files, integration pytest_files,
and artifact-driven smoke/visual testing.


Reusable development-mode pytest runner engine for logduo.

NOTE:
1. Coverage source is supplied by source_dir and may be
either a package directory or source tree root.

Example:
    source_dir=PROJECT_ROOT / "src" / "logduo"

2. Pytest execution policy is intentionally defined here rather than
pyproject.toml so the development test harness remains self-contained
and reproducible regardless of project-level pytest configuration.

Last edited: 2026-03-18
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from pytest_harness.constants_and_classes import TestFileRecord, TestFileStatus

PYTEST_NO_TESTS_COLLECTED_EXIT_CODE = 5

# --- _build_test_file_record() ------------------------------------------------------------
def _build_test_file_record(  # noqa: PLR0915
    *,
    test_file_path: Path,
    test_file_log_path: Path,
    source_dir: Path,
    coverage_data_file_path: Path,
    extra_pytest_args: list[str] | None = None,
    coverage_config_file_path: Path | None = None,
    individual_logs: bool = True,
    debug_pytest_harness: bool = False,    # noqa  # maybe unused, but reserved for future use
) -> TestFileRecord:
    """
    Dev-mode pytest runner using subprocess.

    Guarantees correct coverage instrumentation.
    """

    if not source_dir.exists():
        raise RuntimeError(
            f"Source directory does not exist:\n"
            f"    {source_dir}"
        )


    # Lazy imports (after subprocess design decision)
    from logduo import log
    from logduo.utils.wrap.wrap_text import strip_ansi

    log.join()

    test_logger: Callable[[str], Any] | None = None

    if individual_logs:
        test_logger = cast(
            Callable[[str], Any],
            log.new_logger(
                test_file_log_path,
                to_console=False,
                to_main_log=False,
                log_prefix="off",
            ),
        )


    # --- temporary JSON to record pass and fail count ---
    with tempfile.NamedTemporaryFile(
            suffix=".json",
            delete=False,
    ) as temp_file:
        test_file_report_path = Path(temp_file.name)

    pytest_cmd = [
        sys.executable,

        "-m",
        "pytest",

        # Ignore addopts from pyproject.toml.
        "-o",
        "addopts=",

        # --- Output ---
        "-q",  # quieter pytest output
        "-rA",  # summary for all test outcomes
        "--color=yes",  # preserve colored output
        "--capture=no",  # allow test print() output
        "--tb=short",  # compact tracebacks
        # "--showlocals",  # include local variables in failures, too big
        "--durations=10",  # show 10 slowest pytest_files

        # --- Execution policy ---
        "--maxfail=0",  # run all pytest_files
        "--strict-markers",  # reject unknown pytest markers
        "--disable-warnings",  # suppress warning summary
        "--reruns=0",  # do not rerun failures

        # --- Coverage ---
        f"--cov={source_dir}",  # measure coverage for logduo package
        f"--cov-config={coverage_config_file_path}",
        "--cov-branch",  # include branch coverage
        # Use "--cov-report=" instead to suppress coverage tables in individual logs.
        (
            "--cov-report=term-missing"
            if individual_logs
            else "--cov-report="
        ),

        # --- Test file path ---
        str(test_file_path),

        # --- JSON test_file_report ---
        "--json-report",  # emit machine-readable test results
        f"--json-report-file={test_file_report_path}",
    ]


    if extra_pytest_args:
        pytest_cmd.extend(extra_pytest_args)

    start = time.time()

    subprocess_env = os.environ.copy()
    subprocess_env["COVERAGE_FILE"] = str(coverage_data_file_path)

    process = subprocess.Popen(
        pytest_cmd,
        env=subprocess_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    captured: list[str] = []

    assert process.stdout is not None

    for line in process.stdout:
        captured.append(line)

    process.wait()
    duration = time.time() - start

    if test_logger is not None:
        cleaned = strip_ansi("".join(captured))
        test_logger(cleaned)
        test_logger(f"pytest exit code: {process.returncode}")
        test_logger(f"duration: {duration:.2f} seconds")


    # --- Read pytest JSON report, then delete temporary file ---
    passed_test_function_names: list[str] = []
    failed_test_function_names: list[str] = []
    error_test_function_names: list[str] = []
    skipped_test_function_names: list[str] = []
    xfailed_test_function_names: list[str] = []
    xpassed_test_function_names: list[str] = []


    try:
        test_file_report = json.loads(test_file_report_path.read_text())
        summary = test_file_report["summary"]
        passed_test_function_count = summary.get("passed", 0)
        failed_test_function_count = summary.get("failed", 0)
        error_test_function_count = (
                summary.get("error", 0)
                or summary.get("errors", 0)
        )
        skipped_test_function_count = summary.get("skipped", 0)
        xfailed_test_function_count = summary.get("xfailed", 0)
        xpassed_test_function_count = summary.get("xpassed", 0)

        for test_record in test_file_report.get("tests", []):
            nodeid = test_record["nodeid"]
            test_function_name = nodeid.rsplit("::", maxsplit=1)[-1]
            outcome = test_record["outcome"]

            if outcome == "passed":
                passed_test_function_names.append(test_function_name)
            elif outcome == "failed":
                failed_test_function_names.append(test_function_name)
            elif outcome in ("error", "errors"):
                error_test_function_names.append(test_function_name)
            elif outcome == "skipped":
                skipped_test_function_names.append(test_function_name)
            elif outcome == "xfailed":
                xfailed_test_function_names.append(test_function_name)
            elif outcome == "xpassed":
                xpassed_test_function_names.append(test_function_name)
            else:
                raise RuntimeError(
                    f"Unexpected pytest outcome: {outcome!r}\n"
                    f"Test: {nodeid}"
                )


    finally:
        test_file_report_path.unlink(missing_ok=True)

    # Pytest exit codes:
    # 0  tests completed successfully
    # 1  tests completed, with failures
    # 2  interrupted
    # 3  internal error
    # 4  command-line usage error
    # 5  no tests collected

    if process.returncode == PYTEST_NO_TESTS_COLLECTED_EXIT_CODE:
        status = TestFileStatus.NO_TESTS_COLLECTED
        file_error_message = None

    elif process.returncode not in (0, 1):
        status = TestFileStatus.NOT_PROCESSED
        file_error_message = "".join(captured).strip() or None

    else:
        status = TestFileStatus.PROCESSED
        file_error_message = None

    if status is TestFileStatus.PROCESSED:
        assert passed_test_function_count == len(passed_test_function_names)
        assert failed_test_function_count == len(failed_test_function_names)
        assert error_test_function_count == len(error_test_function_names)
        assert skipped_test_function_count == len(skipped_test_function_names)
        assert xfailed_test_function_count == len(xfailed_test_function_names)
        assert xpassed_test_function_count == len(xpassed_test_function_names)
    elif status is TestFileStatus.NO_TESTS_COLLECTED:
        assert not test_file_report.get("tests")



    return TestFileRecord(
        test_file_path=str(test_file_path),
        exit_code=process.returncode,
        status=status,
        file_error_message=file_error_message,
        passed_test_function_count=passed_test_function_count,
        failed_test_function_count=failed_test_function_count,
        error_test_function_count=error_test_function_count,
        skipped_test_function_count=skipped_test_function_count,
        xfailed_test_function_count=xfailed_test_function_count,
        xpassed_test_function_count=xpassed_test_function_count,
        duration_seconds=duration,
        passed_test_function_names=passed_test_function_names,
        failed_test_function_names=failed_test_function_names,
        error_test_function_names=error_test_function_names,
        skipped_test_function_names=skipped_test_function_names,
        xfailed_test_function_names=xfailed_test_function_names,
        xpassed_test_function_names=xpassed_test_function_names,
    )

