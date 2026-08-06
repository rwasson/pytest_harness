"""
test_tested_code_import_path.py

Verify that pytest_harness makes tested_code_dir.parent available to each
pytest subprocess and imports the tested package from the expected directory.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from pytest_harness.record_builder import _build_test_file_record


class _FakeLog:
    def join(self) -> None:
        pass

    @staticmethod
    def new_logger(
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[str], None]:
        return cast(
            Callable[[str], None],
            lambda message: None,
        )


def test_01_tested_code_parent_is_used_for_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    tested_code_dir = project_dir / "src" / "sample_package"
    test_file_dir = project_dir / "tests"
    run_dir = tmp_path / "run"

    tested_code_dir.mkdir(parents=True)
    test_file_dir.mkdir(parents=True)
    run_dir.mkdir()

    (tested_code_dir / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    (tested_code_dir / "calculator.py").write_text(
        "def add(left: int, right: int) -> int:\n"
        "    return left + right\n",
        encoding="utf-8",
    )

    test_file_path = test_file_dir / "test_import_location.py"
    test_file_path.write_text(
        """
from pathlib import Path
import sys

import sample_package
from sample_package.calculator import add


def test_import_environment() -> None:
    expected_package_dir = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "sample_package"
    )

    imported_package_dir = Path(sample_package.__file__).resolve().parent

    resolved_sys_paths = {
        Path(path).resolve()
        for path in sys.path
        if path
    }

    assert expected_package_dir.parent.resolve() in resolved_sys_paths
    assert imported_package_dir == expected_package_dir.resolve()
    assert add(4, 7) == 11
""",
        encoding="utf-8",
    )

    coverage_work_dir = run_dir / "coverage"
    log_dir = run_dir / "logs"

    coverage_work_dir.mkdir()
    log_dir.mkdir()

    coverage_config_file_path = (
        coverage_work_dir / "pytest_harness_coveragerc"
    )

    coverage_config_file_path.write_text(
        "[run]\n"
        "branch = true\n"
        f"source = {tested_code_dir}\n"
        "relative_files = false\n"
        "parallel = true\n"
        "\n"
        "[report]\n"
        "skip_empty = true\n"
        "show_missing = true\n"
        "precision = 2\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "logduo.log",
        _FakeLog(),
    )

    record = _build_test_file_record(
        test_file_path=test_file_path,
        test_file_log_path=log_dir / "test_import_location.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=coverage_work_dir / ".coverage.import_path",
        coverage_config_file_path=coverage_config_file_path,
        individual_logs=False,
        debug_pytest_harness=True,
    )

    assert record.test_file_exit_code == 0, (
        "Nested pytest subprocess failed.\n\n"
        f"Exit code: {record.test_file_exit_code}\n"
        f"Status: {record.status}\n"
        f"Error:\n{record.file_error_message}"
    )
    assert record.passed_test_function_count == 1
    assert record.failed_test_function_count == 0
    assert record.error_test_function_count == 0
