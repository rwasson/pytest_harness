"""
test_coverage_equivalence.py

Verify that combined coverage from isolated test-file subprocesses matches
coverage from one test file containing the same tests.

Last edited: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from pytest_harness.constants_and_classes import (
    CombinedCoverageResult,
    SourceFileCoverageRecord,
)
from pytest_harness.record_builder import (
    _build_test_file_record,
)
from pytest_harness.summary_data_builder import (
    _combine_coverage_data_files,
)

# === Fakes ===================================================================

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


# === Tests ===================================================================
def test_01_single_test_file_matches_official_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    tested_code_dir = project_dir / "src"
    test_file_dir = project_dir / "tests"

    tested_code_dir.mkdir(parents=True)
    test_file_dir.mkdir()

    source_file = tested_code_dir / "coverage_target.py"
    source_file.write_text(
        _SOURCE_TEXT,
        encoding="utf-8",
    )

    test_file = _write_test_file(
        test_file_dir / "test_group_one.py",
        _TEST_IMPORT_BLOCK + _TEST_GROUP_ONE,
    )

    monkeypatch.setattr(
        "logduo.log",
        _FakeLog(),
    )

    result = _run_and_combine(
        run_dir=tmp_path / "single_run",
        tested_code_dir=tested_code_dir,
        test_files=[test_file],
    )

    record = _get_only_source_record(result)

    expected_executed_lines = {
        2,
        3,
        4,
        5,
        6,
        8,
        9,
        17,
        32,
        47,
        48,
        51,
        60,
    }

    expected_missing_lines = {
        11,
        12,
        14,
        18,
        19,
        20,
        21,
        23,
        24,
        26,
        27,
        29,
        38,
        39,
        41,
        42,
        44,
        49,
        52,
        53,
        55,
        57,
        61,
        62,
        63,
    }

    expected_executed_branches = {
        (3, 4),
        (3, 8),
        (4, 5),
        (4, 6),
        (8, 9),
    }

    expected_missing_branches = {
        (8, 11),
        (11, 12),
        (11, 14),
        (23, 24),
        (23, 26),
        (26, 27),
        (26, 29),
        (38, 39),
        (38, 41),
        (41, 42),
        (41, 44),
        (52, 53),
        (52, 55),
        (61, -60),
        (61, 62),
        (62, 61),
        (62, 63),
    }

    assert record.executed_lines == expected_executed_lines
    assert record.missing_lines == expected_missing_lines

    assert record.executed_branch_pairs == expected_executed_branches
    assert (
        record.total_branch_pairs
        == expected_executed_branches | expected_missing_branches
    )

    # There is only one measured source file, so its counts must exactly
    # match Coverage.py's official combined totals.
    assert result.executed_line_count == record.executed_line_count == 13
    assert result.total_line_count == record.total_line_count == 38

    assert result.executed_branch_count == record.executed_branch_count == 5
    assert result.total_branch_count == record.total_branch_count == 22

    assert result.statement_coverage_pct == pytest.approx(
        record.statement_coverage_pct
    )
    assert result.branch_coverage_pct == pytest.approx(
        record.branch_coverage_pct
    )
    assert result.total_coverage_pct == pytest.approx(
        record.overall_coverage_pct
    )

    assert result.statement_coverage_pct == pytest.approx(
        34.21052631578947
    )
    assert result.branch_coverage_pct == pytest.approx(
        22.727272727272727
    )
    assert result.total_coverage_pct == pytest.approx(30.0)

def test_02_two_test_files_combine_to_expected_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    tested_code_dir = project_dir / "src"
    test_file_dir = project_dir / "tests"

    tested_code_dir.mkdir(parents=True)
    test_file_dir.mkdir()

    source_file = tested_code_dir / "coverage_target.py"
    source_file.write_text(
        _SOURCE_TEXT,
        encoding="utf-8",
    )

    test_files = [
        _write_test_file(
            test_file_dir / "test_group_one.py",
            _TEST_IMPORT_BLOCK + _TEST_GROUP_ONE,
        ),
        _write_test_file(
            test_file_dir / "test_group_two.py",
            _TEST_IMPORT_BLOCK + _TEST_GROUP_TWO,
        ),
    ]

    monkeypatch.setattr(
        "logduo.log",
        _FakeLog(),
    )

    result = _run_and_combine(
        run_dir=tmp_path / "two_file_run",
        tested_code_dir=tested_code_dir,
        test_files=test_files,
    )

    record = _get_only_source_record(result)

    expected_executed_lines = {
        2,
        3,
        4,
        5,
        6,
        8,
        9,
        11,
        12,
        14,
        17,
        18,
        19,
        20,
        21,
        23,
        24,
        26,
        27,
        29,
        32,
        47,
        48,
        51,
        60,
    }

    expected_missing_lines = {
        38,
        39,
        41,
        42,
        44,
        49,
        52,
        53,
        55,
        57,
        61,
        62,
        63,
    }

    expected_executed_branches = {
        (3, 4),
        (3, 8),
        (4, 5),
        (4, 6),
        (8, 9),
        (8, 11),
        (11, 12),
        (11, 14),
        (23, 24),
        (23, 26),
        (26, 27),
        (26, 29),
    }

    expected_missing_branches = {
        (38, 39),
        (38, 41),
        (41, 42),
        (41, 44),
        (52, 53),
        (52, 55),
        (61, -60),
        (61, 62),
        (62, 61),
        (62, 63),
    }

    assert record.executed_lines == expected_executed_lines
    assert record.missing_lines == expected_missing_lines

    assert record.executed_branch_pairs == expected_executed_branches
    assert (
        record.total_branch_pairs
        == expected_executed_branches | expected_missing_branches
    )

    assert result.executed_line_count == 25
    assert result.total_line_count == 38

    assert result.executed_branch_count == 12
    assert result.total_branch_count == 22

    assert result.statement_coverage_pct == pytest.approx(
        65.78947368421052
    )
    assert result.branch_coverage_pct == pytest.approx(
        54.54545454545455
    )
    assert result.total_coverage_pct == pytest.approx(
        61.666666666666664
    )


def test_03_split_test_files_match_one_combined_test_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    tested_code_dir = project_dir / "src"
    split_test_file_dir = project_dir / "split_tests"
    combined_test_file_dir = project_dir / "combined_tests"

    tested_code_dir.mkdir(parents=True)
    split_test_file_dir.mkdir()
    combined_test_file_dir.mkdir()

    source_file = tested_code_dir / "coverage_target.py"
    source_file.write_text(
        _SOURCE_TEXT,
        encoding="utf-8",
    )

    split_test_files = [
        _write_test_file(
            split_test_file_dir / "test_group_one.py",
            _TEST_IMPORT_BLOCK + _TEST_GROUP_ONE,
        ),
        _write_test_file(
            split_test_file_dir / "test_group_two.py",
            _TEST_IMPORT_BLOCK + _TEST_GROUP_TWO,
        ),
        _write_test_file(
            split_test_file_dir / "test_group_three.py",
            _TEST_IMPORT_BLOCK + _TEST_GROUP_THREE,
        ),
    ]

    combined_test_file = _write_test_file(
        combined_test_file_dir / "test_all.py",
        (
            _TEST_IMPORT_BLOCK
            + _TEST_GROUP_ONE
            + _TEST_GROUP_TWO
            + _TEST_GROUP_THREE
        ),
    )

    monkeypatch.setattr(
        "logduo.log",
        _FakeLog(),
    )

    split_result = _run_and_combine(
        run_dir=tmp_path / "split_run",
        tested_code_dir=tested_code_dir,
        test_files=split_test_files,
    )

    combined_result = _run_and_combine(
        run_dir=tmp_path / "combined_run",
        tested_code_dir=tested_code_dir,
        test_files=[combined_test_file],
    )

    assert split_result.executed_line_count == (
        combined_result.executed_line_count
    )
    assert split_result.total_line_count == (
        combined_result.total_line_count
    )

    assert split_result.executed_branch_count == (
        combined_result.executed_branch_count
    )
    assert split_result.total_branch_count == (
        combined_result.total_branch_count
    )

    assert split_result.statement_coverage_pct == pytest.approx(
        combined_result.statement_coverage_pct
    )
    assert split_result.branch_coverage_pct == pytest.approx(
        combined_result.branch_coverage_pct
    )
    assert split_result.total_coverage_pct == pytest.approx(
        combined_result.total_coverage_pct
    )

    split_record = next(
        iter(split_result.source_file_coverage_records.values())
    )
    combined_record = next(
        iter(combined_result.source_file_coverage_records.values())
    )

    assert split_record.executed_lines == (
        combined_record.executed_lines
    )
    assert split_record.missing_lines == (
        combined_record.missing_lines
    )
    assert split_record.executed_branch_pairs == (
        combined_record.executed_branch_pairs
    )
    assert split_record.total_branch_pairs == (
        combined_record.total_branch_pairs
    )
    print(
        "\n"
        "Coverage equivalence results\n"
        "----------------------------\n"
        f"Split run test files:       {len(split_test_files)}\n"
        f"Combined run test files:    1\n"
        "\n"
        "Official combined totals\n"
        f"  Split statements:         "
        f"{split_result.executed_line_count}/"
        f"{split_result.total_line_count} "
        f"({split_result.statement_coverage_pct:.2f}%)\n"
        f"  Combined statements:      "
        f"{combined_result.executed_line_count}/"
        f"{combined_result.total_line_count} "
        f"({combined_result.statement_coverage_pct:.2f}%)\n"
        "\n"
        f"  Split branches:           "
        f"{split_result.executed_branch_count}/"
        f"{split_result.total_branch_count} "
        f"({split_result.branch_coverage_pct:.2f}%)\n"
        f"  Combined branches:        "
        f"{combined_result.executed_branch_count}/"
        f"{combined_result.total_branch_count} "
        f"({combined_result.branch_coverage_pct:.2f}%)\n"
        "\n"
        f"  Split total coverage:     "
        f"{split_result.total_coverage_pct:.2f}%\n"
        f"  Combined total coverage:  "
        f"{combined_result.total_coverage_pct:.2f}%\n"
        "\n"
        "Detailed source record\n"
        f"  Split executed lines:     "
        f"{len(split_record.executed_lines)}\n"
        f"  Combined executed lines:  "
        f"{len(combined_record.executed_lines)}\n"
        f"  Split missing lines:      "
        f"{len(split_record.missing_lines)}\n"
        f"  Combined missing lines:   "
        f"{len(combined_record.missing_lines)}\n"
        f"  Split executed branches:  "
        f"{len(split_record.executed_branch_pairs)}\n"
        f"  Combined executed branches: "
        f"{len(combined_record.executed_branch_pairs)}\n"
        "\n"
        "Result: split and combined coverage match."
    )


# === Internal helpers ========================================================
def _run_and_combine(
    *,
    run_dir: Path,
    tested_code_dir: Path,
    test_files: list[Path],
) -> CombinedCoverageResult:
    coverage_work_dir = run_dir / "coverage"
    log_dir = run_dir / "logs"

    coverage_work_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)

    coverage_config_path = (
        coverage_work_dir / "pytest_harness_coveragerc"
    )

    coverage_config_path.write_text(
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

    for index, test_file in enumerate(
        test_files,
        start=1,
    ):
        record = _build_test_file_record(
            test_file_path=test_file,
            test_file_log_path=(
                log_dir / f"{test_file.stem}.log"
            ),
            tested_code_dir=tested_code_dir,
            coverage_data_file_path=(
                coverage_work_dir / f".coverage.{index}"
            ),
            coverage_config_file_path=coverage_config_path,
            individual_logs=False,
        )

        assert record.test_file_exit_code == 0
        assert record.failed_test_function_count == 0
        assert record.error_test_function_count == 0

    return _combine_coverage_data_files(
        coverage_temp_dir_path=coverage_work_dir,
        tested_code_dir=tested_code_dir,
    )


def _write_test_file(
    path: Path,
    text: str,
) -> Path:
    path.write_text(
        text,
        encoding="utf-8",
    )
    return path


# === Internal helpers =========================================================
def _get_only_source_record(
    result: CombinedCoverageResult,
) -> SourceFileCoverageRecord:
    assert len(result.source_file_coverage_records) == 1

    return next(
        iter(result.source_file_coverage_records.values())
    )


_SOURCE_TEXT = '''
def classify_number(value: int) -> str:
    if value < 0:
        if value % 2:
            return "negative odd"
        return "negative even"

    if value == 0:
        return "zero"

    if value % 2:
        return "positive odd"

    return "positive even"


def parse_and_scale(value: str, multiplier: int) -> int:
    try:
        number = int(value)
    except ValueError:
        return -1

    if multiplier == 0:
        raise ZeroDivisionError("zero multiplier")

    if number > 10 and multiplier > 1:
        return number * multiplier

    return number + multiplier


def permission_level(
    *,
    active: bool,
    admin: bool,
    suspended: bool,
) -> str:
    if not active or suspended:
        return "blocked"

    if admin:
        return "admin"

    return "user"


class Accumulator:
    def __init__(self) -> None:
        self.total = 0

    def add(self, value: int) -> int:
        if value < 0:
            self.total -= abs(value)
        else:
            self.total += value

        return self.total


def limited_values(limit: int):
    for number in range(limit):
        if number % 2 == 0:
            yield number
'''

_TEST_IMPORT_BLOCK = '''
import importlib.util
from pathlib import Path

import pytest


SOURCE_FILE = (
    Path(__file__).parents[1]
    / "src"
    / "coverage_target.py"
)

SPEC = importlib.util.spec_from_file_location(
    "coverage_target",
    SOURCE_FILE,
)

assert SPEC is not None
assert SPEC.loader is not None

coverage_target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage_target)
'''

_TEST_GROUP_ONE = '''

def test_classifies_negative_numbers():
    assert coverage_target.classify_number(-3) == "negative odd"
    assert coverage_target.classify_number(-4) == "negative even"


def test_classifies_zero():
    assert coverage_target.classify_number(0) == "zero"
'''

_TEST_GROUP_TWO = '''

def test_classifies_positive_numbers():
    assert coverage_target.classify_number(3) == "positive odd"
    assert coverage_target.classify_number(4) == "positive even"


def test_parses_and_scales_values():
    assert coverage_target.parse_and_scale("12", 3) == 36
    assert coverage_target.parse_and_scale("5", 2) == 7
    assert coverage_target.parse_and_scale("bad", 2) == -1


def test_zero_multiplier_raises():
    with pytest.raises(ZeroDivisionError):
        coverage_target.parse_and_scale("5", 0)
'''

_TEST_GROUP_THREE = '''

def test_permission_levels():
    assert coverage_target.permission_level(
        active=False,
        admin=False,
        suspended=False,
    ) == "blocked"

    assert coverage_target.permission_level(
        active=True,
        admin=True,
        suspended=False,
    ) == "admin"

    assert coverage_target.permission_level(
        active=True,
        admin=False,
        suspended=False,
    ) == "user"

    assert coverage_target.permission_level(
        active=True,
        admin=True,
        suspended=True,
    ) == "blocked"


def test_accumulator_paths():
    accumulator = coverage_target.Accumulator()

    assert accumulator.add(5) == 5
    assert accumulator.add(-2) == 3


def test_generator_branching():
    assert list(coverage_target.limited_values(6)) == [0, 2, 4]
'''

