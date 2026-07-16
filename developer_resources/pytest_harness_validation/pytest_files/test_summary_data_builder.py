"""
test_summary_data_builder.py

Last edited: 2026-07-16
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pytest_harness.summary_data_builder as module
from pytest_harness.constants_and_classes import (
    CombinedCoverageResult,
    SourceFileCoverageRecord,
    TestFileRecord,
    TestFileStatus,
)

# === Tests ===================================================================

def test_01_builds_aggregate_counts_and_problem_records(
    tmp_path: Path,
) -> None:

    records = [
        _file_record(
            path=str(tmp_path / "test_pass.py"),
            passed=["test_a", "test_b"],
        ),
        _file_record(
            path=str(tmp_path / "test_mixed.py"),
            passed=["test_ok"],
            failed=["test_fail"],
            skipped=["test_skip"],
            xfailed=["test_expected_failure"],
            xpassed=["test_unexpected_pass"],
            exit_code=1,
        ),
        _file_record(
            path=str(tmp_path / "test_error.py"),
            errors=["test_setup_error"],
            exit_code=1,
        ),
        _file_record(
            path=str(
                tmp_path / "test_import_problem.py"
            ),
            exit_code=2,
            status=TestFileStatus.NOT_PROCESSED,
            file_error_message=(
                "ImportError during collection"
            ),
        ),
        _file_record(
            path=str(tmp_path / "test_empty.py"),
            exit_code=5,
            status=TestFileStatus.NO_TESTS_COLLECTED,
        ),
    ]

    coverage = _combined_result(
        [
            _coverage_record(
                str(tmp_path / "well_covered.py"),
                executed_lines=set(range(1, 10)),
                total_line_count=10,
            ),
            _coverage_record(
                str(tmp_path / "poorly_covered.py"),
                executed_lines={1},
                total_line_count=10,
            ),
        ]
    )

    result = module._build_summary_data(
        pytest_test_file_records=records,
        combined_coverage_result=coverage,
        show_skipped_and_xfailed=False,
        debug_pytest_harness=False,
    )

    assert result.test_file_count == 5
    assert result.passed_test_file_count == 1

    assert result.failed_test_file_count == 1
    assert result.error_test_file_count == 1
    assert result.skipped_test_file_count == 1
    assert result.xfailed_test_file_count == 1
    assert result.xpassed_test_file_count == 1

    assert result.passed_test_function_count == 3
    assert result.failed_test_function_count == 1
    assert result.error_test_function_count == 1
    assert result.skipped_test_function_count == 1
    assert result.xfailed_test_function_count == 1
    assert result.xpassed_test_function_count == 1

    assert result.not_processed_test_files == [
        "test_import_problem.py"
    ]
    assert result.not_processed_test_file_count == 1

    assert result.no_tests_collected_test_files == [
        "test_empty.py"
    ]
    assert (
        result.no_tests_collected_test_file_count
        == 1
    )

    assert [
        record.test_file_name
        for record in result.problem_test_files
    ] == [
        "test_mixed.py",
        "test_error.py",
    ]

    mixed = result.problem_test_files[0]

    assert mixed.failed_test_function_names == [
        "test_fail"
    ]
    assert mixed.skipped_test_function_names == [
        "test_skip"
    ]
    assert mixed.xfailed_test_function_names == [
        "test_expected_failure"
    ]
    assert mixed.xpassed_test_function_names == [
        "test_unexpected_pass"
    ]

    # ProblemTestFileRecord currently retains all non-Passed
    # outcomes, including Skipped and XFailed.
    assert mixed.problem_count == 4


def test_02_skipped_and_xfailed_only_file_is_not_flagged_by_default(
    tmp_path: Path,
) -> None:

    record = _file_record(
        path=str(tmp_path / "test_expected.py"),
        skipped=["test_skip"],
        xfailed=["test_expected_failure"],
    )

    result = module._build_summary_data(
        pytest_test_file_records=[record],
        combined_coverage_result=_combined_result([]),
        show_skipped_and_xfailed=False,
        debug_pytest_harness=False,
    )

    assert result.skipped_test_file_count == 1
    assert result.xfailed_test_file_count == 1
    assert result.problem_test_files == []
    assert result.passed_test_file_count == 0


def test_03_show_all_problems_flags_skipped_and_xfailed_file(
    tmp_path: Path,
) -> None:


    record = _file_record(
        path=str(tmp_path / "test_expected.py"),
        skipped=["test_skip"],
        xfailed=["test_expected_failure"],
    )

    result = module._build_summary_data(
        pytest_test_file_records=[record],
        combined_coverage_result=_combined_result([]),
        show_skipped_and_xfailed=True,
        debug_pytest_harness=False,
    )

    assert [
        problem.test_file_name
        for problem in result.problem_test_files
    ] == ["test_expected.py"]

    problem = result.problem_test_files[0]

    assert problem.skipped_test_function_names == [
        "test_skip"
    ]
    assert problem.xfailed_test_function_names == [
        "test_expected_failure"
    ]


def test_04_copies_official_coverage_totals_and_sorts_source_files_lowest_first(
    tmp_path: Path,
) -> None:
    low = _coverage_record(
        str(tmp_path / "low.py"),
        executed_lines={1},
        total_line_count=10,
    )

    high = _coverage_record(
        str(tmp_path / "high.py"),
        executed_lines=set(range(1, 10)),
        total_line_count=10,
    )

    result = module._build_summary_data(
        pytest_test_file_records=[],
        combined_coverage_result=_combined_result(
            [high, low]
        ),
        show_skipped_and_xfailed=False,
        debug_pytest_harness=False,
    )

    assert result.source_file_count == 2

    assert [
        Path(record.source_file_path).name
        for record in result.source_file_coverage_records
    ] == [
        "low.py",
        "high.py",
    ]

    assert result.executed_line_count == 15
    assert result.total_line_count == 20
    assert result.executed_branch_count == 6
    assert result.total_branch_count == 10

    assert result.statement_coverage_pct == 75.0
    assert result.branch_coverage_pct == 60.0
    assert result.total_coverage_pct == 70.0


def test_05_debug_mode_prints_official_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = module._build_summary_data(
        pytest_test_file_records=[],
        combined_coverage_result=_combined_result([]),
        show_skipped_and_xfailed=False,
        debug_pytest_harness=True,
    )

    output = capsys.readouterr().out

    assert result.test_file_count == 0
    assert (
        "Official combined Coverage.py counts"
        in output
    )
    assert "statements: 15 / 20" in output
    assert "branches:   6 / 10" in output


def test_06_combines_coverage_and_builds_source_file_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage_dir = tmp_path / "coverage"
    coverage_dir.mkdir()

    source_dir = tmp_path / "src" / "package"
    source_dir.mkdir(parents=True)

    included_file = source_dir / "module.py"
    excluded_file = tmp_path / "outside.py"

    _FakeCoverage.instances.clear()
    _FakeCoverage.report = {
        "totals": {
            "covered_lines": 8,
            "num_statements": 10,
            "covered_branches": 3,
            "num_branches": 4,
            "percent_covered": 78.571428,
        },
        "files": {
            str(included_file): {
                "executed_lines": [1, 2, 3, 4],
                "missing_lines": [5],
                "executed_branches": [
                    [2, 3],
                    [2, 4],
                ],
                "missing_branches": [
                    [4, 5],
                ],
                "summary": {
                    "num_statements": 5,
                },
            },
            str(excluded_file): {
                "executed_lines": [1],
                "missing_lines": [],
                "executed_branches": [],
                "missing_branches": [],
                "summary": {
                    "num_statements": 1,
                },
            },
        },
    }

    monkeypatch.setattr(
        module,
        "Coverage",
        _FakeCoverage,
    )

    result = module._combine_coverage_data_files(
        coverage_dir_path=coverage_dir,
        source_dir=source_dir,
    )

    assert result.executed_line_count == 8
    assert result.total_line_count == 10
    assert result.executed_branch_count == 3
    assert result.total_branch_count == 4

    assert result.statement_coverage_pct == 80.0
    assert result.branch_coverage_pct == 75.0
    assert result.total_coverage_pct == pytest.approx(
        78.571428
    )

    assert list(
        result.source_file_coverage_records
    ) == [str(included_file.resolve())]

    record = result.source_file_coverage_records[
        str(included_file.resolve())
    ]

    assert record.executed_lines == {1, 2, 3, 4}
    assert record.missing_lines == {5}
    assert record.total_line_count == 5

    assert record.executed_branch_pairs == {
        (2, 3),
        (2, 4),
    }
    assert record.total_branch_pairs == {
        (2, 3),
        (2, 4),
        (4, 5),
    }
    assert record.branch_source == {
        (2, 2),
        (4, 1),
    }

    fake_coverage = _FakeCoverage.instances[0]

    assert fake_coverage.data_file == str(
        coverage_dir / ".coverage"
    )
    assert fake_coverage.branch is True
    assert fake_coverage.save_called is True

    assert fake_coverage.combine_calls == [
        {
            "data_paths": [str(coverage_dir)],
            "strict": True,
            "keep": True,
        }
    ]

    assert fake_coverage.json_report_calls == [
        {
            "outfile": str(
                coverage_dir / "combined_coverage.json"
            ),
            "pretty_print": False,
        }
    ]


def test_07_combined_coverage_handles_zero_statement_and_branch_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coverage_dir = tmp_path / "coverage"
    coverage_dir.mkdir()

    source_dir = tmp_path / "src"
    source_dir.mkdir()

    _FakeCoverage.instances.clear()
    _FakeCoverage.report = {
        "totals": {
            "covered_lines": 0,
            "num_statements": 0,
            "covered_branches": 0,
            "num_branches": 0,
            "percent_covered": 100.0,
        },
        "files": {},
    }

    monkeypatch.setattr(
        module,
        "Coverage",
        _FakeCoverage,
    )

    result = module._combine_coverage_data_files(
        coverage_dir_path=coverage_dir,
        source_dir=source_dir,
    )

    assert result.statement_coverage_pct == 0.0
    assert result.branch_coverage_pct == 0.0
    assert result.total_coverage_pct == 100.0
    assert result.source_file_coverage_records == {}

# === Internal helpers ========================================================

def _file_record(
    *,
    path: str,
    passed: list[str] | None = None,
    failed: list[str] | None = None,
    errors: list[str] | None = None,
    skipped: list[str] | None = None,
    xfailed: list[str] | None = None,
    xpassed: list[str] | None = None,
    exit_code: int = 0,
    status: TestFileStatus = TestFileStatus.PROCESSED,
    file_error_message: str | None = None,
) -> TestFileRecord:
    passed = passed or []
    failed = failed or []
    errors = errors or []
    skipped = skipped or []
    xfailed = xfailed or []
    xpassed = xpassed or []

    return TestFileRecord(
        test_file_path=path,
        exit_code=exit_code,
        duration_seconds=0.1,
        status=status,
        file_error_message=file_error_message,
        passed_test_function_count=len(passed),
        failed_test_function_count=len(failed),
        error_test_function_count=len(errors),
        skipped_test_function_count=len(skipped),
        xfailed_test_function_count=len(xfailed),
        xpassed_test_function_count=len(xpassed),
        passed_test_function_names=passed,
        failed_test_function_names=failed,
        error_test_function_names=errors,
        skipped_test_function_names=skipped,
        xfailed_test_function_names=xfailed,
        xpassed_test_function_names=xpassed,
    )


def _coverage_record(
    path: str,
    *,
    executed_lines: set[int],
    total_line_count: int,
) -> SourceFileCoverageRecord:
    all_lines = set(
        range(1, total_line_count + 1)
    )

    return SourceFileCoverageRecord(
        source_file_path=path,
        executed_lines=executed_lines,
        missing_lines=all_lines - executed_lines,
        total_line_count=total_line_count,
        branch_source=set(),
        total_branch_pairs=set(),
        executed_branch_pairs=set(),
    )


def _combined_result(
    records: list[SourceFileCoverageRecord],
) -> CombinedCoverageResult:
    return CombinedCoverageResult(
        source_file_coverage_records={
            record.source_file_path: record
            for record in records
        },
        executed_line_count=15,
        total_line_count=20,
        executed_branch_count=6,
        total_branch_count=10,
        statement_coverage_pct=75.0,
        branch_coverage_pct=60.0,
        total_coverage_pct=70.0,
    )


class _FakeCoverage:
    report: dict[str, object] = {}
    instances: list["_FakeCoverage"] = []

    def __init__(
        self,
        *,
        data_file: str,
        branch: bool,
    ) -> None:
        self.data_file = data_file
        self.branch = branch
        self.combine_calls: list[dict[str, object]] = []
        self.save_called = False
        self.json_report_calls: list[dict[str, object]] = []

        type(self).instances.append(self)

    def combine(
        self,
        *,
        data_paths: list[str],
        strict: bool,
        keep: bool,
    ) -> None:
        self.combine_calls.append(
            {
                "data_paths": data_paths,
                "strict": strict,
                "keep": keep,
            }
        )

    def save(self) -> None:
        self.save_called = True

    def json_report(
        self,
        *,
        outfile: str,
        pretty_print: bool,
    ) -> None:
        self.json_report_calls.append(
            {
                "outfile": outfile,
                "pretty_print": pretty_print,
            }
        )

        Path(outfile).write_text(
            json.dumps(type(self).report),
            encoding="utf-8",
        )
