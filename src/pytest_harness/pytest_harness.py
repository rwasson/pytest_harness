"""
pytest_harness.py

pytest_harness runs a complete pytest workflow from a Python runner script.

- runs each test file in isolation and continues when an individual file fails
- creates a console dashboard and summary log
- optionally creates detailed per-test-file logs with missing source lines
- presents aggregate coverage with optional per-test-file and per-source-file details

Last edited: 2026-08-10
"""

import tempfile
from pathlib import Path
from secrets import randbelow
from uuid import uuid4

from logduo import log
from rich.text import Text

from pytest_harness.arg_resolver import _resolve_harness_args
from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    DEFAULT_COVERAGE_WARNING_THRESHOLD,
    DEFAULT_DASHBOARD_WIDTH,
    RunResult,
    TestFileRecord,
    TestFunctionRecord,
    ValidatedHarnessArgs,
)
from pytest_harness.dashboard_builder import _build_dashboard
from pytest_harness.file_path_builder import _build_file_paths
from pytest_harness.record_builder import _build_test_file_record
from pytest_harness.resolve_test_file_paths import _resolve_test_file_paths
from pytest_harness.style_helpers import _build_summary_styles, _styled
from pytest_harness.summary_data_builder import _build_summary_data, _combine_coverage_data_files


# --- pytest_harness() ---------------------------------------------------------
def pytest_harness(  # noqa PLR0913   # more than 15 args appropriate
    *,
    test_file_dir: Path,
    log_dir: Path,
    tested_code_dir: Path,
    include_list: list[str | Path] | None = None,
    exclude_list: list[str | Path] | None = None,
    random_order: bool = False,
    random_order_seed: int | None = None,
    test_function_timeout: int | float | None = 200,
    runner_log: bool = True,
    test_file_logs: bool = True,
    log_keep: int | None = None,
    console_dashboard: bool = True,
    console_theme: str = "dark",
    dashboard_width: int = DEFAULT_DASHBOARD_WIDTH,
    show_source_file_coverage: bool = True,
    show_skipped_and_xfailed: bool = False,
    coverage_warning_threshold: float | None = DEFAULT_COVERAGE_WARNING_THRESHOLD,
    debug_harness: bool = False,
) -> RunResult:
    """
    Run a complete pytest workflow from a Python runner script.

    The runner can be launched with one click from an IDE or run like any other
    Python script from Terminal.

    pytest_harness runs each selected test file in an isolated subprocess. A
    crash, timeout, collection failure, or import failure in one test file does
    not prevent later test files from running.

    After all selected files finish, pytest_harness combines coverage data,
    presents a dashboard and summary log, and returns structured run results.
    Optional individual logs provide detailed output for each test file.

    pytest_harness owns logging during the run. Do not configure logging in test
    files or in the runner before calling pytest_harness.

    Test environment
    ----------------
    pytest_harness uses consistent pytest, coverage, import, timeout, and plugin
    settings for each isolated test-file run.

    These settings apply only while pytest_harness is running. They do not modify
    project files, IDE settings, or the caller's Python environment.


    Basic example
    -------------
    Example project layout:

        basic_project/
            src/
                sample_package/
                    __init__.py
                    calculator.py
            tests/
                pytest_harness_runner.py
                test_calculator.py

    In ``pytest_harness_runner.py``:

        from pathlib import Path

        from pytest_harness import pytest_harness

        PROJECT_DIR = Path(__file__).resolve().parents[1]

        result = pytest_harness(
            test_file_dir=PROJECT_DIR / "tests",
            log_dir=PROJECT_DIR / "tests" / "logs",
            tested_code_dir=PROJECT_DIR / "src" / "sample_package",
            log_keep=3,
        )

    In ``test_calculator.py``:

        from sample_package.calculator import add

        def test_add() -> None:
            assert add(4, 7) == 11


    Arguments
    ---------
    Paths (required):
        test_file_dir : Path
            Directory containing pytest test files. Files are discovered
            recursively using pytest-style names such as ``test_*.py``.

        log_dir : Path
            Directory where time-stamped pytest_harness run directories are
            created.

        tested_code_dir : Path
            Directory containing the Python code to measure for coverage.

            Its parent directory is made available for imports within each pytest
            subprocess. Tests should normally import starting with the name of
            tested_code_dir.

            For example:

                tested_code_dir = PROJECT_DIR / "src" / "sample_package"

                from sample_package.calculator import add

            tested_code_dir should normally contain only code intended to be
            included in coverage results.

    Test selection and execution (optional):
        include_list : list[str | Path] | None
            Run only specified test files or directories. Entries may be names,
            relative paths, absolute paths, or directories. Relative paths are
            resolved from test_file_dir. None selects all discovered tests.

        exclude_list : list[str | Path] | None
            Exclude specified test files or directories. None excludes nothing.

        random_order : bool
            Run test functions in randomized order. Default is False.

        random_order_seed : int | None
            Seed used when random_order is True. If None, a seed is generated and
            reported so the order can be reproduced.

        test_function_timeout : int | float | None
            Maximum execution time in seconds for an individual test function.
            None disables the timeout. Default is 200 seconds.

    Output (optional):
        runner_log : bool
            Create the main pytest_harness summary log. Default is True.

        test_file_logs : bool
            Create a detailed log for each test file, including pytest output,
            failures, tracebacks, coverage details, and file duration.
            Default is True.

        log_keep : int | None
            Number of recent run directories to retain. None retains all runs.

        console_dashboard : bool
            Display the summary dashboard in the console. Default is True.

        console_theme : str
            Console color theme: ``"dark"`` or ``"light"``.
            Default is ``"dark"``.

        dashboard_width : int
            Width used for the console and log dashboard. Minimum is 80.
            Default is 150.

        show_skipped_and_xfailed : bool
            Include detailed Skipped and XFailed entries in the dashboard.
            Failed, Error, and XPassed entries are always shown.
            Default is False.

        debug_harness : bool
            Display internal diagnostic information, including selected test files
            and captured output from flagged subprocesses. Default is False.

    Coverage (optional):
        coverage_warning_threshold : float | None
            Total coverage percentage below which a warning is shown. This does
            not affect the process exit code. None disables the warning.

        show_source_file_coverage : bool
            Include per-source-file coverage in the dashboard. Default is True.

    Returns
    -------
    RunResult
        Structured run results containing the harness exit code, file and function
        outcomes, stable and execution-order test IDs, coverage totals, source-file
        coverage records, output directory, random-order seed, and timeout setting.

    Advanced environment behavior
    -----------------------------
    pytest_harness ignores project pytest ``addopts`` and disables automatic
    loading of unrelated third-party pytest plugins. It explicitly loads only the
    plugins required by the harness.

    The parent of tested_code_dir is supplied as the temporary pytest pythonpath
    for each subprocess. pytest_harness does not modify the caller's sys.path,
    environment variables, IDE settings, pyproject.toml, or pytest.ini.

    Subprocesses use the active Python interpreter and virtual environment, so
    pytest_harness and its required dependencies must be installed there.

    """
    run_id = uuid4().hex
    exit_code = 1
    test_file_records: list[TestFileRecord] = []

    args = _resolve_harness_args(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        include_list=include_list,
        exclude_list=exclude_list,
        random_order=random_order,
        random_order_seed=random_order_seed,
        test_function_timeout=test_function_timeout,
        runner_log=runner_log,
        test_file_logs=test_file_logs,
        log_keep=log_keep,
        console_dashboard=console_dashboard,
        console_theme=console_theme,
        dashboard_width=dashboard_width,
        show_source_file_coverage=show_source_file_coverage,
        show_skipped_and_xfailed=show_skipped_and_xfailed,
        coverage_warning_threshold=coverage_warning_threshold,
        debug_harness=debug_harness,
    )

    resolved_random_order_seed = (
        (
            args.random_order_seed
            if args.random_order_seed is not None
            else randbelow(2_147_483_647) + 1
        )
        if args.random_order
        else None
    )

    _configure_log(args)

    try:
        theme = log.session_config.console_theme_dict
        output_dir_path = log.output_dir_path
        if output_dir_path is None:
            raise RuntimeError("PYTEST HARNESS INTERNAL ERROR: "
                               "Logduo did not create an output directory.")

        relative_test_file_paths = _resolve_test_file_paths(
            test_file_dir_path=args.test_file_dir,
            include_list=args.include_list,
            exclude_list=args.exclude_list,
        )
        test_file_count = len(relative_test_file_paths)
        print(
            f"Running {test_file_count} test files: ",
            end="",
            flush=True,
        )

        if args.debug_harness:
            print("\nDEBUG: --- List of test files pytest_harness will run ---")
            for index, relative_test_file_path in enumerate(relative_test_file_paths, start=1):
                print(f"    {index:>2}. {relative_test_file_path}")

        with tempfile.TemporaryDirectory(
            prefix="coverage_",
            dir=output_dir_path,
        ) as coverage_temp_dir_name:

            coverage_temp_dir_path = Path(coverage_temp_dir_name)
            coverage_config_file_path = coverage_temp_dir_path / "pytest_harness_coveragerc"
            coverage_config_file_path.write_text(
                "[run]\n"
                "branch = true\n"
                f"source = {args.tested_code_dir}\n"
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

            long_stem_warning_issued = False
            for relative_test_file_path in relative_test_file_paths:
                print(".", end="", flush=True)

                paths = _build_file_paths(
                    relative_test_file_path=relative_test_file_path,
                    test_file_dir=args.test_file_dir,
                    output_dir_path=output_dir_path,
                    coverage_temp_dir_path=coverage_temp_dir_path,
                )

                if paths.test_file_log_name_was_shortened and not long_stem_warning_issued:
                    log.warning(
                        "One or more test-file artifact names were shortened "
                        "to satisfy filename or filesystem path-length limits."
                    )
                    long_stem_warning_issued = True

                test_file_result = _build_test_file_record(
                    test_file_path=paths.test_file_path,
                    test_file_label=relative_test_file_path.as_posix(),  # str
                    test_file_log_path=paths.test_file_log_path,
                    tested_code_dir=args.tested_code_dir,
                    coverage_data_file_path=paths.coverage_data_file_path,
                    coverage_config_file_path=coverage_config_file_path,
                    progress_file_path=paths.progress_file_path,
                    test_file_logs=args.test_file_logs,
                    debug_harness=args.debug_harness,
                    random_order=args.random_order,
                    random_order_seed=resolved_random_order_seed,
                    test_function_timeout=args.test_function_timeout,
                    # extra_pytest_args=None,
                )
                test_file_records.append(test_file_result)

            combined_coverage_result = _combine_coverage_data_files(
                coverage_temp_dir_path=coverage_temp_dir_path,
                tested_code_dir=args.tested_code_dir,
            )

            print(" done", flush=True)
            print()

            # Finalize the flat function-level records now that every test file has run.
            # These records are used by both the dashboard and the returned RunResult.
            test_function_records = _finalize_test_function_records(test_file_records)

            summary_data = _build_summary_data(
                test_file_records=test_file_records,
                combined_coverage_result=combined_coverage_result,
                random_order_seed=resolved_random_order_seed,
                test_function_timeout=args.test_function_timeout,
                test_file_dir=args.test_file_dir,
                show_skipped_and_xfailed=args.show_skipped_and_xfailed,
                debug_harness=args.debug_harness,
            )

            summary_text = _build_dashboard(
                    summary_data=summary_data,
                    test_function_records=test_function_records,
                    coverage_warning_threshold=args.coverage_warning_threshold,
                    show_skipped_and_xfailed=args.show_skipped_and_xfailed,
                    show_source_file_coverage=args.show_source_file_coverage,
                    theme=theme,
                    dashboard_width=args.dashboard_width,

                )

            log(Text.from_markup(summary_text))

            run_failed = (
                summary_data.failed_test_function_count > 0
                or summary_data.error_test_function_count > 0
                or summary_data.xpassed_test_function_count > 0
                or summary_data.not_processed_test_file_count > 0
                or summary_data.no_tests_collected_test_file_count > 0
            )

            if not run_failed:
                exit_code = 0

    finally:
        styles = _build_summary_styles(log.session_config.console_theme_dict)

        exit_description = (
            "no test run errors detected"
            if exit_code == 0
            else "test run errors detected"
        )
        exit_style = (
            styles.success
            if exit_code == 0
            else styles.problem
        )
        exit_message = _styled(
            (
                f"Pytest Harness exit code: {exit_code} "
                f"({exit_description})"
            ),
            style=exit_style,
        )
        log("")
        log("")
        log(Text.from_markup(exit_message))
        log.close()

    return _build_run_result(
        run_id=run_id,
        pytest_harness_exit_code=exit_code,
        output_dir_path=output_dir_path,
        test_file_records=test_file_records,
        test_function_records=test_function_records,
        summary_data=summary_data,
    )


# === Internal helpers =========================================================
def _configure_log(
    args: ValidatedHarnessArgs,
) -> None:
    log.configure(
        log_file_mode="write",
        log_file_path=None,
        log_file_name=None,
        log_file_layout="run",
        log_dir_path=args.log_dir,
        keep=args.log_keep,

        console_verbosity=3 if args.console_dashboard else 0,
        console_prefix="off",
        console_wrap_width=args.dashboard_width,
        console_header=None,
        console_footer=None,
        # console_color="default",  # allow logduo TOML override for this one arg
        console_theme=args.console_theme,
        console_theme_dict=None,

        log_verbosity=3 if args.runner_log else 0,
        log_wrap_width=args.dashboard_width,
        log_prefix="off",
        log_header=None,
        log_footer=None,

        show_debug_source=False,
        show_logger_name=False,
        show_pid_in_console=False,
        write_config_table=False,
        write_config_json=False,
        write_jsonl=False,
        first_instance_owns_console=False,

        rotation="off",
        retention="off",
        compression="off",
        enqueue=True,
        catch=False,
        backtrace=False,
        diagnose=False
    )


# --- _finalize_test_function_records() ----------------------------------------
def _finalize_test_function_records(
    test_file_records: list[TestFileRecord],
) -> tuple[TestFunctionRecord, ...]:
    """
    Finalize function-level results for the complete pytest_harness run.

    test_order_id:
        Stable deterministic order based on alphabetically sorted full node IDs.

    run_order:
        Actual execution order across the complete harness run, based on
        progress-plugin START events. Tests that never started use 0.

    outcome:
        A collected test with no recorded outcome becomes "not_run".

    duration_seconds:
        Already recorded during per-file execution and preserved unchanged.
    """

    # --- Flatten all known test-function records ---
    test_function_records = [
        test_function_record
        for test_file_record in test_file_records
        for test_function_record in test_file_record.test_function_records
    ]

    # --- Assign stable test IDs ---
    for test_order_id, record in enumerate(
        sorted(
            test_function_records,
            key=lambda item: item.node_id.casefold(),
        ),
        start=1,
    ):
        record.test_order_id = test_order_id

    # --- Build actual whole-run execution order from START events ---
    started_node_ids = [
        node_id
        for test_file_record in test_file_records
        for node_id in test_file_record.started_test_function_node_ids
    ]

    run_order_by_node_id = {
        node_id: run_order
        for run_order, node_id in enumerate(
            started_node_ids,
            start=1,
        )
    }

    # --- Finalize run order and outcome ---
    for record in test_function_records:
        record.run_order = run_order_by_node_id.get(
            record.node_id,
            0,
        )

        if record.outcome is None:
            record.outcome = "not_run"

    return tuple(test_function_records)


# --- _build_run_result() ------------------------------------------------------
def _build_run_result(
    *,
    run_id: str,
    pytest_harness_exit_code: int,
    output_dir_path: Path,
    test_file_records: list[TestFileRecord],
    test_function_records: tuple[TestFunctionRecord, ...],
    summary_data: AggregateTestSummary,
) -> RunResult:

    return RunResult(
        run_id=run_id,
        pytest_harness_exit_code=pytest_harness_exit_code,
        output_dir_path=output_dir_path,
        random_order_seed=summary_data.random_order_seed,
        test_function_timeout_seconds=summary_data.test_function_timeout_seconds,
        test_file_count=summary_data.test_file_count,
        passed_test_file_count=summary_data.passed_test_file_count,
        failed_test_file_count=summary_data.failed_test_file_count,
        error_test_file_count=summary_data.error_test_file_count,
        skipped_test_file_count=summary_data.skipped_test_file_count,
        xfailed_test_file_count=summary_data.xfailed_test_file_count,
        xpassed_test_file_count=summary_data.xpassed_test_file_count,
        not_processed_test_file_count=summary_data.not_processed_test_file_count,
        no_tests_collected_test_file_count=summary_data.no_tests_collected_test_file_count,
        warning_test_file_count=summary_data.warning_test_file_count,
        warning_count=summary_data.warning_count,
        passed_test_function_count=summary_data.passed_test_function_count,
        failed_test_function_count=summary_data.failed_test_function_count,
        error_test_function_count=summary_data.error_test_function_count,
        skipped_test_function_count=summary_data.skipped_test_function_count,
        xfailed_test_function_count=summary_data.xfailed_test_function_count,
        xpassed_test_function_count=summary_data.xpassed_test_function_count,
        test_function_records=test_function_records,
        test_file_records=tuple(test_file_records),
        source_file_count=summary_data.source_file_count,
        executed_line_count=summary_data.executed_line_count,
        total_line_count=summary_data.total_line_count,
        executed_branch_count=summary_data.executed_branch_count,
        total_branch_count=summary_data.total_branch_count,
        statement_coverage_pct=summary_data.statement_coverage_pct,
        branch_coverage_pct=summary_data.branch_coverage_pct,
        total_coverage_pct=summary_data.total_coverage_pct,
        source_file_coverage_records=tuple(summary_data.source_file_coverage_records),
    )
