from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows integration test",
)


def test_pytest_harness_runs_with_windows_temp_paths(
    tmp_path: Path,
) -> None:
    # --- Arrange: temporary project ---
    project_dir = tmp_path / "sample project"
    package_dir = project_dir / "sample_package"
    test_file_dir = project_dir / "tests"
    log_dir = project_dir / "test logs"

    package_dir.mkdir(parents=True)
    test_file_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)

    (package_dir / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    (package_dir / "calculator.py").write_text(
        "def add(first: int, second: int) -> int:\n"
        "    return first + second\n",
        encoding="utf-8",
    )

    (test_file_dir / "test_calculator.py").write_text(
        "from sample_package.calculator import add\n\n"
        "\n"
        "def test_add() -> None:\n"
        "    assert add(4, 7) == 11\n",
        encoding="utf-8",
    )

    runner_path = project_dir / "pytest_harness_runner.py"

    runner_path.write_text(
        "from pathlib import Path\n\n"
        "from pytest_harness import pytest_harness\n\n"
        "\n"
        "PROJECT_DIR = Path(__file__).resolve().parent\n\n"
        "pytest_harness(\n"
        "    test_file_dir=PROJECT_DIR / 'tests',\n"
        "    tested_code_dir=PROJECT_DIR / 'sample_package',\n"
        "    log_dir=PROJECT_DIR / 'test logs',\n"
        ")\n",
        encoding="utf-8",
    )

    # --- Act ---
    process = subprocess.run(
        [sys.executable, str(runner_path)],
        cwd=project_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    # --- Assert: process completed successfully ---
    assert process.returncode == 0, (
        f"STDOUT:\n{process.stdout}\n\n"
        f"STDERR:\n{process.stderr}"
    )

    assert "Running 1 test file" in process.stdout
    assert "Passed:" in process.stdout

    # --- Assert: Windows paths were actually used ---
    assert project_dir.drive
    assert "\\" in str(project_dir)

    # --- Assert: permanent logs were created ---
    main_logs = list(log_dir.rglob("pytest_harness_runner.log"))
    test_file_logs = list(log_dir.rglob("test_calculator.log"))

    assert len(main_logs) == 1
    assert len(test_file_logs) == 1

    main_log_text = main_logs[0].read_text(encoding="utf-8")
    test_file_log_text = test_file_logs[0].read_text(encoding="utf-8")

    assert "Pytest Harness Summary" in main_log_text
    assert "Pytest Harness exit code: 0 (no errors detected)" in main_log_text

    assert "1 passed" in test_file_log_text
    assert "pytest exit code: 0" in test_file_log_text
