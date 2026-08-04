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
- no command-line flags, `pyproject.toml` coverage settings, or logging setup required
- test files run independently; if one test file crashes or fails during import,
  collection, or execution, pytest_harness continues to the next test file
- compact color-coded dashboard and plain-text log for the complete run:
    - summary of test results 
    - list of files with import or test collection errors
    - combined coverage
    - optional coverage for each source file
    - output directory and names of created log files
    - exit code
- optional per-test-file logs containing pytest results and output from `print()` statements
    - support visual inspection of test and function outputs
    - display missing (uncovered) source lines
    - can serve as lightweight documentation of tested behavior and passing status
- detailed docstring with complete argument list:  

        from pytest_harness import pytest_harness

        help(pytest_harness)


pytest_harness is a workflow orchestrator, not a pytest plugin.


Tips
----
- pytest_harness_runner:
  - Place pytest_harness_runner.py in your project's test directory.
  - Place test_helper files in a subdirectory inside your project's test directory.
  - pytest_harness uses Logduo internally for its own console output and test-run
    logs. Do not add separate logging setup for the runner or for
    pytest_harness-generated test-file logs.
  - Give your runner script a name that does not start with
    `test_` or end with `_test.py`. PyCharm may treat those names as pytest test
    files rather than as executable runner scripts (right-click won't work).

- test files:
  - Test file names should match `test_*.py`.
  - Test functions may configure and inspect Logduo logging via Duo() when logging behavior
    is part of what the test verifies (see example test below).
  - `print()` statements inside test functions are captured in the test file's individual log and 
     can be used to verify the tested code is executing as intended.
  - `print()` statements outside test functions are not included in the console,
    the summary log, or the test file's individual log.
  - Use pytest's `tmp_path` fixture when tests create temporary files or directories 
    (see example test below).
  - Keep test functions independent and do not rely on test function execution order.
  - Recommendations: 
    - Give test functions descriptive names that include a numeric component
    (e.g., `test_01_verify_add_calculation_and_output_to_console_and_log`).
    - Ordered numeric components make it easier to find and edit flagged tests.

  
Example runner
--------------
    """
    pytest_harness_runner.py

    Run from PyCharm: Right-click on `pytest_harness_runner.py` and select Run.
    Run from Terminal (in tests' directory): `python pytest_harness_runner.py`
    """

    from pathlib import Path

    from pytest_harness import pytest_harness

    # --- Path settings ---
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


    def main() -> None:
        pytest_harness(
            test_file_dir=PROJECT_ROOT / "tests",                 
            log_dir=PROJECT_ROOT / "tests" / "logs",              
            tested_code_dir=PROJECT_ROOT / "src" / "my_project",  
            log_keep=3,                                           
        )


    if __name__ == "__main__":
        main()


* IMPORTANT: `tested_code_dir` identifies the dedicated code directory used
for test imports and coverage analysis.

For example, if `tested_code_dir = PROJECT_ROOT / "src" / "sample_package"`
and the `sample_package` directory contains `calculator.py` (and the recommended empty `__init__.py`),
then the function `add` can be imported from `test_calculator.py` as shown below. 


Example test file (excerpt)
---------------------------
    """
    test_calculator.py
    """
    from pathlib import Path

    import pytest
    from logduo import Duo

    from sample_package.calculator import add

    def test_01_verify_add_calculation_and_output_to_console_and_log(
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:

        result = add(4, 7)
        assert result == 11

        message = f"add(4, 7) returned {result:g}"

        log_dir_path = str(tmp_path / "logs")

        # pytest manages and later removes the temporary directory log_dir_path.
        # Duo() creates an isolated Logduo logger for this test.
        log = Duo()
        log.configure(log_dir_path=log_dir_path)

        log(message)
 
        log_file_path = log.main_log_file_path
        assert log_file_path is not None
    
        log.close()
    
        captured = capsys.readouterr()
        console_output = captured.out + captured.err
        log_content = log_file_path.read_text(encoding="utf-8")
    
        assert message in console_output
        assert message in log_content

        print("test_01_verify_add_calculation_and_output_to_console_and_log")
        print(f"Passed add() assert statement: confirmed add(4, 7) returns expected result = {result}.")
        print("Passed output assert statements: confirmed that expected messages are in console and log.")
        print("\n--- CAPTURED CONSOLE OUTPUT FOR VISUAL INSPECTION ---")
        print(console_output.rstrip())
        print("\n--- LOG CONTENT FOR VISUAL INSPECTION ---")
        print(log_content.rstrip())
        print("")
        print("--- End of test_01 ---")


Example console output
----------------------
- Console output is color-coded (logs are plain text).

    Logging started:  2026-08-03 16:41:48
    Running script:   pytest_harness_runner.py
    pruned run directories: 1 (keep=3)  

    Running 5 test files: ..... done

    Pytest Harness Summary
    ═════════════════════════════════════
    
    Test file summary
    -------------------------------------
    Source files covered:         2
    Test files run:               5
    Test files passed all tests:  2
    
    Test files not processed (check imports) (1):
        test_import_error.py
    
    Test files with no collected tests (1):
        test_empty.py
    
    
    Test function summary
    -------------------------------------
        Passed:     22
        Failed:      1
        Error:       1
        XPassed:     1
        Skipped:     1
        XFailed:     1
    
    Flagged test functions (in 1 test file):
        test_flagged.py
            Failed (1):
                test_03_intentional_fail
            Error (1):
                test_06_intentional_error_during_setup
            XPassed (1):
                test_05_intentional_unexpected_pass
    
    
    Total coverage
    -------------------------------------
    Statements:   96%
    Branches:    100%
    Total:        97%


    Source file  Executed/    Source
    coverage     statements   file
    -----------  -----------  -----------
    95%          21/22        calculator.py
    100%         2/2          __init__.py
    ──────────────────────────────────────────────────────
    Logging ended:    2026-08-03 16:41:48 (duration 00 sec)
    Script path:
        /Users/<my_name>/basic_project/tests/pytest_harness_runner.py
    Output directory:
        /Users/<my_name>/basic_project/tests/logs/pytest_harness_runner/run_2026_08_03__16_41_48
    Log-generated files in output directory:
        pytest_harness_runner.log
        test_calculator.log
        test_empty.log
        test_flagged.log
        test_import_error.log
        test_validation.log
    
    Process finished with exit code 1


Example individual log file (excerpt from test_calculator.log)
--------------------------------------------------------------
    ───────────────────────────────────────────────────────
    test_calculator.log
    Logging started:  2026-08-04 10:03:16
    Generated by:     pytest_harness_runner.py
    ───────────────────────────────────────────────────────

    test_01_verify_add_calculation_and_output_to_console_and_log
    Passed add() assert statement: confirmed add(4, 7) returns expected result = 11.
    Passed output assert statements: confirmed that expected messages are in console and log.
    
    --- CAPTURED CONSOLE OUTPUT FOR VISUAL INSPECTION ---
    Logging started:  2026-08-04 10:27:54
    | INFO     | add(4, 7) returned 11
    ───────────────────────────────────────────────────────
    Logging ended:    2026-08-04 10:27:54 (duration 00 sec)
    Output directory:
        /private/var/folders/_3/4hr4l8_j0xgg2qp127f3bs180000gn/T/pytest-of-<my_name>/pytest-663/
            test_01_verify_add_calculation0/logs/session/run_2026_08_04__10_27_54
    Log-generated files in output directory:
        config_table.txt
        session.log
    
    --- LOG CONTENT FOR VISUAL INSPECTION ---
    ───────────────────────────────────────────────────────
    session.log
    Logging started:  2026-08-04 10:27:54
    ───────────────────────────────────────────────────────
    
    10:27:54.919 | INFO     | add(4, 7) returned 11
    ───────────────────────────────────────────────────────
    Logging ended:    2026-08-04 10:27:54 (duration 00 sec)
    Output directory:
        /private/var/folders/_3/4hr4l8_j0xgg2qp127f3bs180000gn/T/pytest-of-<my_name>/pytest-663/
            test_01_verify_add_calculation0/logs/session/run_2026_08_04__10_27_54
    Log-generated files in output directory:
        config_table.txt
        session.log
    
    --- End of test_01 ---
    ...

    ==================================== PASSES ====================================
    ================================ tests coverage ================================
    _______________ coverage: platform darwin, python 3.13.5-final-0 _______________
    
    Name                               Stmts   Miss Branch BrPart   Cover   Missing
    -------------------------------------------------------------------------------
    src/sample_package/__init__.py         2      0      0      0 100.00%
    src/sample_package/calculator.py      22     10      6      2  50.00%   21, 50, 68, 86-96
    -------------------------------------------------------------------------------
    TOTAL                                 24     10      6      2  53.33%
    ============================= slowest 10 durations =============================
    0.05s call     examples/basic_project/tests/test_calculator.py::test_01_verify_add_calculation_and_output_to_console_and_log
    
    (9 durations < 0.005s hidden.  Use -vv to show these durations.)

    =========================== short test summary info ============================
    PASSED tests/test_calculator.py::test_01_verify_add_calculation_and_output_to_console_and_log
    ...

    pytest exit code: 0
    duration: 0.42 seconds
    ───────────────────────────────────────────────────────
    Logging ended:    2026-08-04 10:18:32
    Script path:
        /Users/<my_name>/basic_project/tests/pytest_harness_runner.py
    Log file path:
        /Users/<my_name>/basic_project/tests/logs/pytest_harness_runner/
            run_2026_08_04__10_18_31/test_calculator.log


- The individual test-file log also includes detailed tracebacks for failed tests.
- The coverage of 53.33% applies to this test file only. Other test files boosted total coverage to 97%.
- The `Missing` source lines can help target code that needs additional tests.
- A complete basic project is available in the GitHub repository under

    `examples/basic_project/`.


Arguments
---------
- **`test_file_dir`**: `pathlib.Path`  
   Existing directory containing pytest test files.

- **`log_dir`**: `pathlib.Path`  
    Directory where pytest_harness creates run logs. The directory is created
    if it does not already exist.

- **`tested_code_dir`**: `pathlib.Path`  
    Existing dedicated directory containing the code targeted by the tests and
    measured for coverage. Its parent is used for imports in each pytest
    subprocess.

- **`include_list`**: `list[str | pathlib.Path] | None`  
    Optional test files or directories to run. Default is None, which discovers
    all matching test files under `test_file_dir`.

- **`exclude_list`**: `list[str | pathlib.Path] | None`  
    Optional test files or directories to exclude after discovery or inclusion.
    Default is None.

- **`individual_logs`**: `bool`  
    Write one detailed log for each selected test file. Default is True.

- **`coverage_warning_threshold`**: `float | None`  
    Warn when total coverage is below this percentage. This does not affect the
    process exit code. Default is 85.0. Use 0 or None to disable the warning.

- **`show_source_file_coverage`**: `bool`  
    Display the source-file coverage table. Default is True.

- **`show_skipped_and_xfailed`**: `bool`  
    Include Skipped and XFailed outcomes in the flagged-test section. Default
    is False.

- **`log_keep`**: `int | None`  
    Number of recent marked run directories to retain. Default is None, which
    disables pruning.

- **`console_theme`**: `str`  
    Console color theme: `"dark"` or `"light"`. Default is `"dark"`.

- **`console_wrap_width`**: `int`  
    Console wrapping width. Must be at least 80. Default is 150.

- **`debug_pytest_harness`**: `bool`  
    Display additional internal diagnostics when a test-file subprocess cannot
    be processed. Default is False.

For complete validation rules and documentation:

    from pytest_harness import pytest_harness

    help(pytest_harness)


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

Note:
- Skipped and XFailed outcomes do not by themselves cause exit code 1.
- They also do not trigger tests being listed under `Flagged test functions` 
  unless `show_skipped_and_xfailed=True` (default = False)
