"""
pytest_harness_runner.py

Run the basic pytest_harness example from an IDE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pytest_harness import pytest_harness

PROJECT_ROOT = Path(__file__).resolve().parent

SOURCE_ROOT = PROJECT_ROOT / "src"
TEST_DIR = PROJECT_ROOT / "tests"
LOG_DIR = PROJECT_ROOT / "logs"

# Make sample_package importable in this process.
source_root_text = str(SOURCE_ROOT)

if source_root_text not in sys.path:
    sys.path.insert(0, source_root_text)

# Make the example package importable by each isolated pytest subprocess.
existing_pythonpath = os.environ.get("PYTHONPATH")

if existing_pythonpath:
    os.environ["PYTHONPATH"] = (
        f"{SOURCE_ROOT}{os.pathsep}{existing_pythonpath}"
    )
else:
    os.environ["PYTHONPATH"] = str(SOURCE_ROOT)


pytest_harness(
    test_dir=TEST_DIR,
    log_dir=LOG_DIR,
    source_dir=SOURCE_ROOT / "sample_package",
    include_list=None,
    exclude_list=None,
    individual_logs=True,
    coverage_warning_threshold=85.0,
    show_source_file_coverage=True,
    show_skipped_and_xfailed=False,
    log_keep=5,
    console_wrap_width=120,
    debug_pytest_harness=False,
)
