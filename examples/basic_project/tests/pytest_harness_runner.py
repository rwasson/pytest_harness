"""
pytest_harness_runner.py

Project layout:
    basic_project/
        src/
            sample_package/
        tests/
            pytest_harness_runner.py
            test_calculator.py
            test_flagged.py
            test_validation.py

Run from PyCharm:
    Right-click this file and select Run.

Run from Terminal:
    From the tests' directory:

        python pytest_harness_runner.py

help(pytest_harness) provides documentation and complete list of arguments.
"""

from pathlib import Path
from typing import NoReturn

from pytest_harness import pytest_harness

PROJECT_ROOT = Path(__file__).resolve().parents[1]

__test__ = False


def main() -> NoReturn:
    __test__ = False
    pytest_harness(
        test_file_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "tests" / "logs",
        tested_code_dir=PROJECT_ROOT / "src" / "sample_package",
        log_keep=3,
    )


if __name__ == "__main__":
    __test__ = False
    main()
