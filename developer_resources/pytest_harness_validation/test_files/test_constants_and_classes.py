"""
test_constants_and_classes.py

Tests for result-record classes and their derived behavior.

Last edited: 2026-08-08
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    CombinedCoverageResult,
    RunResult,
    SourceFileCoverageRecord,
    TestFileRecord,
    TestFileStatus,
    TestFunctionRecord,
    ValidatedHarnessArgs,
)

# === Tests ===================================================================

# --- test_01_test_function_record_extracts_function_name() --------------------
def test_01_test_function_record_extracts_function_name() -> None:
    record = TestFunctionRecord(
        node_id=(
            "tests/unit/test_math.py::"
            "TestCalculator::test_add[param-1]"
        ),
        outcome="passed",
    )

    assert record.test_function_name == "test_add[param-1]"


# --- test_02_test_file_record_derives_outcome_counts_and_names() --------------
def test_02_test_file_record_derives_outcome_counts_and_names() -> None:
    record = _test_file_record(
        outcomes=[
            ("test_pass_01", "passed"),
            ("test_pass_02", "passed"),
            ("test_failed", "failed"),
            ("test_error", "error"),
            ("test_skipped", "skipped"),
            ("test_xfailed", "xfailed"),
            ("test_xpassed", "xpassed"),
            ("test_timeout", "timed_out"),
            ("test_not_run", "not_run"),
        ],
    )

    assert record.passed_test_function_count == 2
    assert record.failed_test_function_count == 1
    assert record.error_test_function_count == 1
    assert record.skipped_test_function_count == 1
    assert record.xfailed_test_function_count == 1
    assert record.xpassed_test_function_count == 1
    assert record.timed_out_test_function_count == 1

    assert record.passed_test_function_names == [
        "test_pass_01",
        "test_pass_02",
    ]
    assert record.failed_test_function_names == ["test_failed"]
    assert record.error_test_function_names == ["test_error"]
    assert record.skipped_test_function_names == ["test_skipped"]
    assert record.xfailed_test_function_names == ["test_xfailed"]
    assert record.xpassed_test_function_names == ["test_xpassed"]
    assert record.timed_out_test_function_names == ["test_timeout"]


# --- test_03_test_file_record_derives_aggregate_function_information() --------
def test_03_test_file_record_derives_aggregate_function_information() -> None:
    record = _test_file_record(
        outcomes=[
            ("test_passed", "passed"),
            ("test_failed", "failed"),
            ("test_error", "error"),
            ("test_skipped", "skipped"),
            ("test_xfailed", "xfailed"),
            ("test_xpassed", "xpassed"),
            ("test_timeout", "timed_out"),
            ("test_not_run", "not_run"),
            ("test_unfinalized", None),
        ],
    )

    assert record.total_test_function_count == 9
    assert record.executed_any_tests is True

    # Actually executed:
    # passed, failed, error, xfailed, xpassed, timed_out.
    # skipped, not_run, and unfinalized records were not executed.
    assert record.executed_test_count == 6


# --- test_04_empty_test_file_record_reports_no_execution_or_problems() --------
def test_04_empty_test_file_record_reports_no_execution_or_problems() -> None:
    record = _test_file_record(
        outcomes=[],
        status=TestFileStatus.NO_TESTS_COLLECTED,
    )

    assert record.total_test_function_count == 0
    assert record.executed_test_count == 0
    assert record.executed_any_tests is False

    assert record.has_failures is False
    assert record.has_errors is False
    assert record.has_skips is False
    assert record.has_xfails is False
    assert record.has_xpasses is False
    assert record.has_timeouts is False

    assert record.problem_count == 0
    assert record.has_problems is False


# --- test_05_test_file_record_derives_problem_flags_and_warning_data() --------
def test_05_test_file_record_derives_problem_flags_and_warning_data() -> None:
    record = _test_file_record(
        outcomes=[
            ("test_failed", "failed"),
            ("test_error", "error"),
            ("test_skipped", "skipped"),
            ("test_xfailed", "xfailed"),
            ("test_xpassed", "xpassed"),
            ("test_timeout", "timed_out"),
        ],
        warning_messages=[
            "first warning",
            "second warning",
        ],
    )

    assert record.warning_count == 2

    assert record.has_failures is True
    assert record.has_errors is True
    assert record.has_skips is True
    assert record.has_xfails is True
    assert record.has_xpasses is True
    assert record.has_timeouts is True

    assert record.problem_count == 6
    assert record.has_problems is True


# --- test_06_test_file_name_uses_final_path_component() -----------------------
def test_06_test_file_name_uses_final_path_component() -> None:
    record = _test_file_record(
        test_file_label="nested/unit_tests/test_example.py",
        outcomes=[],
    )

    assert record.test_file_name == "test_example.py"


# --- test_07_aggregate_summary_derives_file_and_warning_counts() --------------
def test_07_aggregate_summary_derives_file_and_warning_counts() -> None:
    not_processed = _test_file_record(
        test_file_label="test_import_error.py",
        outcomes=[],
        status=TestFileStatus.NOT_PROCESSED,
    )

    empty = _test_file_record(
        test_file_label="test_empty.py",
        outcomes=[],
        status=TestFileStatus.NO_TESTS_COLLECTED,
    )

    warning_01 = _test_file_record(
        test_file_label="test_warning_01.py",
        outcomes=[("test_one", "passed")],
        warning_messages=[
            "warning one",
            "warning two",
        ],
    )

    warning_02 = _test_file_record(
        test_file_label="test_warning_02.py",
        outcomes=[("test_two", "passed")],
        warning_messages=[
            "warning three",
        ],
    )

    summary = _aggregate_summary(
        not_processed_test_files=[not_processed],
        no_tests_collected_test_files=[empty],
        warning_test_files=[
            warning_01,
            warning_02,
        ],
    )

    assert summary.not_processed_test_file_count == 1
    assert summary.no_tests_collected_test_file_count == 1
    assert summary.warning_test_file_count == 2
    assert summary.warning_count == 3


# --- test_08_source_coverage_record_derives_counts_and_percentages() -----------
def test_08_source_coverage_record_derives_counts_and_percentages() -> None:
    record = SourceFileCoverageRecord(
        source_file_path="/project/src/example.py",
        relative_source_file_path="example.py",
        executed_lines={1, 2, 4},
        missing_lines={3},
        total_line_count=4,
        branch_source={(2, 2), (4, 2)},
        total_branch_pairs={
            (2, 3),
            (2, 4),
            (4, 5),
            (4, 6),
        },
        executed_branch_pairs={
            (2, 3),
            (4, 5),
            (4, 6),
        },
    )

    assert record.executed_line_count == 3
    assert record.missing_line_count == 1

    assert record.total_branch_count == 4
    assert record.executed_branch_count == 3
    assert record.missing_branch_count == 1

    assert record.statement_coverage_pct == pytest.approx(75.0)
    assert record.branch_coverage_pct == pytest.approx(75.0)
    assert record.overall_coverage_pct == pytest.approx(75.0)


# --- test_09_source_coverage_handles_zero_denominators() ----------------------
def test_09_source_coverage_handles_zero_denominators() -> None:
    record = SourceFileCoverageRecord(
        source_file_path="/project/src/empty.py",
        relative_source_file_path="empty.py",
        executed_lines=set(),
        missing_lines=set(),
        total_line_count=0,
        branch_source=set(),
        total_branch_pairs=set(),
        executed_branch_pairs=set(),
    )

    assert record.executed_line_count == 0
    assert record.missing_line_count == 0
    assert record.total_branch_count == 0
    assert record.executed_branch_count == 0
    assert record.missing_branch_count == 0

    assert record.statement_coverage_pct == 0.0
    assert record.branch_coverage_pct == 0.0
    assert record.overall_coverage_pct == 0.0


# --- test_10_frozen_configuration_and_path_records_reject_assignment() --------
def test_10_frozen_configuration_record_rejects_assignment(
    tmp_path: Path,
) -> None:

    args = ValidatedHarnessArgs(
        test_file_dir=tmp_path / "tests",
        log_dir=tmp_path / "logs",
        tested_code_dir=tmp_path / "src",
        include_list=None,
        exclude_list=None,
        runner_log=True,
        test_file_logs=True,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=True,
        log_keep=3,
        console_dashboard=True,
        console_theme="light",
        dashboard_width=120,
        show_skipped_and_xfailed=False,
        debug_harness=False,
        random_order=True,
        random_order_seed=1234,
        test_function_timeout=2.0,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(args, "dashboard_width", 80)

# --- test_11_test_function_record_is_intentionally_mutable() ------------------
def test_11_test_function_record_is_intentionally_mutable() -> None:
    record = TestFunctionRecord(
        node_id="tests/test_example.py::test_one",
    )

    assert record.outcome is None
    assert record.test_order_id == 0
    assert record.run_order == 0

    record.outcome = "passed"
    record.test_order_id = 7
    record.run_order = 3

    assert record.outcome == "passed"
    assert record.test_order_id == 7
    assert record.run_order == 3


# --- test_12_combined_coverage_result_preserves_official_totals() -------------
def test_12_combined_coverage_result_preserves_official_totals() -> None:
    source_record = _coverage_record()

    result = CombinedCoverageResult(
        source_file_coverage_records={
            source_record.source_file_path: source_record,
        },
        executed_line_count=8,
        total_line_count=10,
        executed_branch_count=3,
        total_branch_count=4,
        statement_coverage_pct=80.0,
        branch_coverage_pct=75.0,
        total_coverage_pct=78.57,
    )

    assert len(result.source_file_coverage_records) == 1
    assert result.executed_line_count == 8
    assert result.total_line_count == 10
    assert result.executed_branch_count == 3
    assert result.total_branch_count == 4
    assert result.statement_coverage_pct == 80.0
    assert result.branch_coverage_pct == 75.0
    assert result.total_coverage_pct == 78.57

# --- test_13_test_file_record_false_problem_flags() ----------------------------
def test_13_test_file_record_false_problem_flags() -> None:
    record = _test_file_record(
        outcomes=[
            ("test_passed", "passed"),
        ],
    )

    assert record.has_failures is False
    assert record.has_errors is False
    assert record.has_skips is False
    assert record.has_xfails is False
    assert record.has_xpasses is False
    assert record.has_timeouts is False
    assert record.has_problems is False
    assert record.problem_count == 0


# --- test_14_not_run_and_none_are_not_outcome_counts() ------------------------
def test_14_not_run_and_none_are_not_outcome_counts() -> None:
    record = _test_file_record(
        outcomes=[
            ("test_not_run", "not_run"),
            ("test_unfinalized", None),
        ],
    )

    assert record.passed_test_function_count == 0
    assert record.failed_test_function_count == 0
    assert record.error_test_function_count == 0
    assert record.skipped_test_function_count == 0
    assert record.xfailed_test_function_count == 0
    assert record.xpassed_test_function_count == 0
    assert record.timed_out_test_function_count == 0

    assert record.passed_test_function_names == []
    assert record.failed_test_function_names == []
    assert record.error_test_function_names == []
    assert record.skipped_test_function_names == []
    assert record.xfailed_test_function_names == []
    assert record.xpassed_test_function_names == []
    assert record.timed_out_test_function_names == []


# --- test_15_source_coverage_statement_only() ---------------------------------
def test_15_source_coverage_statement_only() -> None:
    record = SourceFileCoverageRecord(
        source_file_path="/project/src/example.py",
        relative_source_file_path="example.py",
        executed_lines={1, 2},
        missing_lines={3, 4},
        total_line_count=4,
        branch_source=set(),
        total_branch_pairs=set(),
        executed_branch_pairs=set(),
    )

    assert record.statement_coverage_pct == pytest.approx(50.0)
    assert record.branch_coverage_pct == 0.0
    assert record.overall_coverage_pct == pytest.approx(50.0)


# --- test_16_source_coverage_branch_only() ------------------------------------
def test_16_source_coverage_branch_only() -> None:
    record = SourceFileCoverageRecord(
        source_file_path="/project/src/example.py",
        relative_source_file_path="example.py",
        executed_lines=set(),
        missing_lines=set(),
        total_line_count=0,
        branch_source={(10, 2)},
        total_branch_pairs={
            (10, 11),
            (10, 12),
        },
        executed_branch_pairs={
            (10, 11),
        },
    )

    assert record.statement_coverage_pct == 0.0
    assert record.branch_coverage_pct == pytest.approx(50.0)
    assert record.overall_coverage_pct == pytest.approx(50.0)


# --- test_17_run_result_preserves_public_result_data() ------------------------
def test_17_run_result_preserves_public_result_data(
    tmp_path: Path,
) -> None:
    function_record = TestFunctionRecord(
        node_id="tests/test_example.py::test_one",
        outcome="passed",
        test_order_id=1,
        run_order=1,
    )

    file_record = _test_file_record(
        test_file_label="test_example.py",
        outcomes=[
            ("test_one", "passed"),
        ],
    )

    source_record = _coverage_record()

    result = RunResult(
        run_id="abc123",
        pytest_harness_exit_code=0,
        output_dir_path=tmp_path,
        random_order_seed=1234,
        test_function_timeout_seconds=2.0,

        test_file_count=1,
        passed_test_file_count=1,
        failed_test_file_count=0,
        error_test_file_count=0,
        skipped_test_file_count=0,
        xfailed_test_file_count=0,
        xpassed_test_file_count=0,
        not_processed_test_file_count=0,
        no_tests_collected_test_file_count=0,
        warning_test_file_count=0,
        warning_count=0,

        passed_test_function_count=1,
        failed_test_function_count=0,
        error_test_function_count=0,
        skipped_test_function_count=0,
        xfailed_test_function_count=0,
        xpassed_test_function_count=0,

        test_function_records=(function_record,),
        test_file_records=(file_record,),

        source_file_count=1,
        executed_line_count=4,
        total_line_count=5,
        executed_branch_count=1,
        total_branch_count=2,
        statement_coverage_pct=80.0,
        branch_coverage_pct=50.0,
        total_coverage_pct=70.0,

        source_file_coverage_records=(source_record,),
    )

    assert result.run_id == "abc123"
    assert result.pytest_harness_exit_code == 0
    assert result.test_function_records == (function_record,)
    assert result.test_file_records == (file_record,)
    assert result.source_file_coverage_records == (source_record,)

    with pytest.raises(FrozenInstanceError):
        setattr(result, "pytest_harness_exit_code", 1)

# === Internal helpers =========================================================

def _test_file_record(
    *,
    test_file_label: str = "nested/test_example.py",
    outcomes: list[tuple[str, str | None]],
    status: TestFileStatus = TestFileStatus.PROCESSED,
    warning_messages: list[str] | None = None,
) -> TestFileRecord:
    test_function_records = [
        TestFunctionRecord(
            node_id=f"{test_file_label}::{name}",
            outcome=outcome,
        )
        for name, outcome in outcomes
    ]

    node_ids = [
        record.node_id
        for record in test_function_records
    ]

    return TestFileRecord(
        test_file_path=Path("/project/tests") / test_file_label,
        test_file_label=test_file_label,
        test_file_exit_code=0,
        duration_seconds=0.1,
        status=status,
        timed_out_test_function_node_id=None,
        not_processed_reason=None,
        file_error_message=None,
        warning_messages=warning_messages or [],
        collected_test_function_node_ids=node_ids,
        started_test_function_node_ids=[
            record.node_id
            for record in test_function_records
            if record.outcome not in {
                None,
                "not_run",
            }
        ],
        test_function_records=test_function_records,
    )


def _aggregate_summary(
    *,
    not_processed_test_files: list[TestFileRecord] | None = None,
    no_tests_collected_test_files: list[TestFileRecord] | None = None,
    warning_test_files: list[TestFileRecord] | None = None,
) -> AggregateTestSummary:
    return AggregateTestSummary(
        random_order_seed=1234,
        test_function_timeout_seconds=2.0,
        source_file_count=0,
        test_file_count=4,

        passed_test_file_count=2,
        failed_test_file_count=0,
        error_test_file_count=0,
        skipped_test_file_count=0,
        xfailed_test_file_count=0,
        xpassed_test_file_count=0,

        passed_test_function_count=2,
        failed_test_function_count=0,
        error_test_function_count=0,
        skipped_test_function_count=0,
        xfailed_test_function_count=0,
        xpassed_test_function_count=0,

        executed_line_count=0,
        total_line_count=0,
        executed_branch_count=0,
        total_branch_count=0,

        statement_coverage_pct=0.0,
        branch_coverage_pct=0.0,
        total_coverage_pct=0.0,

        problem_test_files=[],
        not_processed_test_files=not_processed_test_files or [],
        no_tests_collected_test_files=no_tests_collected_test_files or [],
        warning_test_files=warning_test_files or [],
        source_file_coverage_records=[],
    )


def _coverage_record() -> SourceFileCoverageRecord:
    return SourceFileCoverageRecord(
        source_file_path="/project/src/example.py",
        relative_source_file_path="example.py",
        executed_lines={1, 2, 3, 4},
        missing_lines={5},
        total_line_count=5,
        branch_source={(2, 2)},
        total_branch_pairs={
            (2, 3),
            (2, 4),
        },
        executed_branch_pairs={
            (2, 3),
        },
    )
