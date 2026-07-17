"""
pytest_harness_validation_runner.py

Last edited: 2026-07-16
"""

from pathlib import Path

from pytest_harness import pytest_harness

# --- File settings ---
INDIVIDUAL_LOGS = True

# Run all test_*.py files if include_list is None.
include_list: list[str] | None = None


# Exclude specific test_*.py files if needed.
# These two files are tested in test_pytest_harness.py
# exclude_list: list[str] | None = None
exclude_list = [
    "test_import_error.py",
    "test_empty.py",
]



# --- Path settings ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]

test_dir = (
    PROJECT_ROOT
    / "developer_resources"
    / "pytest_harness_validation"
    / "pytest_files"
)

log_dir = (
    PROJECT_ROOT
    / "developer_resources"
    / "pytest_harness_validation"
    / "logs"
)

source_dir = (
    PROJECT_ROOT
    / "src"
    / "pytest_harness"
)


# === main() DO NOT EDIT BELOW =================================================
def main() -> None:
    pytest_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        include_list=include_list,
        exclude_list=exclude_list,
        individual_logs=INDIVIDUAL_LOGS,
        log_keep=3,
        debug_pytest_harness=False,
    )


if __name__ == "__main__":
    main()
