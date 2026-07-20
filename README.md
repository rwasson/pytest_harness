pytest_harness
==============

pytest_harness is a one-click pytest workflow runner for IDE-centered development.
It handles pytest, coverage, subprocess isolation, summary reporting, and logs
so tests are easy to run and interpret.


Why use pytest_harness?
-----------------------
- one-click test execution from an IDE
- no command-line flags, pyproject.toml coverage settings, or log setup required 
    (pytest_harness handles settings)
- all test files run even if one test file crashes
- compact dashboard and runner log for the complete run:
    - summary results 
    - list of files with import/test collection errors
    - combined coverage
    - (optional) coverage for each source file
    - list of paths of created log files
    - exit code
- optional per-test-file logs:
    - test results
    - user-generated print() statements (verifies tests are exercising the code as intended)  
    - missing (uncovered) source lines
- detailed docstring available with help(pytest_harness)

pytest_harness is a workflow tool, not a pytest plugin.


Quick Start
-----------
Create a small runner script in your project's test directory:
- pytest_harness handles logging. Do not set up logging in your runner script.
- Recommendation: give your runner script a name that does not start with
  `test_` or end with `_test.py`. PyCharm may treat those names as pytest test
  files rather than executable scripts that can be run with right-click.


    # pytest_harness_runner.py, located inside project_root/tests/

    from pathlib import Path

    from pytest_harness import pytest_harness

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    pytest_harness(
        test_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "logs",
        source_dir=PROJECT_ROOT / "src" / "my_package",
        log_keep=5,
    )

Create a test file in your project's test directory:
- Test filenames should match `test_*.py`.
- Do not configure pytest_harness or logging inside individual test files.
- Use print() inside test definitions to verify tests are exercising the code as intended.
- Use tmp_path when tests create temporary files or directories.
- Keep tests independent and do not rely on test execution order.


    # test_calculator.py, located inside project_root/tests/

    from my_package.calculator import calculate_discount

    def test_discount_calculation():

        subtotal = 120
        discount_rate = 0.15
    
        result = calculate_discount(subtotal, discount_rate)
        expected = 18
    
        print(f"subtotal={subtotal}")
        print(f"discount_rate={discount_rate}")
        print(f"calculated_discount={result}")
        print(f"expected_discount={expected}")
    
        assert result == expected

In PyCharm, right-click the runner script and run it.


Logs
----
pytest_harness automatically writes one summary log for the runner. When
`individual_logs=True` (the default), it also writes one log for each selected
test file.

When running `pytest_harness_runner.py` with

    log_dir=PROJECT_ROOT / "logs"

and `test_dir` containing

    test_config.py

    unit/test_paths.py

-> log files: 

    output directory: 
    project_root/logs/pytest_runner/run_YYYY_MM_DD__HH_MM_SS/

    files in output directory: 
        pytest_harness_runner.log
        test_config.log
        unit__test_paths.log

Output from print() statements inside a test file is captured in that test file's 
individual log.


Example Dashboard 
-----------------
* Note: Created using `console_wrap_width = 100` to better fit this document

        logging started:  2026-07-19 12:25:55
        running script :  pytest_harness_runner.py
        pruned run directories: 1 (keep=3)  
        
        Running 9 test files: ......... done
        
        ════════════════════════════════════════════════════════════
                                TEST SUMMARY                        
        ════════════════════════════════════════════════════════════
        
        Test file summary
        ------------------------------------------------------------
        Source files covered:         8
        Test files run:               9
        Test files passed all tests:  6
        
        Test files not processed, often due to an import error (1):
            test_import_error.py
        
        Test files with no collected tests (1):
            test_empty.py
        
        
        Test function summary
        ------------------------------------------------------------
            Passed:   103
            Failed:     1
            Error:      0
            XPassed:    0
            Skipped:    0
            XFailed:    0
        
        Flagged test functions (in 1 test file):
            test_pytest_harness.py
                Failed (1):
                    test_12_intentional_fail
        
        Coverage
        ------------------------------------------------------------
            Statements:   95%
            Branches:     93%
            Total:        95%
        
        
        Source  
        file      Executed/ 
        Coverage  Statements  Source file
        --------  ----------  -----------
        90%       94/104      record_builder.py
        92%       168/183     constants_and_classes.py
        97%       101/104     summary_data_builder.py
        98%       78/80       arg_resolver.py
        98%       48/49       resolve_test_file_paths.py
        98%       55/56       pytest_harness.py
        99%       70/71       summary_table_builder.py
        100%      3/3         __init__.py
        ───────────────────────────────────────────────────────
        logging ended   :  2026-07-19 12:25:59 (duration 04 sec)
        script path     :  project_root/dev/pytest_harness_validation/pytest_harness_runner.py
        output directory:  project_root/logs/pytest_harness_runner/run_2026_07_19__12_25_55/

        files created this logging session in output directory:
            pytest_harness_runner.log
            ...
            test_summary_table_builder.log
        

        Process finished with exit code 1


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
- They also do not trigger tests being listed under `Flagged test functions by 
test file` unless `show_skipped_and_xfailed=True` (default = False)


Arguments:
---------

### `test_dir`

Directory containing pytest test files.
Must be a `pathlib.Path`, must exist, and must be a directory.

### `log_dir`

Directory where `pytest_harness` writes run logs.
Must be a `pathlib.Path`. If the directory does not exist, `pytest_harness`
creates it after all arguments have been validated.


### `source_dir`

Source directory containing code files measured for coverage.
Must be a `pathlib.Path`, must exist, and must be a directory.

### `include_list`

Optional list of test files or test directories to run.
Entries may be strings or `pathlib.Path` objects.

Default: None (discover all test files in `test_dir`).

### `exclude_list`

Optional list of test files or test directories to exclude.
Exclusions are applied after normal discovery or include-list selection.

Default: None (no test files excluded)

### `individual_logs`

Optional. If True, writes a detailed log for each selected test file.

Default: True

### `coverage_warning_threshold`

Optional total-coverage warning threshold from 0 through 100.

Default: 85.0 (use 0 or None to disable)

### `show_source_file_coverage`

Optional. If True, displays the source-file coverage table.

Default: True

### `show_skipped_and_xfailed`

Optional. If True, Skipped and XFailed outcomes are included in the
    flagged-test section along with Failed, Error, and XPassed outcomes.

Default: False

### `log_keep`

Optional number of recent pytest_harness run directories to keep.
Only run directories containing the auto-generated `.logduo_marker` file are
eligible for pruning.        

Default: None (no run directories pruned)

### `console_wrap_width`
    
Optional. Console wrapping width used by Logduo. Must be a positive integer >= 80.

Default: 150

### `debug_pytest_harness`

Optional. If True, prints additional pytest_harness diagnostic information,
including the exact selected test files and official combined Coverage.py
line counts.

Default: False


Examples
--------
A basic example project is available in:

    examples/basic_project/

More advanced usage and edge-case examples are available in:

    developer_resources/pytest_harness_validation/


