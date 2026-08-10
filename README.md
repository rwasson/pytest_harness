pytest_harness
==============

An easy-to-use Python testing workflow orchestrator built around pytest.

Set the project paths and call `pytest_harness()` in a small runner script.
pytest_harness automatically manages isolated test execution, combined coverage,
dashboard output, summary logging, and optional per-test-file logs.

The runner script can be launched with one click from an IDE or run like any
other Python script from Terminal.


Why use pytest_harness?
-----------------------
- no command-line flags, `pyproject.toml`, coverage settings, or logging setup required
- compact color-coded dashboard and plain-text log that report:
    - test file progress
    - summary of test results
    - list of test files with processing errors and warnings
    - randomization seed, timeout limit, and slow test functions (if any)
    - combined coverage with optional coverage for each source file
    - output directory and names of created log files
- test files run independently; if one test file crashes or fails during import,
  collection, or execution, pytest_harness records the problem and continues to the next test file
- optional per-test-file logs containing pytest results, warnings, and `print()` output
    - support visual inspection of test and function outputs for debugging
    - display missing (uncovered) source lines
    - can serve as lightweight documentation of tested behavior and passing status
- detailed docstring with complete argument list:  

        from pytest_harness import pytest_harness

        help(pytest_harness)

pytest_harness is a workflow orchestrator, not a pytest plugin.

    
Quick Start: Example runner
--------------------------
    """
    pytest_harness_runner.py
    """
    import sys
    from dataclasses import fields
    from pathlib import Path

    from pytest_harness import pytest_harness
    
    # --- Path settings ---
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    
    # pytest_harness creates the dashboard and logs automatically.
    # The returned results are optional and support additional analysis.
    results = pytest_harness(
        test_file_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "tests" / "logs",
        tested_code_dir=PROJECT_ROOT / "src" / "sample_package",
        log_keep=3,
        dashboard_width=80,
        console_theme="light",
        random_order=True,
        test_function_timeout=2,
        show_skipped_and_xfailed=True,
    )

    # --- Inspect returned results --- 
    print("\nFields in results")
    print("-----------------")
    for field in fields(results):
        print(field.name)
    
    # test_function_records is useful for repeated-run and flaky-test analysis
    print("\nFirst 3 results.test_function_records")
    print("-------------------------------------")
    for record in results.test_function_records[:3]:
        print(f"{record}\n")

    # --- Exit with pytest_harness_exit code if any test problems ---
    if results.pytest_harness_exit_code != 0:
        sys.exit(results.pytest_harness_exit_code)


Example console output
----------------------
Console output is color-coded (logs are plain text).

    Running 7 test files: ....... done
    
    Pytest Harness Summary
    ════════════════════════════════════════
    Random-order seed: 1002631522
    Test-function timeout (in seconds): 2.0
    
    
    Test file summary
    ----------------------------------------
    Source files covered:         2
    Test files run:               7
    Test files passed all tests:  4
    
    Test files not processed successfully (1):
        Test function timed out (1):
            test_timeout.py
                    in: test_02_exceeds_test_function_timeout
    
    Test files with no collected tests (1):
        test_empty.py
    
    Test files with warnings (details in individual test-file logs) (1):
        unit_tests/test_intentional_warning.py (1 warning)

    Test function summary
    ----------------------------------------
        Passed:     25
        Failed:      1
        Error:       1
        XPassed:     1
        Skipped:     1
        XFailed:     1
    
    Flagged test functions (in 1 test file):
        unit_tests/test_flagged.py
            Failed (1):
                test_03_intentional_fail
            Error (1):
                test_06_intentional_error_during_setup
            XPassed (1):
                test_05_intentional_unexpected_pass
            Skipped (1):
                test_02_intentional_skip
            XFailed (1):
                test_04_intentional_expected_failure

    Total coverage
    ----------------------------------------
        Statements:   83%
        Branches:     58%
        Total:        76%
    
    WARNING: Total coverage (76%) is below recommended threshold 85%.
    
    Source file   Executed/    Source
    coverage      statements   file
    ------------  -----------  --------------
    55%           6/11         calculator.py
    100%          19/19        helpers/arithmetic_functions.py

    Slowest test functions
    ----------------------------------------
    0.51 s  examples/basic_project/tests/unit_tests/test_flagged.py::test_07_slow_
                test
    
    
    Pytest Harness exit code: 1 (test run errors detected)
    ───────────────────────────────────────────────────────
    Pruned run dirs:  1
    Logging ended:    2026-08-08 10:12:13 (duration 04 sec)
    Script path:
        /Users/<my_name>/basic_project/tests/pytest_harness_runner.py
    Output directory:
        /Users/<my_name>/basic_project/tests/logs/pytest_harness_runner/run_2026_08_08_
            _10_12_09
    Log-generated files in output directory:
        pytest_harness_runner.log
        test_calculator.log
        ...


Arguments
---------
- **test_file_dir**: `pathlib.Path`  
   Existing directory containing pytest test files.

- **log_dir**: `pathlib.Path`  
    Directory where pytest_harness creates run logs. The directory is created
    if it does not already exist.

- **tested_code_dir**: `pathlib.Path`  
    Existing dedicated directory containing the code targeted by the tests and
    measured for coverage. Its parent is used for imports in each pytest
    subprocess.

- **include_list**: `list[str | pathlib.Path] | None`  
    Optional test files or directories to run. Default is None, which discovers
    all matching test files under `test_file_dir`.

- **exclude_list**: `list[str | pathlib.Path] | None`  
    Optional test files or directories to exclude after discovery or inclusion.
    Default is None.

- **random_order**: `bool`  
    Randomize test-function execution order. Default is False.

- **random_order_seed**: `int | None`  
    Seed used when `random_order=True`. If None, pytest_harness generates and
    reports a seed so the test order can be reproduced. Default is None.

- **test_function_timeout**: `int | float | None`  
    Maximum execution time in seconds for an individual test function.
    Use None to disable the timeout. Default is 200.

- **runner_log**: `bool`  
    Write the main pytest_harness summary log. Default is True.

- **test_file_logs**: `bool`  
    Write one detailed log for each selected test file. Default is True.

- **console_dashboard**: `bool`  
    Display the summary dashboard in the console. Default is True.

- **coverage_warning_threshold**: `float | None`  
    Warn when total coverage is below this percentage. This does not affect the
    process exit code. Default is 85.0. Use 0 or None to disable the warning.

- **show_source_file_coverage**: `bool`  
    Display the source-file coverage table. Default is True.

- **show_skipped_and_xfailed**: `bool`  
    Include Skipped and XFailed outcomes in flagged-test section. Default is False.

- **log_keep**: `int | None`  
    Number of recent marked run directories to retain. Default is None, which
    disables pruning.

- **console_theme**: `str`  
    Console color theme: `"dark"` or `"light"`. Default is `"dark"`.

- **dashboard_width**: `int`  
    Width used for the console and log dashboard. Must be at least 80.
    Default is 150.

- **debug_harness**: `bool`  
    Display additional internal diagnostics, including selected test files and
    captured output from flagged test-file subprocesses. Default is False.

Return value
------------
`pytest_harness()` returns structured run, test-file, test-function, and coverage
results for optional programmatic analysis.
The dashboard and logs are generated automatically; using the returned results
is not required.

For complete validation rules and documentation:

    from pytest_harness import pytest_harness
    help(pytest_harness)


Pytest Harness Exit Codes
-------------------------
pytest_harness displays an exit code and includes it in the returned results:

    0    no test run errors detected
    1    test run errors detected

Any of the following produce `pytest_harness_exit_code = 1`:
- one or more test functions Failed
- one or more test functions produced Error
- one or more tests XPassed
- one or more selected test files could not be processed
- one or more selected test files collected no tests

Note:
- Skipped and XFailed outcomes do not by themselves cause exit code 1.
- They also do not trigger tests being listed under `Flagged test functions` 
  unless `show_skipped_and_xfailed=True` (default = False)


Tips
----
- Runner for pytest_harness(): suggested name is `pytest_harness_runner.py`
  - Place pytest_harness_runner.py in your project's test directory.
  - Place test_helper files in a subdirectory inside your project's test directory.
  - pytest_harness uses Logduo internally for its own console output and test-run
    logs. Do not add separate logging setup for the runner or for
    pytest_harness-generated test-file logs. 
  - If desired, set up logging in your runner after calling pytest_harness().
  - Give your runner script a name that does not start with
    `test_` or end with `_test.py`. PyCharm may treat those names as pytest test
    files rather than as executable runner scripts (right-click won't work).

- Test files:
  - Test file names must match `test_*.py` or `*_test.py`.
  - Test function names must begin with `test_`.
  - Suggestion: give test functions names that are descriptive and include a 
    numeric component to make it easier to quickly find and edit flagged tests, 
    (e.g., `test_01_verify_add_calculation_and_output_to_console_and_log`).
  - Keep test functions independent and do not rely on test function execution order.
  - Use pytest's `tmp_path` fixture when tests create temporary files or directories 
    (see example test file below).
  - `print()` statements inside a test file are captured in the test file's 
    individual log and can be used to verify the tested code is executing as intended.
  - Test functions may configure and inspect Logduo logging via Duo() when logging 
    behavior is part of what the test verifies (see example test file below).

    
Example test file
-----------------
    """
    test_calculator.py

    When debugging a failing test,
    place diagnostic print statements before the assertion being investigated.
    Execution of that test function stops when an assertion fails.
    """
    from pathlib import Path

    import pytest
    from logduo import Duo
    from sample_package.calculator import calculation_report
    from sample_package.helpers.arithmetic_functions import add

    def test_01_verify_add_calculation_and_output_to_console_and_log(
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:

        assert add(4, 7) == 11
    
        # Duo() creates an isolated Logduo instance local to this test function.
        # log.close() closes its logging session.
        # pytest provides the tmp_path directory and removes it after the test run.
        log_dir_path = str(tmp_path / "logs")
        log = Duo()
        log.configure(log_dir_path=log_dir_path, console_prefix="off")
    
        log("Passed assert statement: assert add(4, 7) == 11")
        log('Show: calculation_report("add",4,7)')
        log(f'    {calculation_report("add", 4, 7)}')
        
        log_file_path = log.main_log_file_path  # must assign before log.close()
        log.close()
    
        captured = capsys.readouterr()
        console_output = captured.out + captured.err
        
        assert log_file_path is not None
        log_content = log_file_path.read_text(encoding="utf-8")
    
        assert "Calculation report" in console_output
        assert "Calculation report" in log_content
    
        print("")
        print("--- test_01_verify_add_calculation_and_output_to_console_and_log ---")
        print("Passed assert statements that expected strings are in console and log.")
    
        print("\n--- CAPTURED CONSOLE OUTPUT FOR VISUAL INSPECTION ---")
        print(console_output.rstrip())
        print("\n--- LOG CONTENT FOR VISUAL INSPECTION ---")
        print(log_content.rstrip())
       

Example test-file log 
----------------------
Excerpt from `test_calculator.log`:

    test_01_verify_add_calculation_and_output_to_console_and_log
    Passed assert statements: confirmed expected strings in console and log.

    --- CAPTURED CONSOLE OUTPUT FOR VISUAL INSPECTION ---
    Logging started:  2026-08-06 10:03:16
    Passed assert statement: assert add(4, 7) == 11
    ...

    --- LOG CONTENT FOR VISUAL INSPECTION ---
    10:03:16.919 | INFO     | Passed assert statement: assert add(4, 7) == 11
    ...

    ================================ tests coverage ================================
    Name                               Stmts   Miss Branch BrPart   Cover   Missing
    -------------------------------------------------------------------------------
    src/sample_package/calculator.py      22     10      6      2  50.00%   21, 50, 68, 86-96
    -------------------------------------------------------------------------------
    TOTAL                                 24     10      6      2  53.33%
    PASSED tests/test_calculator.py::test_01_verify_add_calculation_and_output_to_console_and_log
    pytest exit code: 0
    duration: 0.42 seconds

- The individual test-file logs include warnings and detailed tracebacks for 
  failed tests if relevant.
- The `TOTAL` coverage of 53.33% applies to this test file only. Other test files 
  boosted total coverage to 76%.
- The `Missing` source lines can help target code that needs additional tests.
- A complete basic project is available in the GitHub repository under

    `examples/basic_project/`.
