"""
pytest_harness.py

pytest_harness runs a complete pytest workflow from a Python runner script.

- runs each test file in isolation and continues when an individual file fails
- creates a console dashboard and summary log
- optionally creates detailed per-test-file logs with missing source lines
- presents aggregate coverage with optional per-test-file and per-source-file details

Last edited: 2026-08-03
"""

import tempfile
from pathlib import Path
from typing import NoReturn

from logduo import log
from rich.text import Text

from pytest_harness.arg_resolver import _resolve_harness_args
from pytest_harness.constants_and_classes import (
    DEFAULT_COVERAGE_WARNING_THRESHOLD,
    DEFAULT_WIDTH,
    TestFileRecord,
)
from pytest_harness.dashboard_builder import _build_dashboard
from pytest_harness.record_builder import _build_test_file_record
from pytest_harness.resolve_test_file_paths import _resolve_test_file_paths
from pytest_harness.summary_data_builder import _build_summary_data, _combine_coverage_data_files


# --- pytest_harness() ---------------------------------------------------------
def pytest_harness(
    *,
    test_file_dir: Path,
    log_dir: Path,
    tested_code_dir: Path,
    include_list: list[str | Path] | None = None,
    exclude_list: list[str | Path] | None = None,
    individual_logs: bool = True,
    coverage_warning_threshold: float | None = DEFAULT_COVERAGE_WARNING_THRESHOLD,
    show_source_file_coverage: bool = True,
    log_keep: int | None = None,
    console_theme: str = "dark",
    console_wrap_width: int = DEFAULT_WIDTH,
    show_skipped_and_xfailed: bool = False,
    debug_pytest_harness: bool = False,
) -> NoReturn:
    """
    Run a complete pytest workflow from a Python runner script.

    The runner script can be launched with one click from an IDE or run like
    any other Python script from Terminal. The pytest_harness call should be the final
    operation in the runner script because pytest_harness ends the process with SystemExit.

    pytest_harness runs each selected test file in an isolated subprocess.
    A crash, collection failure, or import failure in one test file therefore
    does not prevent later test files from running.

    After all selected files finish, pytest_harness combines coverage data and
    presents one console dashboard and summary log. It can also create a
    detailed individual log for each test file.

    Test environment
    ----------------
    pytest_harness uses consistent pytest, coverage, import, and plugin settings
    for each isolated test-file run.

    These settings apply only while pytest_harness is running. They do not change
    your project files, IDE settings, or Python environment.


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

        pytest_harness(
            test_file_dir=PROJECT_DIR / "tests",
            log_dir=PROJECT_DIR / "tests" / "logs",
            tested_code_dir=PROJECT_DIR / "src" / "sample_package",
            log_keep=3,
        )

    In ``test_calculator.py`` (start imports from last directory in tested_code_dir):

        from sample_package.calculator import add

        def test_add() -> None:
            assert add(4, 7) == 11


    Arguments
    ---------
    Paths (required):
        test_file_dir : Path
            Directory containing the pytest test files.

            pytest_harness discovers files recursively using pytest-style names
            such as ``test_*.py``.

        log_dir : Path
            Directory where pytest_harness creates time-stamped run directories.

            Each run directory contains the main summary log and, when
            individual_logs is True, one detailed log for each test file.

        tested_code_dir : Path
            Dedicated directory containing the Python code tested by the selected
            test files.

            pytest_harness measures coverage only within this directory and makes
            its parent directory available for imports during each pytest
            subprocess.

            Test imports should begin with the name of tested_code_dir.

            For example, if:

                tested_code_dir = PROJECT_DIR / "src" / "sample_package"

            and the directory contains:

                sample_package/
                    __init__.py
                    calculator.py

            a test file can import ``add`` with:

                from sample_package.calculator import add

            tested_code_dir should normally contain only the package or source-code
            files that should be included in coverage results.

    Test file selection (optional)
        include_list : list[str | Path] | None
            Run only the specified test files or directories.

            Entries may be file names, relative paths, absolute paths, or
            directories. Relative paths are resolved from test_file_dir.

            None runs all discovered test files except those removed by
            exclude_list.

        exclude_list : list[str | Path] | None
            Exclude the specified test files or directories.

            Entries may be file names, relative paths, absolute paths, or
            directories. Relative paths are resolved from test_file_dir.

            None excludes nothing.

    Output (optional):
        individual_logs : bool
            Create a detailed log for each test file.

            Individual logs include pytest output, printed diagnostic values,
            failures, tracebacks, coverage details, the pytest exit code, and run
            duration.

            Default is True.

        log_keep : int | None
            Number of recent pytest_harness run directories to retain.

            Older run directories are pruned after a new run starts.
            None retains all run directories.

        console_theme : str
            Console color theme.

            Supported values are:

                "dark"
                "light"

            Default is "dark".

        console_wrap_width : int
            Width used for console output and the summary dashboard.

            Default is 150.

        show_skipped_and_xfailed : bool
            Include detailed Skipped and XFailed test entries in the dashboard.

            Failed, Error, and XPassed entries are always shown.

            Default is False.

        debug_pytest_harness : bool
            Display internal diagnostic details, including the exact selected test
            files and captured output for failed test-file subprocesses.

            Default is False.


    Coverage (optional):
        coverage_warning_threshold : float | None
            Coverage percentage below which a warning is shown.

            This affects dashboard warnings only. It does not change the process
            exit code.

            None disables coverage warnings.

        show_source_file_coverage : bool
            Include the per-source-file coverage table in the dashboard.

            Default is True.


    Exit behavior
    -------------
    pytest_harness raises:

        SystemExit(0)
            The complete run succeeded.

        SystemExit(1)
            At least one test failed or unexpectedly passed, or at least one
            test file could not be processed or collected no tests.

    Skipped and XFailed tests do not cause a failed run.


    Advanced environment behavior
    -----------------------------
    pytest_harness ignores project-level pytest ``addopts`` and disables automatic
    loading of unrelated third-party pytest plugins. It explicitly loads the
    plugins required for coverage, JSON reporting, and rerun control.

    For each pytest subprocess, the parent of tested_code_dir is supplied as the
    temporary pytest pythonpath. This allows test files to import the tested-code
    directory by name.

    pytest_harness does not modify the caller's sys.path, environment variables,
    IDE settings, pyproject.toml, pytest.ini, or other project files.

    The subprocesses still use the active Python interpreter and virtual
    environment, so pytest_harness and its required dependencies must be installed
    there.

    """

    runner_results: list[TestFileRecord] = []

    args = _resolve_harness_args(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        include_list=include_list,
        exclude_list=exclude_list,
        coverage_warning_threshold=coverage_warning_threshold,
        individual_logs=individual_logs,
        show_source_file_coverage=show_source_file_coverage,
        log_keep=log_keep,
        console_theme=console_theme,
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
        console_theme=args.console_theme,
        console_prefix="off",
        console_wrap_width=args.console_wrap_width,
        log_prefix="off",
    )
    theme = log.session_config.console_theme_dict

    try:
        output_dir_path = log.output_dir_path
        if output_dir_path is None:
            raise RuntimeError("Logduo did not create an output directory.")

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
            tested_code_dir_path = Path(coverage_temp_dir_name)
            coverage_config_file_path = (
                tested_code_dir_path / "pytest_harness_coveragerc"
            )

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

            for relative_test_file_path in relative_test_file_paths:
                print(".", end="", flush=True)

                test_file_path = args.test_file_dir / relative_test_file_path

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
                    tested_code_dir_path / f".coverage.{test_file_safe_stem}"
                )

                test_file_result = _build_test_file_record(
                    test_file_path=test_file_path,
                    test_file_log_path=test_file_log_path,
                    tested_code_dir=args.tested_code_dir,
                    coverage_data_file_path=coverage_data_file_path,
                    # extra_pytest_args=["-q"],    # "-q" already called, extra_pytest_args[] reserved for future args
                    coverage_config_file_path=coverage_config_file_path,
                    individual_logs=args.individual_logs,
                    debug_pytest_harness=args.debug_pytest_harness,
                )

                runner_results.append(test_file_result)

            combined_coverage_result = _combine_coverage_data_files(
                tested_code_dir_path=tested_code_dir_path,
                tested_code_dir=args.tested_code_dir,
            )

            print(" done", flush=True)
            print()

            summary_data = _build_summary_data(
                pytest_test_file_records=runner_results,
                combined_coverage_result=combined_coverage_result,
                show_skipped_and_xfailed=args.show_skipped_and_xfailed,
                debug_pytest_harness=args.debug_pytest_harness,
            )

            summary_text = _build_dashboard(
                summary_data=summary_data,
                coverage_warning_threshold=args.coverage_warning_threshold,
                show_skipped_and_xfailed=args.show_skipped_and_xfailed,
                show_source_file_coverage=args.show_source_file_coverage,
                theme=theme,
            )

            log(Text.from_markup(summary_text))

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
