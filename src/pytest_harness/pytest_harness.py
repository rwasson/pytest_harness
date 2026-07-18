"""
pytest_harness.py

pytest_harness is an IDE-friendly pytest workflow runner built on Logduo.

- runs each test file in isolation and continues when an individual file fails
- creates a console dashboard and summary log
- optionally creates detailed per-test-file logs with missing source lines
- presents aggregate coverage with optional per-test-file and per-source-file details

Last edited: 2026-07-18
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
from pytest_harness.summary_table_builder import _build_summary_table


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
    Run a complete pytest workflow from an IDE or Python script.

    pytest_harness runs each selected test file in an isolated subprocess, so
    a crash or collection failure in one file does not prevent later files from
    running. It combines coverage and presents one console dashboard and summary
    log, with optional detailed logs for each test file.

    Example
    -------
    Create a runner script such as ``run_tests.py`` and run it directly from
    your IDE:

        from pathlib import Path

        from pytest_harness import pytest_harness

        PROJECT_DIR = Path(__file__).resolve().parent

        pytest_harness(
            test_dir=PROJECT_DIR / "tests",
            log_dir=PROJECT_DIR / "logs",
            source_dir=PROJECT_DIR / "src" / "my_package",
            log_keep=5,
        )

    pytest_harness ends the process with SystemExit, so the call should be the
    final operation in the runner script.

    Required arguments
    ------------------
    test_dir : Path
        Directory containing the pytest test files.

    log_dir : Path
        Directory where time-stamped pytest_harness run folders are created.

    source_dir : Path
        Source-code directory measured by coverage.

    Test selection
    --------------
    include_list : list[str | Path] | None
        Run only the specified files or directories.

    exclude_list : list[str | Path] | None
        Exclude the specified files or directories.
        Relative paths in either list are resolved from test_dir.

    Output
    ------
    individual_logs : bool
        Create a detailed log for each test file. Default is True.

    log_keep : int | None
        Number of recent run directories to retain. None retains all runs.

    console_wrap_width : int
        Width used for console output and the summary dashboard.

    Coverage
    --------
    coverage_warning_threshold : float | None
        Mark source files below this coverage percentage in the dashboard.
        This does not affect the exit code. None disables warnings.

    show_source_file_coverage : bool
        Include per-source-file coverage in the dashboard. Default is True.

    Test details
    ------------
    show_skipped_and_xfailed : bool
        Include detailed Skipped and XFailed entries. Failed, Error, and
        XPassed entries are always shown.

    debug_pytest_harness : bool
        Display internal diagnostic details, including the exact selected files.

    Exit behavior
    -------------
        - SystemExit(0) when the complete run succeeded
        - SystemExit(1) when a test failed or unexpectedly passed, or when
            a test file could not be processed or collected no tests.
            Skipped and XFailed tests do not count as failed tests.

    """
    runner_results: list[TestFileRecord] = []

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

    try:
        output_dir_path = log.output_dir_path
        if output_dir_path is None:
            raise RuntimeError("Logduo did not create an output directory.")

        relative_test_file_paths = _resolve_test_file_paths(
            test_dir_path=args.test_dir,
            include_list=args.include_list,
            exclude_list=args.exclude_list,
        )
        test_file_count = len(relative_test_file_paths)
        print(
            f"Running {test_file_count} test files: ",
            end="",
            flush=True,
        )

        if args.debug_pytest_harness:
            print("\nDEBUG: Exact test files pytest_harness will run:")
            for index, relative_test_file_path in enumerate(relative_test_file_paths, start=1):
                print(f"    {index:>2}. {relative_test_file_path}")
            print(
                f"DEBUG: Exact test-file count: "
                f"{len(relative_test_file_paths)}\n"
            )

        with tempfile.TemporaryDirectory(
            prefix="coverage_",
            dir=output_dir_path,
        ) as coverage_temp_dir_name:
            coverage_dir_path = Path(coverage_temp_dir_name)
            coverage_config_file_path = (
                coverage_dir_path / "pytest_harness_coveragerc"
            )

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

                test_file_result = _build_test_file_record(
                    test_file_path=test_file_path,
                    test_file_log_path=test_file_log_path,
                    source_dir=args.source_dir,
                    coverage_data_file_path=coverage_data_file_path,
                    # extra_pytest_args=["-q"],    # "-q" already called, extra_pytest_args[] reserved for future args
                    coverage_config_file_path=coverage_config_file_path,
                    individual_logs=args.individual_logs,
                    debug_pytest_harness=args.debug_pytest_harness,
                )

                runner_results.append(test_file_result)

            combined_coverage_result = _combine_coverage_data_files(
                coverage_dir_path=coverage_dir_path,
                source_dir=args.source_dir,
            )

            print(" done", flush=True)
            print()

            summary_data = _build_summary_data(
                pytest_test_file_records=runner_results,
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

    finally:
        log.close()

    raise SystemExit(exit_code)
