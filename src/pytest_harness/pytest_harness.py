"""
pytest_harness.py

pytest_harness is an IDE-friendly pytest runner built on Logduo.
It runs test files in isolated subprocesses, captures readable logs,
combines coverage, and produces a compact test dashboard.

Responsibilities:
- run each test file in isolation
- create per-test-file logs
- validate test execution succeeded
- combine per-test-file coverage data
- build aggregate coverage and test summaries

Last edited: 2026-07-11
"""

import tempfile
from pathlib import Path
from typing import NoReturn

from logduo import log

from pytest_harness.arg_resolver import _resolve_harness_args
from pytest_harness.constants_and_classes import (
    DEFAULT_COVERAGE_WARNING_THRESHOLD,
    DEFAULT_WIDTH,
    TestFileRecord,
)
from pytest_harness.record_builder import _build_test_file_record
from pytest_harness.resolve_test_file_paths import _resolve_test_file_paths
from pytest_harness.summary_data_builder import _build_summary_data, _combine_coverage_data_files
from pytest_harness.summary_table_builder import (
    _build_summary_table,
)


# --- pytest_harness() ---------------------------------------------------------
def pytest_harness(
    *,
    test_dir: Path,
    log_dir: Path,
    source_dir: Path,
    include_list: list[str | Path] | None = None,
    exclude_list: list[str | Path] | None = None,
    individual_logs: bool = True,
    coverage_warning_threshold: float | None = DEFAULT_COVERAGE_WARNING_THRESHOLD,
    show_source_file_coverage: bool = True,
    log_keep: int | None = None,
    console_wrap_width: int = DEFAULT_WIDTH,
    show_skipped_and_xfailed: bool = False,
    debug_pytest_harness: bool = False,
) -> NoReturn:
    """
    Purpose
    -------
    Run a complete pytest workflow from an IDE or Python script.

    pytest_harness runs each selected test file in an isolated subprocess,
    captures readable logs, combines coverage across all test files, and
    displays one aggregate test and coverage dashboard.

    The function ends the process with:
        - SystemExit(0) when the complete test run succeeds
        - SystemExit(1) when tests fail or a test file cannot be processed

    Example
    -------
        from pathlib import Path

        pytest_harness(
            test_dir=Path("tests"),
            log_dir=Path("logs"),
            source_dir=Path("src") / "my_package",
            log_keep=5,
        )

    Required arguments
    ------------------
    test_dir : Path
        Directory containing the pytest test files to run.

    log_dir : Path
        Root directory where pytest_harness creates a time-stamped
        output directory for the current run.

        The run directory contains:
            - the main summary log
            - optional individual test-file logs

    source_dir : Path
        Source-code directory measured by coverage.

        Example:
            Path("src") / "my_package"

        pytest_harness creates and manages its own temporary coverage
        configuration. Coverage settings in pyproject.toml are not required.

    Test selection
    --------------
    include_list : list[str | Path] | None
        Restrict the run to specified test files or directories.

        Paths are resolved relative to test_dir unless absolute paths
        are supplied.

        If omitted, all discoverable test files under test_dir are considered.

    exclude_list : list[str | Path] | None
        Exclude specified test files or directories from the run.

        Paths are resolved relative to test_dir unless absolute paths
        are supplied.

    Logging
    -------
    individual_logs : bool
        Create a separate detailed log for each test file.

        Default:
            True

    log_keep : int | None
        Number of recent time-stamped run directories to retain.

        Use None to retain all run directories.

        Default:
            None

    console_wrap_width : int
        Maximum width used for console output and the summary dashboard.

        Default:
            DEFAULT_WIDTH

    Coverage
    --------
    coverage_warning_threshold : float | None
        Coverage percentage below which source files are marked with
        a warning in the summary dashboard.

        Use None to disable coverage warnings.

        This setting does not change the process exit code.

        Default:
            DEFAULT_COVERAGE_WARNING_THRESHOLD

    show_source_file_coverage : bool
        Include the per-source-file coverage table in the summary dashboard.

        Default:
            True

    Test outcome display
    --------------------
    show_skipped_and_xfailed : bool
        Include detailed entries for Skipped and XFailed test functions.

        Failed, Error, and XPassed test functions are always shown.

        Default:
            False

    Debugging
    ---------
    debug_pytest_harness : bool
        Display additional internal diagnostic information, including the
        exact test files selected for execution.

        Intended for debugging pytest_harness itself rather than ordinary
        project test runs.

        Default:
            False

    Failure rules
    -------------
    The run exits with SystemExit(1) when any of the following occurs:
        - one or more test functions Failed
        - one or more test functions produced an Error
        - one or more tests unexpectedly XPassed
        - a test file was not processed successfully
        - a test file collected no tests

    Skipped and XFailed tests do not cause the run to fail.

    Notes
    -----
        - Each test file runs in its own subprocess.
        - A crash or collection failure in one test file does not prevent
          later test files from running.
        - Coverage data from all successfully executed test files is combined.
        - Temporary coverage files are removed after summary data is built.
        - The function raises SystemExit rather than returning normally.
    """

    args = _resolve_harness_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        include_list=include_list,
        exclude_list=exclude_list,
        coverage_warning_threshold=coverage_warning_threshold,
        individual_logs=individual_logs,
        show_source_file_coverage=show_source_file_coverage,
        log_keep=log_keep,
        console_wrap_width=console_wrap_width,
        show_skipped_and_xfailed=show_skipped_and_xfailed,
        debug_pytest_harness=debug_pytest_harness,
    )

    log.configure(
        log_dir_path=args.log_dir,
        log_file_layout="run",
        log_verbosity=3,
        keep=args.log_keep,
        write_config_table=False,
        console_prefix="off",
        console_wrap_width=args.console_wrap_width,
        log_prefix="off",
    )

    output_dir_path = log.output_dir_path
    if output_dir_path is None:
        raise RuntimeError(

            "Logduo did not create an output directory."

        )

    relative_test_file_paths = _resolve_test_file_paths(
        test_dir_path=args.test_dir,
        include_list=args.include_list,
        exclude_list=args.exclude_list,
    )

    if debug_pytest_harness:
        print("\nDEBUG: Exact test files pytest_harness will run:")
        for index, relative_test_file_path in enumerate(relative_test_file_paths, start=1):
            print(f"    {index:>2}. {relative_test_file_path}")
        print(
            f"DEBUG: Exact test-file count: "
            f"{len(relative_test_file_paths)}\n"
        )

    # --- Temporary per-test-file coverage data ---
    coverage_temp_dir = tempfile.TemporaryDirectory(
        prefix="coverage_",
        dir=output_dir_path,
    )
    coverage_dir_path = Path(coverage_temp_dir.name)

    # --- Run test files ---
    results: list[TestFileRecord] = []

    test_file_count = len(relative_test_file_paths)
    print(
        f"Running {test_file_count} test files: ",
        end="",
        flush=True,
    )

    for relative_test_file_path in relative_test_file_paths:
        print(".", end="", flush=True)

        test_file_path = args.test_dir / relative_test_file_path

        if not test_file_path.exists():
            raise RuntimeError(
                "Error in pytest_harness_runner.py\n"
                "Unrecognized test file:\n"
                f"    {relative_test_file_path}"
            )

        if not test_file_path.is_file():
            raise RuntimeError(
                "Expected file but found something else:\n"
                f"    {test_file_path}"
            )

        try:
            test_file_path.read_text(encoding="utf-8")
        except OSError as e:
            raise RuntimeError(
                "Unable to read test file:\n"
                f"    {test_file_path}\n"
                f"    {e}"
            ) from e

        # Keep generated logs flat while preserving nested test-file identity.
        test_file_safe_stem = (
            str(relative_test_file_path.with_suffix(""))
            .replace("/", "__")
            .replace("\\", "__")
        )

        test_file_log_path = output_dir_path / f"{test_file_safe_stem}.log"
        coverage_data_file_path = (
            coverage_dir_path / f".coverage.{test_file_safe_stem}"
        )

        # Create temporary coverage config file - do not rely on pyproject.toml
        coverage_config_file_path = coverage_dir_path / "pytest_harness_coveragerc"
        coverage_config_file_path.write_text(
            "[run]\n"
            "branch = true\n"
            f"source = {args.source_dir}\n"
            "relative_files = false\n"
            "parallel = true\n"
            "concurrency = multiprocessing\n"
            "patch = subprocess\n"
            "\n"
            "[report]\n"
            "skip_empty = true\n"
            "show_missing = true\n"
            "precision = 2\n",
            encoding="utf-8",
        )

        result = _build_test_file_record(
            test_file_path=test_file_path,
            test_file_log_path=test_file_log_path,
            source_dir=args.source_dir,
            coverage_data_file_path=coverage_data_file_path,
            # extra_pytest_args=["-q"],    # "-q" already called, extra_pytest_args[] reserved for future args
            coverage_config_file_path=coverage_config_file_path,
            individual_logs=individual_logs,
            debug_pytest_harness=debug_pytest_harness,
        )

        results.append(result)

    # Combine the separate per-test-file data files once.
    combined_coverage_result = _combine_coverage_data_files(
        coverage_dir_path=coverage_dir_path,
        source_dir=args.source_dir,
    )

    # All combined data is now stored in normal Python records.
    coverage_temp_dir.cleanup()

    print(" done", end="", flush=True)
    print(" ")
    print(" ")

    summary_data = _build_summary_data(
        pytest_test_file_records=results,
        combined_coverage_result=combined_coverage_result,
        show_skipped_and_xfailed=args.show_skipped_and_xfailed,
        debug_pytest_harness=args.debug_pytest_harness,
    )

    summary_text = _build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=args.coverage_warning_threshold,
        show_skipped_and_xfailed=args.show_skipped_and_xfailed,
        show_source_file_coverage=args.show_source_file_coverage,
    )
    log(summary_text)

    run_failed = (
            summary_data.failed_test_function_count > 0
            or summary_data.error_test_function_count > 0
            or summary_data.xpassed_test_function_count > 0
            or summary_data.not_processed_test_file_count > 0
            or summary_data.no_tests_collected_test_file_count > 0
    )


    exit_code = 1 if run_failed else 0
    log.close()

    raise SystemExit(exit_code)
