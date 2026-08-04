"""
pytest_harness_ci_runner.py

Run the successful basic-project tests in CI.
Intentional failure, error, empty, and import-error examples are excluded.
"""

from pathlib import Path

from pytest_harness import pytest_harness


PROJECT_ROOT = Path(__file__).resolve().parents[2] / "examples" / "basic_project"


def main() -> None:
    pytest_harness(
        test_file_dir=PROJECT_ROOT / "tests",
        log_dir=PROJECT_ROOT / "tests" / "logs",
        tested_code_dir=PROJECT_ROOT / "src" / "sample_package",
        include_list=[
            "test_calculator.py",
            "test_validation.py",
        ],
        log_keep=3,
    )


if __name__ == "__main__":
    main()