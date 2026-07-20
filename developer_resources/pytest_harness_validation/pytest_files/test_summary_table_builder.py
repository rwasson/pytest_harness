"""
test_summary_table_builder.py

Last edited: 2026-07-16
"""

from __future__ import annotations

import pytest

import pytest_harness.summary_table_builder as module
from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    ProblemTestFileRecord,
    SourceFileCoverageRecord,
)

# === Tests ====================================================================

# --- test_01_builds_main_summary_sections() -----------------------------------
def test_01_builds_main_summary_sections() -> None:
    text = module._build_summary_table(
        summary_data=_summary(),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "TEST SUMMARY" in text

    assert "Test file summary" in text
    assert "Source files covered:" in text
    assert "Test files run:" in text
    assert "Test files passed all tests:" in text

    assert "Test function summary" in text
    assert "Passed:" in text
    assert "Failed:" in text
    assert "Error:" in text
    assert "XPassed:" in text
    assert "Skipped:" in text
    assert "XFailed:" in text

    assert "Coverage" in text
    assert "Statements:" in text
    assert "80%" in text
    assert "Branches:" in text
    assert "60%" in text
    assert "Total:" in text
    assert "74%" in text


# --- test_02_includes_default_flagged_outcomes_and_test_names() ---------------
def test_02_includes_default_flagged_outcomes_and_test_names(
) -> None:


    problem = ProblemTestFileRecord(
        test_file_name="test_mixed.py",
        failed_test_function_names=["test_failed"],
        error_test_function_names=["test_error"],
        skipped_test_function_names=["test_skipped"],
        xfailed_test_function_names=["test_xfailed"],
        xpassed_test_function_names=["test_xpassed"],
    )

    text = module._build_summary_table(
        summary_data=_summary(
            problems=[problem]
        ),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "Flagged test functions by test file" in text

    assert "test_mixed.py" in text

    assert "Failed (1):" in text
    assert "test_failed" in text

    assert "Error (1):" in text
    assert "test_error" in text

    assert "XPassed (1):" in text
    assert "test_xpassed" in text

    assert "Skipped (1):" not in text
    assert "test_skipped" not in text

    assert "XFailed (1):" not in text
    assert "test_xfailed" not in text


# --- test_03_show_all_problems_includes_skipped_and_xfailed -------------------
def test_03_show_all_problems_includes_skipped_and_xfailed(
) -> None:


    problem = ProblemTestFileRecord(
        test_file_name="test_expected.py",
        failed_test_function_names=[],
        error_test_function_names=[],
        skipped_test_function_names=["test_skipped"],
        xfailed_test_function_names=["test_xfailed"],
        xpassed_test_function_names=[],
    )

    text = module._build_summary_table(
        summary_data=_summary(
            problems=[problem]
        ),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=True,
    )

    assert "Flagged test functions by test file" in text

    assert "Skipped (1):" in text
    assert "test_skipped" in text

    assert "XFailed (1):" in text
    assert "test_xfailed" in text


# --- test_04_includes_special_test_file_categories() --------------------------
def test_04_includes_special_test_file_categories() -> None:
    text = module._build_summary_table(
        summary_data=_summary(
            not_processed=[
                "test_collection_problem.py"
            ],
            no_tests_collected=[
                "test_empty.py"
            ],
        ),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "Test files not processed, often due to an import error (1):" in text
    assert "test_collection_problem.py" in text
    assert "Test files with no collected tests (1):" in text
    assert "test_empty.py" in text


# --- test_05_displays_statement_coverage_table_by_source_file() ---------------
def test_05_displays_statement_coverage_table_by_source_file() -> None:
    records = [
        _coverage_record(
            "/project/src/alpha.py",
            executed={1, 2, 3},
            total=4,
        ),
        _coverage_record(
            "/project/src/empty_init.py",
            executed=set(),
            total=0,
        ),
    ]

    text = module._build_summary_table(
        summary_data=_summary(
            coverage_records=records
        ),
        coverage_warning_threshold=None,
        show_source_file_coverage=True,
        show_skipped_and_xfailed=False,
    )

    assert "Executed/" in text
    assert "Statements" in text
    assert "Source file" in text

    assert "75%" in text
    assert "3/4" in text
    assert "alpha.py" in text

    # Source records containing no statements are omitted.
    assert "empty_init.py" not in text


# --- test_06_omits_optional_sections_when_empty() -----------------------------
def test_06_omits_optional_sections_when_empty() -> None:
    text = module._build_summary_table(
        summary_data=_summary(),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert (
        "Test files not processed, often due to "
        "import error"
        not in text
    )
    assert (
        "Test files with no collected tests"
        not in text
    )
    assert (
        "Flagged test functions by test file"
        not in text
    )

    assert "Executed/" not in text


# --- test_07_includes_warning_when_rounded_total_is_below_threshold() ---------
def test_07_includes_warning_when_rounded_total_is_below_threshold() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 84.4

    text = module._build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert (
        "WARNING: Total coverage (84%) "
        "is below recommended threshold 85%."
        in text
    )


# --- test_08_omits_warning_when_rounded_values_are_equal() --------------------
def test_08_omits_warning_when_rounded_values_are_equal() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 84.79

    text = module._build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "WARNING:" not in text


# --- test_09_omits_warning_when_threshold_is_disabled() -----------------------
def test_09_omits_warning_when_threshold_is_disabled() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 10.0

    text = module._build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "WARNING:" not in text


# --- test_10_uses_plural_file_label_for_multiple_flagged_files() --------------
def test_10_uses_plural_file_label_for_multiple_flagged_files(
) -> None:


    first = _problem_record(
        "test_first.py",
        failed=["test_first_failure"],
    )
    second = _problem_record(
        "test_second.py",
        failed=["test_second_failure"],
    )

    text = module._build_summary_table(
        summary_data=_summary(
            problems=[first, second]
        ),
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "Flagged test functions by test file (in 2 test files):" in text


# --- test_11_coverage_warning_can_be_disabled() -------------------------------
@pytest.mark.parametrize(
    "coverage_warning_threshold",
    [
        pytest.param(None, id="none"),
        pytest.param(0, id="zero"),
    ],
)
def test_11_coverage_warning_can_be_disabled(
    coverage_warning_threshold: float | None,
) -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 10.0

    text = module._build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=coverage_warning_threshold,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert "WARNING:" not in text


# --- test_12_coverage_warning_is_shown_below_threshold() ----------------------
def test_12_coverage_warning_is_shown_below_threshold() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 10.0

    text = module._build_summary_table(
        summary_data=summary_data,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=False,
    )

    assert (
        "WARNING: Total coverage (10%) "
        "is below recommended threshold 85%."
        in text
    )


# === Internal helpers ========================================================

def _problem_record(
    test_file_name: str,
    *,
    failed: list[str] | None = None,
    errors: list[str] | None = None,
    skipped: list[str] | None = None,
    xfailed: list[str] | None = None,
    xpassed: list[str] | None = None,
) -> ProblemTestFileRecord:
    return ProblemTestFileRecord(
        test_file_name=test_file_name,
        failed_test_function_names=failed or [],
        error_test_function_names=errors or [],
        skipped_test_function_names=skipped or [],
        xfailed_test_function_names=xfailed or [],
        xpassed_test_function_names=xpassed or [],
    )


def _coverage_record(
    path: str,
    *,
    executed: set[int],
    total: int,
) -> SourceFileCoverageRecord:
    all_lines = set(range(1, total + 1))

    return SourceFileCoverageRecord(
        source_file_path=path,
        executed_lines=executed,
        missing_lines=all_lines - executed,
        total_line_count=total,
        branch_source=set(),
        total_branch_pairs=set(),
        executed_branch_pairs=set(),
    )


def _summary(
    *,
    problems: list[ProblemTestFileRecord] | None = None,
    not_processed: list[str] | None = None,
    no_tests_collected: list[str] | None = None,
    coverage_records: list[
        SourceFileCoverageRecord
    ] | None = None,
) -> AggregateTestSummary:
    return AggregateTestSummary(
        source_file_count=len(
            coverage_records or []
        ),
        test_file_count=3,
        passed_test_file_count=1,
        failed_test_file_count=1,
        error_test_file_count=1,
        skipped_test_file_count=1,
        xfailed_test_file_count=1,
        xpassed_test_file_count=1,
        passed_test_function_count=8,
        failed_test_function_count=2,
        error_test_function_count=1,
        skipped_test_function_count=3,
        xfailed_test_function_count=1,
        xpassed_test_function_count=1,
        executed_line_count=80,
        total_line_count=100,
        executed_branch_count=30,
        total_branch_count=50,
        statement_coverage_pct=80.4,
        branch_coverage_pct=60.4,
        total_coverage_pct=73.6,
        problem_test_files=problems or [],
        not_processed_test_files=(
            not_processed or []
        ),
        no_tests_collected_test_files=(
            no_tests_collected or []
        ),
        source_file_coverage_records=(
            coverage_records or []
        ),
    )
