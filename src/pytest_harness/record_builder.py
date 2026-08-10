"""
record_builder.py

Run one pytest test file in an isolated subprocess and build its result record.
The runner captures pytest output, collects JSON test results, writes optional
individual logs, and creates a separate coverage data file for each test file.

Coverage source is supplied by tested_code_dir and may be either a package
directory or a source-tree root.

Pytest execution policy is defined here rather than in project configuration
so pytest_harness remains reproducible across projects.

Last edited: 2026-08-10
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

from pytest_harness.constants_and_classes import (
    TestFileRecord,
    TestFileStatus,
    TestFunctionRecord,
)

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
TEST_TIMEOUT_ERROR_CODE = 102
JSON_REPORT_ERROR_CODE = 103


# --- _build_test_file_record() ------------------------------------------------
def _build_test_file_record(  # noqa: PLR0912, PLR0915
    *,
    test_file_path: Path,
    test_file_label: str,
    test_file_log_path: Path,
    tested_code_dir: Path,
    coverage_data_file_path: Path,
    coverage_config_file_path: Path,
    progress_file_path: Path,
    test_file_logs: bool = True,
    debug_harness: bool = False,
    random_order: bool = False,
    random_order_seed: int | None = None,
    test_function_timeout: float | None = None,
    extra_pytest_args: list[str] | None = None,
) -> TestFileRecord:
    """
    pytest runner using subprocess.

    Guarantees correct coverage instrumentation.
    """

    preflight_error_message = _preflight_test_file_error_check(test_file_path)
    if preflight_error_message is not None:
        return _build_not_processed_record(
            test_file_path=test_file_path,
            test_file_label=test_file_label,
            file_error_message=preflight_error_message,
            test_file_exit_code=PREFLIGHT_ERROR_CODE,
        )


    # Lazy imports (after subprocess design decision)
    from logduo import log
    from logduo.utils.wrap.wrap_text import strip_ansi

    log.join()

    test_logger: Callable[[str], Any] | None = None

    if test_file_logs:
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

    pytest_cmd = _build_pytest_command(
        test_file_path=test_file_path,
        tested_code_dir=tested_code_dir,
        coverage_config_file_path=coverage_config_file_path,
        test_file_report_path=test_file_report_path,
        test_file_logs=test_file_logs,
        random_order=random_order,
        random_order_seed=random_order_seed,
        test_function_timeout=test_function_timeout,
        extra_pytest_args=extra_pytest_args,
    )

    start = time.perf_counter()
    subprocess_env = _build_subprocess_env(
        coverage_data_file_path=coverage_data_file_path,
        progress_file_path=progress_file_path,
    )

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
            test_file_label=test_file_label,
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

    (
        collected_test_function_node_ids,
        started_test_function_node_ids,
        progress_outcomes,
        progress_durations,
        current_test_function_node_id,
    ) = _read_test_function_progress(progress_file_path)

    timeout_detected = _pytest_timeout_detected(
        test_function_timeout=test_function_timeout,
        captured_output=captured_output,
        current_test_function_node_id=current_test_function_node_id,
    )

    if debug_harness and process.returncode != EXIT_CODE_0:
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
    try:
        warning_messages, test_function_records = _read_pytest_json_report(test_file_report_path)

    except (
            OSError,
            UnicodeError,
            KeyError,
            TypeError,
            ValueError,
            RuntimeError,

    ) as e:

        if timeout_detected:
            # The progress plugin may know substantially more than the
            # incomplete JSON report after a timeout. Build records for
            # every successfully collected test function.
            test_function_records = []

            for node_id in collected_test_function_node_ids:
                outcome: str | None

                if node_id == current_test_function_node_id:
                    outcome = "timed_out"
                else:
                    outcome = progress_outcomes.get(node_id)

                test_function_records.append(
                    TestFunctionRecord(
                        node_id=node_id,
                        outcome=outcome,
                    )
                )


            timeout_message = (
                "Test function timed out after "
                f"{test_function_timeout:g} seconds."
            )

            if current_test_function_node_id is not None:
                timeout_message += (
                    "\n"
                    f"    {current_test_function_node_id}"
                )

            return _build_not_processed_record(
                test_file_path=test_file_path,
                test_file_label=test_file_label,
                file_error_message=timeout_message,
                test_file_exit_code=TEST_TIMEOUT_ERROR_CODE,
                timed_out_test_function_node_id=current_test_function_node_id,
                duration_seconds=duration,
                collected_test_function_node_ids=collected_test_function_node_ids,
                started_test_function_node_ids=started_test_function_node_ids,
                test_function_records=test_function_records,
            )

        json_error_message = (
            "PYTEST HARNESS INTERNAL ERROR: "
            "Unable to process pytest JSON report:\n"
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
            test_file_label=test_file_label,
            file_error_message=json_error_message,
            test_file_exit_code=JSON_REPORT_ERROR_CODE,
            duration_seconds=duration,
            collected_test_function_node_ids=collected_test_function_node_ids,
            started_test_function_node_ids=started_test_function_node_ids,
        )

    finally:
        test_file_report_path.unlink(missing_ok=True)

    # Add any successfully collected test functions that did not receive
    # a normal pytest JSON outcome. These may later become "not_run".
    records_by_node_id = {
        record.node_id: record
        for record in test_function_records
    }

    for node_id in collected_test_function_node_ids:
        if node_id not in records_by_node_id:
            record = TestFunctionRecord(node_id=node_id, outcome=None)
            test_function_records.append(record)
            records_by_node_id[node_id] = record

    # Apply outcomes preserved by the progress plugin.
    for node_id, outcome in progress_outcomes.items():
        matched_record = records_by_node_id.get(node_id)
        if matched_record is not None:
            matched_record.outcome = outcome

    # Apply measured durations preserved by the progress plugin.
    for node_id, duration_seconds in progress_durations.items():
        matched_record = records_by_node_id.get(node_id)
        if matched_record is not None:
            matched_record.duration_seconds = duration_seconds

    # A timeout is identified by the progress plugin rather than relying
    # on the potentially incomplete pytest JSON report.
    if timeout_detected and current_test_function_node_id is not None:
        timed_out_record = records_by_node_id.get(current_test_function_node_id)
        if timed_out_record is not None:
            timed_out_record.outcome = "timed_out"

    # --- Resolve test-file status ---
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

    if status is TestFileStatus.NO_TESTS_COLLECTED:
        assert not test_function_records


    return TestFileRecord(
        test_file_path=test_file_path,
        test_file_label=test_file_label,
        test_file_exit_code=process.returncode,
        duration_seconds=duration,
        status=status,
        timed_out_test_function_node_id=None,
        not_processed_reason=not_processed_reason,
        file_error_message=file_error_message,
        warning_messages=warning_messages,
        collected_test_function_node_ids=collected_test_function_node_ids,
        started_test_function_node_ids=started_test_function_node_ids,
        test_function_records=test_function_records,
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


# --- _build_pytest_command() --------------------------------------------------
def _build_pytest_command(
    *,
    test_file_path: Path,
    tested_code_dir: Path,
    coverage_config_file_path: Path,
    test_file_report_path: Path,
    test_file_logs: bool,
    random_order: bool,
    random_order_seed: int | None,
    test_function_timeout: float | None,
    extra_pytest_args: list[str] | None,
) -> list[str]:

    tested_code_parent = tested_code_dir.parent.as_posix()  # Windows safe path str

    pytest_command = [
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
        "-p",
        "pytest_timeout",
        "-p",
        "random_order",
        "-p",
        "pytest_harness.progress_plugin",

        # Ignore addopts from pyproject.toml.
        "-o",
        "addopts=",

        # Tests import starting with the name of tested_code_dir.
        # This override applies only to this pytest subprocess.
        "-o",
        f"pythonpath={tested_code_parent}",

        # --- Output ---
        "-vv" if test_file_logs else "-q",
        "-rA",  # summary for all test outcomes
        "--color=yes",  # preserve colored output
        "--capture=no",  # allow test print() output
        "--tb=short",  # compact tracebacks
        # "--showlocals",  # include local variables in failures, too big
        "--durations=10",  # show 10 slowest test setup/call/teardown phases

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
            if test_file_logs
            else "--cov-report="
        ),

        # --- Test file path ---
        str(test_file_path),

        # --- JSON test_file_report ---
        "--json-report",  # emit machine-readable test results
        f"--json-report-file={test_file_report_path}",
    ]
    if random_order:
        pytest_command.append("--random-order")
        if random_order_seed is not None:
            pytest_command.append(f"--random-order-seed={random_order_seed}")
    if test_function_timeout is not None:
        pytest_command.append(f"--timeout={test_function_timeout}")
        pytest_command.append("--timeout-method=thread")

    if extra_pytest_args:
        pytest_command.extend(extra_pytest_args)

    return pytest_command


# --- _build_subprocess_env() --------------------------------------------------
def _build_subprocess_env(
    *,
    coverage_data_file_path: Path,
    progress_file_path: Path,
) -> dict[str, str]:
    """
    subprocess_env["COVERAGE_FILE"] = str(coverage_data_file_path)

    # The harness captures child-process output as text.
    # Use UTF-8 on both ends so Unicode test output is transported consistently
    # across Windows, macOS, and Linux.
    subprocess_env["PYTHONIOENCODING"] = "utf-8"
    subprocess_env["PYTEST_HARNESS_PROGRESS_FILE"] = str(progress_file_path)
    """

    env = os.environ.copy()
    env["COVERAGE_FILE"] = str(coverage_data_file_path)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTEST_HARNESS_PROGRESS_FILE"] = str(progress_file_path)

    return env


# --- _build_not_processed_record() -------------------------------------------
def _build_not_processed_record(
    *,
    test_file_path: Path,
    test_file_label: str,
    file_error_message: str,
    test_file_exit_code: int,
    timed_out_test_function_node_id: str | None = None,
    duration_seconds: float = 0.0,
    collected_test_function_node_ids: list[str] | None = None,
    started_test_function_node_ids: list[str] | None = None,
    test_function_records: list[TestFunctionRecord] | None = None,
) -> TestFileRecord:
    """Return a record for a test file that could not be fully processed."""

    not_processed_reason = _resolve_not_processed_reason(
        test_file_exit_code=test_file_exit_code,
        file_error_message=file_error_message,
    )

    return TestFileRecord(
        test_file_path=test_file_path,
        test_file_label=test_file_label,
        test_file_exit_code=test_file_exit_code,
        duration_seconds=duration_seconds,
        status=TestFileStatus.NOT_PROCESSED,
        timed_out_test_function_node_id=timed_out_test_function_node_id,
        not_processed_reason=not_processed_reason,
        file_error_message=file_error_message,
        warning_messages=[],
        collected_test_function_node_ids=(
            collected_test_function_node_ids
            if collected_test_function_node_ids is not None
            else []
        ),
        started_test_function_node_ids=(
            started_test_function_node_ids
            if started_test_function_node_ids is not None
            else []
        ),
        test_function_records=(
            test_function_records
            if test_function_records is not None
            else []
        ),
    )


# --- _resolve_not_processed_reason() ------------------------------------------
def _resolve_not_processed_reason(  # noqa: PLR0912
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
    if test_file_exit_code == TEST_TIMEOUT_ERROR_CODE:
        return "test function timed out"
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


# --- _read_pytest_json_report() -----------------------------------------------
def _read_pytest_json_report(
    test_file_report_path: Path,
) -> tuple[
    list[str],
    list[TestFunctionRecord],
]:
    """
    Read pytest's JSON report.

    Returns:
        warning_messages:
            Warning messages reported by pytest.

        test_function_records:
            Function records containing node IDs and normal pytest outcomes.
    """
    report_text = test_file_report_path.read_text(encoding="utf-8")

    if not report_text.strip():
        raise ValueError(
            "PYTEST HARNESS INTERNAL ERROR: "
            "Pytest did not create a JSON test report."
        )

    test_file_report = json.loads(report_text)
    warning_messages = _extract_warning_messages(test_file_report)
    test_function_records: list[TestFunctionRecord] = []

    valid_json_outcomes = {
        "passed",
        "failed",
        "error",
        "errors",
        "skipped",
        "xfailed",
        "xpassed",
    }

    for test_record in test_file_report.get("tests", []):
        node_id = test_record["nodeid"]
        outcome = test_record["outcome"]
        if outcome not in valid_json_outcomes:
            raise RuntimeError(
                f"Unexpected pytest outcome: {outcome!r}\n"
                f"Test: {node_id}"
            )

        if outcome == "errors":
            outcome = "error"

        test_function_records.append(TestFunctionRecord(node_id=node_id, outcome=outcome))

    return warning_messages, test_function_records


# --- _extract_warning_messages() ----------------------------------------------
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

# --- _read_test_function_progress() -------------------------------------------
def _read_test_function_progress(
    progress_file_path: Path,
) -> tuple[
    list[str],
    list[str],
    dict[str, str],
    dict[str, float],
    str | None,
]:
    """
    Read test-function collection and execution progress.

    Returns:
        collected_node_ids:
            All node IDs pytest successfully collected.

        started_node_ids:
            Node IDs in the actual order execution began.

        progress_outcomes:
            Completed test-function outcomes keyed by node ID.

        progress_durations:
            Completed test-function durations, in seconds, keyed by node ID.

        current_node_id:
            Node ID that started but did not finish, if any.
    """
    if not progress_file_path.exists():
        return [], [], {}, {}, None

    collected_node_ids: list[str] = []
    started_node_ids: list[str] = []
    progress_outcomes: dict[str, str] = {}
    progress_durations: dict[str, float] = {}
    current_node_id: str | None = None

    for line in progress_file_path.read_text(
        encoding="utf-8",
    ).splitlines():
        event, value = line.split("\t", maxsplit=1)

        if event == "COLLECT":
            collected_node_ids.append(value)

        elif event == "START":
            started_node_ids.append(value)
            current_node_id = value

        elif event == "OUTCOME":
            node_id, outcome = value.split(
                "\t",
                maxsplit=1,
            )
            progress_outcomes[node_id] = outcome

        elif event == "DURATION":
            node_id, duration_text = value.split(
                "\t",
                maxsplit=1,
            )
            progress_durations[node_id] = float(
                duration_text
            )

        elif event == "FINISH":
            if current_node_id == value:
                current_node_id = None

    return (
        collected_node_ids,
        started_node_ids,
        progress_outcomes,
        progress_durations,
        current_node_id,
    )


# --- _pytest_timeout_detected() -----------------------------------------------
def _pytest_timeout_detected(
    *,
    test_function_timeout: float | None,
    captured_output: str,
    current_test_function_node_id: str | None,
) -> bool:

    if test_function_timeout is None:
        return False
    if current_test_function_node_id is None:
        return False

    return "test_function_timeout" in captured_output.lower()
