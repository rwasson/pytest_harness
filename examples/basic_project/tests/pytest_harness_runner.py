"""
pytest_harness_runner.py

Basic project layout:
    basic_project/
        src/
            sample_package/
                calculator.py
            sample_package/helpers/
                arithmetic_functions.py

        tests/
            pytest_harness_runner.py
            test_calculator.py
            unit_tests/
                test_arithmetic_functions.py
                ...

Run from PyCharm: Right-click this runner file and select Run.
Run from Terminal (from the tests' directory): python pytest_harness_runner.py

Note:
- help(pytest_harness) provides documentation and complete list of arguments.
"""

import sys
from dataclasses import fields
from pathlib import Path

from pytest_harness import pytest_harness

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

# --- Optional: inspect returned results ---
print("\nFields in results")
print("-----------------")
for field in fields(results):
    print(field.name)

# test_function_records is useful for repeated-run and flaky-test analysis
print("\nFirst 3 results.test_function_records")
print("-------------------------------------")
for record in results.test_function_records[:3]:
    print(f"{record}\n")

if results.pytest_harness_exit_code != 0:
    sys.exit(results.pytest_harness_exit_code)