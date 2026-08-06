"""
record_builder.py

Run one pytest test file in an isolated subprocess and build its result record.
The runner captures pytest output, collects JSON test results, writes optional
individual logs, and creates a separate coverage data file for each test file.

Coverage source is supplied by tested_code_dir and may be either a package
directory or a source-tree root.

Pytest execution policy is defined here rather than in project configuration
so pytest_harness remains reproducible across projects.

Last edited: 2026-08-05
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

# pytest exit codes:
EXIT_CODE_0 = 0  # all tests collected and passed
EXIT_CODE_1 = 1  # tests ran and at least one failed
EXIT_CODE_2 = 2  # pytest interrupted
EXIT_CODE_3 = 3  # pytest internal error
EXIT_CODE_4 = 4  # pytest command-line usage error
EXIT_CODE_5 = 5  # no tests collected
EXIT_CODE_6 = 6  # maximum warnings exceeded
#
# pytest_harness per-file processing error codes:
PREFLIGHT_ERROR_CODE = 100
SUBPROCESS_LAUNCH_ERROR_CODE = 101
JSON_REPORT_ERROR_CODE = 102


# --- _build_test_file_record() ------------------------------------------------
def _build_test_file_record(  # noqa: PLR0915
    *,
    test_file_path: Path,
    test_file_log_path: Path,
    tested_code_dir: Path,
    coverage_data_file_path: Path,
    extra_pytest_args: list[str] | None = None,
    coverage_config_file_path: Path,
    individual_logs: bool = True,
    debug_pytest_harness: bool = False,
) -> TestFileRecord:
    """
    pytest runner using subprocess.

    Guarantees correct coverage instrumentation.
    """


    preflight_error_message = _preflight_test_file_error_check(test_file_path)
    if preflight_error_message is not None:
        return _build_not_processed_record(
            test_file_path=test_file_path,
            file_error_message=preflight_error_message,
            test_file_exit_code=PREFLIGHT_ERROR_CODE,
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

    tested_code_parent = tested_code_dir.parent.as_posix()  # Windows safe

    pytest_cmd = [
        sys.executable,

        "-m",
        "pytest",

        # Use only pytest's built-in plugins and the plugins required by
        # pytest_harness. Ignore unrelated third-party plugins installed
        # in the active environment.
        "--disable-plugin-autoload",
        "-p",
        "pytest_cov",
        "-p",
        "pytest_jsonreport",
        "-p",
        "pytest_rerunfailures",

        # Ignore addopts from pyproject.toml.
        "-o",
        "addopts=",

        # Tests import starting with the name of tested_code_dir.
        # This override applies only to this pytest subprocess.
        "-o",
        f"pythonpath={tested_code_parent}",

        # --- Output ---
        "-q",  # quieter pytest output
        "-rA",  # summary for all test outcomes
        "--color=yes",  # preserve colored output
        "--capture=no",  # allow test print() output
        "--tb=short",  # compact tracebacks
        # "--showlocals",  # include local variables in failures, too big
        "--durations=10",  # show 10 slowest test_files

        # --- Execution policy ---
        "--maxfail=0",  # run all test_files
        "--strict-markers",  # reject unknown pytest markers
        "--reruns=0",  # do not rerun failures
        # Do not set --max-warnings. Warnings remain non-fatal and therefore do
        # not change an otherwise successful pytest run into exit code 6.


        # --- Coverage ---
        f"--cov={tested_code_dir}",  # measure the configured tested-code directory
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

    start = time.perf_counter()

    subprocess_env = os.environ.copy()
    subprocess_env["COVERAGE_FILE"] = str(coverage_data_file_path)

    # The harness captures child-process output as text.
    # Use UTF-8 on both ends so Unicode test output is transported consistently
    # across Windows, macOS, and Linux.
    subprocess_env["PYTHONIOENCODING"] = "utf-8"

    try:
        process = subprocess.Popen(
            pytest_cmd,
            env=subprocess_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
    except OSError as e:
        duration = time.perf_counter() - start
        test_file_report_path.unlink(missing_ok=True)
        return _build_not_processed_record(
            test_file_path=test_file_path,
            file_error_message=(
                "Unable to start pytest subprocess:\n"
                f"    {test_file_path}\n"
                f"    {e}"
            ),
            test_file_exit_code=SUBPROCESS_LAUNCH_ERROR_CODE,
            duration_seconds=duration,
        )

    captured: list[str] = []

    assert process.stdout is not None

    for line in process.stdout:
        captured.append(line)

    process.wait()
    duration = time.perf_counter() - start
    captured_output = "".join(captured).strip()

    if debug_pytest_harness and process.returncode != EXIT_CODE_0:
        print()
        print("=" * 80)
        print(f"DEBUG: FLAGGED TEST FILE: {test_file_path}")
        print("=" * 80)
        output_encoding = sys.stdout.encoding or "utf-8"
        safe_captured_output = captured_output.encode(
            output_encoding,
            errors="backslashreplace",
        ).decode(output_encoding)
        print(safe_captured_output, flush=True)
        print("=" * 80)

    if test_logger is not None:
        test_logger(strip_ansi(captured_output))
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
        report_text = test_file_report_path.read_text(encoding="utf-8")
        if not report_text.strip():
            raise ValueError("PYTEST HARNESS INTERNAL ERROR: "
                             "Pytest did not create a JSON test report.")
        test_file_report = json.loads(report_text)
        summary = test_file_report.get("summary")
        if not isinstance(summary, dict):
            raise ValueError("PYTEST HARNESS INTERNAL ERROR: "
                             "Pytest JSON report does not contain a valid summary.")
        warning_messages = _extract_warning_messages(test_file_report)

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

    except (
            OSError,
            UnicodeError,
            KeyError,
            TypeError,
            ValueError,
            RuntimeError,
    ) as e:
        json_error_message = (
            "PYTEST HARNESS INTERNAL ERROR: Unable to process pytest JSON report:\n"
            f"    {test_file_path}\n"
            f"    Pytest exit code: {process.returncode}\n"
            f"    {type(e).__name__}: {e}"
        )

        if captured_output:
            json_error_message += (
                "\n\nPytest output:\n"
                f"{captured_output}"
            )

        return _build_not_processed_record(
            test_file_path=test_file_path,
            file_error_message=json_error_message,
            test_file_exit_code=JSON_REPORT_ERROR_CODE,
            duration_seconds=duration,
        )

    finally:
        test_file_report_path.unlink(missing_ok=True)

    file_error_message: str | None
    not_processed_reason: str | None

    if process.returncode == EXIT_CODE_5:
        status = TestFileStatus.NO_TESTS_COLLECTED
        file_error_message = None
        not_processed_reason = None

    elif process.returncode not in (EXIT_CODE_0, EXIT_CODE_1):
        status = TestFileStatus.NOT_PROCESSED
        file_error_message = captured_output or None
        not_processed_reason = _resolve_not_processed_reason(
            test_file_exit_code=process.returncode,
            file_error_message=file_error_message,
        )

    else:
        status = TestFileStatus.PROCESSED
        file_error_message = None
        not_processed_reason = None


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
        test_file_exit_code=process.returncode,
        status=status,
        file_error_message=file_error_message,
        not_processed_reason=not_processed_reason,
        warning_count=len(warning_messages),
        warning_messages=warning_messages,
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


# === Internal helpers =========================================================

# --- _preflight_test_file_error_check() ---------------------------------------
def _preflight_test_file_error_check(
    test_file_path: Path,
) -> str | None:
    """
    Return an error message when a selected test file cannot be processed.

    The file was already selected by _resolve_test_file_paths(), so failures
    here are per-file processing failures rather than harness setup errors.
    """

    if not test_file_path.exists():
        return (
            "Selected test file no longer exists:\n"
            f"    {test_file_path}"
        )

    if not test_file_path.is_file():
        return (
            "Expected a test file but found something else:\n"
            f"    {test_file_path}"
        )

    try:
        test_file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return (
            "Unable to read test file:\n"
            f"    {test_file_path}\n"
            f"    {e}"
        )

    return None


# --- _build_not_processed_record() -------------------------------------------
def _build_not_processed_record(
    *,
    test_file_path: Path,
    file_error_message: str,
    test_file_exit_code: int,
    duration_seconds: float = 0.0,
) -> TestFileRecord:
    """Return an empty record for a test file that could not be processed."""

    not_processed_reason = _resolve_not_processed_reason(
        test_file_exit_code=test_file_exit_code,
        file_error_message=file_error_message,
    )

    return TestFileRecord(
        test_file_path=str(test_file_path),
        test_file_exit_code=test_file_exit_code,
        status=TestFileStatus.NOT_PROCESSED,
        not_processed_reason=not_processed_reason,
        file_error_message=file_error_message,
        warning_count=0,
        warning_messages=[],
        passed_test_function_count=0,
        failed_test_function_count=0,
        error_test_function_count=0,
        skipped_test_function_count=0,
        xfailed_test_function_count=0,
        xpassed_test_function_count=0,
        duration_seconds=duration_seconds,
        passed_test_function_names=[],
        failed_test_function_names=[],
        error_test_function_names=[],
        skipped_test_function_names=[],
        xfailed_test_function_names=[],
        xpassed_test_function_names=[],
    )


def _resolve_not_processed_reason(
    *,
    test_file_exit_code: int,
    file_error_message: str | None,
) -> str:
    message = (file_error_message or "").lower()

    if test_file_exit_code == PREFLIGHT_ERROR_CODE:
        if "no longer exists" in message:
            dashboard_msg = "missing test file"
        elif "found something else" in message:
            dashboard_msg = "invalid test-file path"
        elif "unable to read" in message:
            dashboard_msg = "unreadable test file"
        else:
            dashboard_msg = "preflight error"
        return dashboard_msg

    if test_file_exit_code == SUBPROCESS_LAUNCH_ERROR_CODE:
        return "subprocess launch failure"

    if test_file_exit_code == JSON_REPORT_ERROR_CODE:
        return "invalid pytest report"

    if "modulenotfounderror" in message:
        dashboard_msg = "missing module"

    elif "importerror" in message:
        dashboard_msg = "import error"

    elif "syntaxerror" in message:
        dashboard_msg = "syntax error"

    elif "error collecting" in message:
        dashboard_msg = "collection error"


    elif test_file_exit_code == EXIT_CODE_2:
        dashboard_msg = "pytest interrupted"

    elif test_file_exit_code == EXIT_CODE_3:
        dashboard_msg = "pytest internal error"

    elif test_file_exit_code == EXIT_CODE_4:
        dashboard_msg = "pytest usage error"

    elif test_file_exit_code == EXIT_CODE_6:
        dashboard_msg = "pytest warning limit exceeded"

    else:
        dashboard_msg = "processing error"

    return dashboard_msg


def _extract_warning_messages(
    test_file_report: dict[str, Any],
) -> list[str]:
    warning_records = test_file_report.get("warnings", [])

    if not isinstance(warning_records, list):
        raise ValueError(
            "PYTEST HARNESS INTERNAL ERROR: "
            "Pytest JSON report does not contain a valid warnings list."
        )

    warning_messages: list[str] = []

    for warning_record in warning_records:
        if not isinstance(warning_record, dict):
            raise ValueError(
                "PYTEST HARNESS INTERNAL ERROR: "
                "Pytest JSON report contains an invalid warning record."
            )

        warning_message = str(
            warning_record.get(
                "message",
                "Unknown pytest warning.",
            )
        )
        warning_category = str(
            warning_record.get(
                "category",
                "Warning",
            )
        )
        warning_filename = warning_record.get("filename")
        warning_line_number = warning_record.get("lineno")

        warning_location = ""

        if warning_filename:
            warning_location = str(warning_filename)

            if warning_line_number is not None:
                warning_location += f":{warning_line_number}"

        if warning_location:
            warning_messages.append(
                f"{warning_location}: "
                f"{warning_category}: {warning_message}"
            )
        else:
            warning_messages.append(
                f"{warning_category}: {warning_message}"
            )

    return warning_messages
