pytest_harness
==============

Purpose
-------
pytest_harness is a one-click pytest runner for IDE-centered workflows.

It handles pytest, coverage, subprocess isolation, logs, and summary reporting
so test runs are easier to start and easier to interpret.

Why use pytest_harness?
-----------------------
- one-click test execution from an IDE
- readable per-test-file logs where printed diagnostics are easy to find
- dedicated test-file coverage reports showing missing source lines (helpful for writing new tests)
- no command-line flags
- remaining test files still run when one file crashes
- explicit reporting of import errors, collection failures, and files with no collected tests
- one compact dashboard for the complete run, including combined coverage

pytest_harness is a workflow tool, not a pytest plugin.


Quick Start
-----------
Create a runner script in your project:

    from pathlib import Path

    from pytest_harness import pytest_harness

    PROJECT_ROOT = Path(__file__).resolve().parent

    pytest_harness(
        test_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "logs",
        source_dir=PROJECT_ROOT / "src" / "my_package",
    )

In PyCharm, right-click the runner script and run it.

pytest_harness will:

1. discover test files
2. run each test file in an isolated subprocess
3. collect statement and branch coverage
4. combine coverage across all test files
5. write the requested logs
6. print a compact dashboard
7. exit with code 0 or 1


Public API
----------
Main entry point:

    pytest_harness(
        *,
        test_dir: Path,
        log_dir: Path,
        source_dir: Path,
        include_list: list[str | Path] | None = None,
        exclude_list: list[str | Path] | None = None,
        individual_logs: bool = True,
        coverage_warning_threshold: float | None = 85.0,
        show_source_file_coverage: bool = True,
        show_skipped_and_xfailed: bool = False,
        log_keep: int | None = None,
        console_wrap_width: int = 150,
        debug_pytest_harness: bool = False,
    ) -> int


Arguments
---------

`test_dir`
    Directory containing pytest test files.

    Must be a pathlib.Path, must exist, and must be a directory.

`log_dir`
    Directory where pytest_harness writes run logs.

    Must be a pathlib.Path. If the directory does not exist, pytest_harness
    creates it after all arguments have been validated.

`source_dir`
    Source directory measured for coverage.

    Must be a pathlib.Path, must exist, and must be a directory.

`include_list`
    Optional list of test files or test directories to run.

    Entries may be strings or pathlib.Path objects.

    Use None to discover all matching test files.

`exclude_list`
    Optional list of test files or test directories to exclude.

    Exclusions are applied after normal discovery or include-list selection.

`individual_logs`
    If True, writes a detailed log for each selected test file.

    Default:

        True

`coverage_warning_threshold`
    Optional total-coverage warning threshold from 0 through 100.

    The dashboard displays a warning when rounded total coverage is below the
    rounded threshold.

    Use None to disable the warning.

    Default:

        85.0

`show_source_file_coverage`
    If True, displays statement coverage for each covered source file.

    Source files are sorted from lowest to highest statement coverage.

    Default:

        True

`show_skipped_and_xfailed`
    Controls whether Skipped and XFailed test functions appear in the detailed
    flagged-test section.

    When False, the detailed section includes:

    - Failed
    - Error
    - XPassed

    When True, it also includes:

    - Skipped
    - XFailed

    Aggregate outcome counts always include Skipped and XFailed regardless of
    this setting.

    Default:

        False

`log_keep`
    Optional number of recent pytest_harness run directories to retain.

    Use None to disable automatic pruning.

    When supplied, the value must be an integer of at least 1.

    Default:

        None

`console_wrap_width`
    Console wrapping width used by Logduo.

    Must be an integer of at least 80.

    Default:

        150

`debug_pytest_harness`
    If True, prints additional pytest_harness diagnostic information,
    including the exact selected test files and official combined Coverage.py
    counts.

    Default:

        False


Expanded Example
----------------
A runner may specify every public option:

    from pathlib import Path

    from pytest_harness import pytest_harness

    PROJECT_ROOT = Path(__file__).resolve().parent

    pytest_harness(
        test_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "logs",
        source_dir=PROJECT_ROOT / "src" / "my_package",
        include_list=None,
        exclude_list=None,
        individual_logs=True,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=True,
        show_skipped_and_xfailed=False,
        log_keep=10,
        console_wrap_width=150,
        debug_pytest_harness=False,
    )


Exit Codes
----------
pytest_harness exits with:

    0    the complete selected test run succeeded
    1    the complete selected test run did not succeed

The run exits with code 1 when any of the following occurs:

- one or more test functions Failed
- one or more test functions produced Error
- one or more tests XPassed
- one or more selected test files could not be processed
- one or more selected test files collected no tests

Skipped and XFailed outcomes do not by themselves cause exit code 1.

A test file that cannot be imported or collected may contain no failed
individual test function. It still causes the complete run to fail because
that file was not successfully validated.

Likewise, a selected file that collects no tests causes the run to fail because
pytest_harness cannot confirm that the file performed its intended testing.

How It Works
------------
pytest_harness runs each selected pytest test file in its own subprocess,
collects the results, combines coverage, prints a final dashboard, and exits
with a standard process result code.

A broken test file does not stop the remaining files from running. Import
errors, collection failures, and files with no collected tests are reported
separately. When `individual_logs=True`, each test file also receives a detailed
log containing its pytest output and Coverage.py missing-line information.
pytest_harness uses Logduo for logging and output management, but ordinary test
files do not need to configure or import Logduo.


Dashboard
---------
The dashboard is divided into four sections:

- test-file summary
- test-function summary
- aggregate coverage
- optional source-file coverage table

Example:

    ════════════════════════════════════════════════════════════
                            TEST SUMMARY
    ════════════════════════════════════════════════════════════

    Test file summary
    ------------------------------------------------------------
    Source files covered:         8
    Test files run:               9
    Test files passed all tests:  7

    Test files not processed, often due to import error (1):
        test_import_error.py

    Test files with no collected tests (1):
        test_empty.py


    Test function summary
    ------------------------------------------------------------
        Passed:   103
        Failed:     0
        Error:      0
        XPassed:    0
        Skipped:    0
        XFailed:    0

    Coverage
    ------------------------------------------------------------
        Statements:   97%
        Branches:     96%
        Total:        97%


    Source
    file      Executed/
    Coverage  Statements  Source file
    --------  ----------  -------------------------
    92%       165/180     constants_and_classes.py
    98%       79/81       arg_resolver.py
    99%       99/100      summary_data_builder.py
    100%      52/52       pytest_harness.py


Test-File Summary
-----------------
The test-file summary reports:

- number of source files included in coverage
- number of selected test files
- number of test files that passed every collected test
- files that were not processed
- files that collected no tests

A file is counted as having passed all tests only when:

- it was successfully processed
- it collected at least one test
- every collected test passed

A file containing only Skipped or XFailed tests is not counted as having passed
all tests.


Test-Function Summary
---------------------
The test-function summary displays aggregate pytest outcomes:

- Passed
- Failed
- Error
- XPassed
- Skipped
- XFailed

These counts are shown regardless of the `show_skipped_and_xfailed` setting.


Flagged Test Functions
----------------------
When relevant outcomes are present, pytest_harness adds a detailed section
grouped by test file.

By default, the section shows:

- Failed
- Error
- XPassed

Example:

    Flagged test functions by test file (in 1 test file):

    test_example.py

        Failed (1):
            test_invalid_value

Set:

    show_skipped_and_xfailed=True

to include Skipped and XFailed test functions in this detailed section as well.


Source-File Coverage
--------------------
When:

    show_source_file_coverage=True

pytest_harness displays a source-file coverage table.

The table includes:

- rounded statement coverage percentage
- executed statement count
- total statement count
- source filename

Files are sorted from lowest to highest statement coverage so the files most
likely to need attention appear first.

Source files containing no executable statements are omitted from the table.

Set:

    show_source_file_coverage=False

to hide the table. Aggregate Statements, Branches, and Total coverage remain
visible.


Runner Script Guidelines
------------------------
The runner script should contain project paths and test-runner settings.

Typical responsibilities:

- define test_dir
- define log_dir
- define source_dir
- optionally define include_list
- optionally define exclude_list
- select reporting options
- call pytest_harness()

The runner script is normally the file run directly from the IDE.


Test File Guidelines
--------------------
Individual test files should contain tests only.

Recommended practices:

- Do not configure pytest_harness inside individual test files.
- Do not configure Logduo solely for pytest_harness output.
- Use print() when diagnostic output should appear in an individual test log.
- Use tmp_path when tests create temporary files or directories.
- Keep tests independent.
- Do not rely on test execution order.


Test Selection
--------------
pytest_harness discovers and runs pytest test files under `test_dir`.

Default behavior:

    include_list = None
    exclude_list = None

This recursively discovers files matching:

    test_*.py

Example test tree:

    tests/
        test_config.py
        unit/
            test_paths.py
        integration/
            test_run.py

Selected paths are tracked relative to `test_dir`:

    test_config.py
    unit/test_paths.py
    integration/test_run.py


include_list and exclude_list
-----------------------------
`include_list` selects specific test files or test directories.

`exclude_list` removes specific test files or test directories after discovery
or include-list resolution.

Examples:

    include_list = ["test_config"]
    include_list = ["test_config.py"]
    include_list = ["unit"]
    include_list = ["unit/"]
    include_list = ["unit/test_paths"]
    include_list = ["unit/test_paths.py"]

    exclude_list = ["test_make_real_logs"]
    exclude_list = ["integration/slow_tests"]

Selector rules:

1. If a selector ends with `.py`, it is treated as a file path.
   The file must exist.

2. If a selector does not end with `.py`:

   - if only `selector.py` exists, that file is selected
   - if only `selector/` exists, that directory is expanded recursively
   - if both exist, the directory is used and a warning is printed
   - if neither exists, pytest_harness raises an error

To force file selection, include `.py`:

    unit/test_paths.py

To force directory selection, use a directory path:

    unit/test_paths/


Coverage
--------
pytest_harness generates a temporary Coverage.py configuration for each run.

It does not use coverage settings from `pyproject.toml`.

The generated configuration includes:

- branch coverage
- source selection from `source_dir`
- parallel coverage data files
- multiprocessing support
- subprocess coverage patching
- skipped empty files in reports
- missing-line reporting
- precision = 2

Absolute source paths are used internally when coverage from isolated
subprocesses is combined.

Each selected test file runs in its own subprocess and writes its own temporary
Coverage.py data file.

Python subprocesses started by those tests are also included when they inherit
the test process environment.

After all selected test files finish:

- Coverage.py combines the per-file coverage data
- Coverage.py generates the official aggregate counts
- pytest_harness builds its source-file records
- temporary coverage files are deleted

Coverage combination has been validated by comparing:

- three isolated test files with separately collected coverage
- one large test file containing the same tests

The resulting statement counts, branch counts, executed lines, missing lines,
executed branch pairs, and total branch pairs matched.


Logs
----
pytest_harness writes one primary log for the complete run.

When:

    individual_logs=True

it also writes one log for each selected test file.

Nested test paths are flattened while retaining their identity.

For example:

    tests/unit/test_paths.py

may produce:

    unit__test_paths.log

Output written with print() inside a test file is captured in that test file's
individual log.


Examples
--------
A complete runnable example project is available under:

    examples/basic_project/

It contains:

    examples/basic_project/
        run_tests.py
        src/
            sample_package/
                __init__.py
                calculator.py
        tests/
            test_calculator.py
            test_validation.py

Run:

    examples/basic_project/run_tests.py

from an IDE to see the normal pytest_harness workflow.
