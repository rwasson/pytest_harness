"""
test_calculator.py

Tests for successful calculator operations.

Printed diagnostic details are included in this test file's individual log.
This can be useful for recording inputs, intermediate values, and calculated
results without adding them to the main pytest_harness summary.

To remove unresolved-reference warnings in the IDE editor, right-click the
src directory and select:

    Mark Directory As > Sources Root

PyCharm may need to restart or reindex before the warnings disappear.
These editor warnings do not affect test execution. A project can have more
than one Sources Root, including a Sources Root inside a nested example or
subproject.

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
    log(f"    {calculation_report("add", 4, 7)}")

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
