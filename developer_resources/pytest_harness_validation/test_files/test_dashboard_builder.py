"""
test_dashboard_builder.py

Last edited: 2026-08-07
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.text import Text

import pytest_harness.dashboard_builder as module
from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    DEFAULT_DASHBOARD_WIDTH,
    SourceFileCoverageRecord,
    TestFileRecord,
    TestFileStatus,
    TestFunctionRecord,
)

_TEST_THEME: dict[str, str] = {
    "title": "bold bright_blue",
    "header_label": "bright_blue",
    "header_value": "grey37",
    "text": "black",
    "muted": "grey39",
    "divider": "blue3",
    "pipe": "grey70",
    "sink_tag": "bright_blue",
    "critical": "bold red3",
    "error": "red3",
    "warning": "bold gold3",
    "success": "green",
    "info": "grey39",
    "debug": "bold magenta",
    "trace": "grey39",
}


# === Tests ===================================================================

# --- test_01_builds_main_summary_sections() -----------------------------------
def test_01_builds_main_summary_sections() -> None:
    text = _build_plain_dashboard(
        summary_data=_summary(),
    )

    assert "Pytest Harness Summary" in text
    assert "Random-order seed:" in text
    assert "1234" in text
    assert "Test-function timeout (in seconds):" in text
    assert "2.0" in text

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

    assert "Total coverage" in text
    assert "Statements:" in text
    assert "80%" in text
    assert "Branches:" in text
    assert "60%" in text
    assert "Total:" in text
    assert "74%" in text


# --- test_02_includes_default_flagged_outcomes() ------------------------------
def test_02_includes_default_flagged_outcomes() -> None:
    problem = _test_file_record(
        "test_mixed.py",
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            problem_test_files=[problem],
        ),
    )

    assert "Flagged test functions" in text
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


# --- test_03_can_show_skipped_and_xfailed() -----------------------------------
def test_03_can_show_skipped_and_xfailed() -> None:
    problem = _test_file_record(
        "test_expected.py",
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            problem_test_files=[problem],
        ),
        show_skipped_and_xfailed=True,
    )

    assert "Skipped (1):" in text
    assert "test_skipped" in text

    assert "XFailed (1):" in text
    assert "test_xfailed" in text


# --- test_04_includes_special_test_file_categories() --------------------------
def test_04_includes_special_test_file_categories() -> None:
    not_processed = _test_file_record(
        "test_collection_problem.py",
        status=TestFileStatus.NOT_PROCESSED,
        not_processed_reason="collection error",
        file_error_message="Test collection failed.",
        test_functions=[]
    )

    empty = _test_file_record(
        "test_empty.py",
        status=TestFileStatus.NO_TESTS_COLLECTED,
        test_functions=[]
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            not_processed_test_files=[not_processed],
            no_tests_collected_test_files=[empty],
        ),
    )

    assert "Test files not processed successfully (1):" in text
    assert "test_collection_problem.py" in text
    assert "Collection error (1):" in text
    assert "Test files with no collected tests (1):" in text
    assert "test_empty.py" in text


# --- test_05_displays_timeout_test_function() ---------------------------------
def test_05_displays_timeout_test_function() -> None:
    timed_out = _test_file_record(
        "nested/test_timeout.py",
        status=TestFileStatus.NOT_PROCESSED,
        not_processed_reason="test function timed out",
        file_error_message="Test function timed out.",
        timed_out_test_function_node_id=(
            "nested/test_timeout.py::test_too_slow"
        ),
        test_functions=[]
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            not_processed_test_files=[timed_out],
        ),
    )

    assert "nested/test_timeout.py" in text
    assert "Test function timed out (1):" in text
    assert "in: test_too_slow" in text


# --- test_06_displays_source_file_coverage() ----------------------------------
def test_06_displays_source_file_coverage() -> None:
    records = [
        _coverage_record(
            "/project/src/alpha.py",
            executed={1, 2, 3},
            total=4,
        ),
    ]

    text = _build_plain_dashboard(
        summary_data=_summary(
            coverage_records=records,
        ),
        show_source_file_coverage=True,
    )

    assert "Executed/" in text
    assert "Statements" in text
    assert "Source file" in text
    assert "75%" in text
    assert "3/4" in text
    assert "alpha.py" in text


# --- test_07_omits_optional_sections_when_empty() -----------------------------
def test_07_omits_optional_sections_when_empty() -> None:
    text = _build_plain_dashboard(
        summary_data=_summary(),
        show_source_file_coverage=False,
    )

    assert "Test files not processed" not in text
    assert "Test files with no collected tests" not in text
    assert "Test files with warnings" not in text
    assert "Flagged test functions" not in text
    assert "Executed/" not in text


# --- test_08_shows_coverage_warning_below_threshold() -------------------------
def test_08_shows_coverage_warning_below_threshold() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 84.4

    text = _build_plain_dashboard(
        summary_data=summary_data,
        coverage_warning_threshold=85.0,
    )

    assert "WARNING:" in text
    assert "Total coverage (84%)" in text
    assert "recommended threshold 85%" in text


# --- test_09_omits_warning_when_rounded_values_are_equal() --------------------
def test_09_omits_warning_when_rounded_values_are_equal() -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 84.79

    text = _build_plain_dashboard(
        summary_data=summary_data,
        coverage_warning_threshold=85.0,
    )

    assert "WARNING:" not in text


# --- test_10_coverage_warning_can_be_disabled() -------------------------------
@pytest.mark.parametrize(
    "coverage_warning_threshold",
    [
        pytest.param(None, id="none"),
        pytest.param(0, id="zero"),
    ],
)
def test_10_coverage_warning_can_be_disabled(
    coverage_warning_threshold: float | None,
) -> None:
    summary_data = _summary()
    summary_data.total_coverage_pct = 10.0

    text = _build_plain_dashboard(
        summary_data=summary_data,
        coverage_warning_threshold=coverage_warning_threshold,
    )

    assert "WARNING:" not in text


# --- test_11_uses_plural_for_multiple_flagged_files() -------------------------
def test_11_uses_plural_for_multiple_flagged_files() -> None:
    first = _test_file_record(
        "test_first.py",
        test_functions=[]
    )
    second = _test_file_record(
        "test_second.py",
        test_functions=[]
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            problem_test_files=[first, second],
        ),
    )

    assert "Flagged test functions (in 2 test files):" in text


# --- test_12_sorts_problem_files_and_test_functions ---
def test_12_sorts_problem_files_and_test_functions() -> None:
    z_file = _test_file_record(
        "z_tests/test_z.py",
        test_functions=[
            ("test_delta", "failed"),
            ("test_beta", "failed"),
            ("test_zebra", "error"),
            ("test_alpha", "error"),
        ],
    )

    a_file = _test_file_record(

        "a_tests/test_a.py",

        test_functions=[
            ("test_delta", "failed"),
            ("test_beta", "failed"),
            ("test_zebra", "error"),
            ("test_alpha", "error"),
        ],
    )

    text = _build_plain_dashboard(
        summary_data=_summary(problem_test_files=[z_file, a_file]),
    )

    assert text.index("a_tests/test_a.py") < text.index("z_tests/test_z.py")
    assert text.index("test_beta") < text.index("test_delta")
    assert text.index("test_alpha") < text.index("test_zebra")


# --- test_13_sorts_special_test_file_lists() ----------------------------------
def test_13_sorts_special_test_file_lists() -> None:
    first = _test_file_record(
        "z_test.py",
        status=TestFileStatus.NOT_PROCESSED,
        not_processed_reason="processing error",
        file_error_message="error",
    )
    second = _test_file_record(
        "a_test.py",
        status=TestFileStatus.NOT_PROCESSED,
        not_processed_reason="processing error",
        file_error_message="error",
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            not_processed_test_files=[first, second],
        ),
    )

    assert text.index("a_test.py") < text.index("z_test.py")


# --- test_14_displays_warning_files ---
def test_14_displays_warning_files() -> None:
    record = _test_file_record(
        "test_warning.py",
        warning_messages=[
            "warning one",
            "warning two",
        ],
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            warning_test_files=[record],
        ),
    )

    assert "Test files with warnings" in text
    assert "test_warning.py" in text
    assert "(2 warnings)" in text


def test_15_source_coverage_wraps_long_source_file_within_dashboard_width() -> None:
    record = _coverage_record(
        "/project/src/a_very_long_directory_name/"
        "another_long_directory_name/"
        "very_long_source_file_name.py",
        executed={1, 2, 3},
        total=4,
    )

    text = _build_plain_dashboard(
        summary_data=_summary(coverage_records=[record]),
        show_source_file_coverage=True,
        dashboard_width=80,
    )

    lines = text.splitlines()

    assert all(
        len(line) <= 80
        for line in lines
    )


def test_16_source_coverage_count_overflow_does_not_expand_column() -> None:
    record = _coverage_record(
        "/project/src/example.py",
        executed={1, 2, 3},
        total=9_876_543_210,
    )

    text = _build_plain_dashboard(
        summary_data=_summary(
            coverage_records=[record],
        ),
        show_source_file_coverage=True,
        dashboard_width=80,
    )

    assert "+" * 11 in text
    assert "12345678/987654321" not in text


def test_17_displays_only_genuinely_slow_test_functions() -> None:
    test_function_records = (
        TestFunctionRecord(
            node_id="tests/test_one.py::test_slow",
            outcome="passed",
            duration_seconds=2.5,
        ),
        TestFunctionRecord(
            node_id="tests/test_two.py::test_fast",
            outcome="passed",
            duration_seconds=0.1,
        ),
    )

    text = _build_plain_dashboard(
        summary_data=_summary(),
        test_function_records=test_function_records,
    )

    assert "Slowest test functions" in text
    assert "test_slow" in text
    assert "2.50 s" in text
    assert "test_fast" not in text


# === Internal helpers =========================================================

def _test_file_record(
    test_file_label: str,
    *,
    status: TestFileStatus = TestFileStatus.PROCESSED,
    test_file_exit_code: int = 0,
    timed_out_test_function_node_id: str | None = None,
    not_processed_reason: str | None = None,
    file_error_message: str | None = None,
    warning_messages: list[str] | None = None,
    test_functions: list[tuple[str, str]] | None = None,
) -> TestFileRecord:

    if test_functions is None:
        test_functions = [
            ("test_passed", "passed"),
            ("test_failed", "failed"),
            ("test_error", "error"),
            ("test_skipped", "skipped"),
            ("test_xfailed", "xfailed"),
            ("test_xpassed", "xpassed"),
        ]

    test_function_records = [
        TestFunctionRecord(
            node_id=f"{test_file_label}::{name}",
            outcome=outcome,
        )
        for name, outcome in test_functions
    ]

    test_function_node_ids = [
        record.node_id
        for record in test_function_records
    ]

    return TestFileRecord(
        test_file_path=Path("/project/tests") / test_file_label,
        test_file_label=test_file_label,
        test_file_exit_code=test_file_exit_code,
        duration_seconds=0.1,
        status=status,
        timed_out_test_function_node_id=timed_out_test_function_node_id,
        not_processed_reason=not_processed_reason,
        file_error_message=file_error_message,
        warning_messages=warning_messages or [],
        collected_test_function_node_ids=test_function_node_ids,
        started_test_function_node_ids=test_function_node_ids,
        test_function_records=test_function_records,
    )


def _coverage_record(
    path: str,
    *,
    executed: set[int],
    total: int,
) -> SourceFileCoverageRecord:

    return SourceFileCoverageRecord(
        source_file_path=path,
        relative_source_file_path=Path(path).name,
        executed_lines=executed,
        missing_lines=set(),
        total_line_count=total,
        branch_source=set(),
        total_branch_pairs=set(),
        executed_branch_pairs=set(),
    )


def _summary(
    *,
    random_order_seed: int | None = 1234,
    test_function_timeout_seconds: float | None = 2.0,
    problem_test_files: list[TestFileRecord] | None = None,
    not_processed_test_files: list[TestFileRecord] | None = None,
    no_tests_collected_test_files: list[TestFileRecord] | None = None,
    warning_test_files: list[TestFileRecord] | None = None,
    coverage_records: list[SourceFileCoverageRecord] | None = None,
) -> AggregateTestSummary:
    visible_coverage_records = [
        record
        for record in (coverage_records or [])
        if record.total_line_count > 0
    ]

    return AggregateTestSummary(
        random_order_seed=random_order_seed,
        test_function_timeout_seconds=test_function_timeout_seconds,

        source_file_count=len(visible_coverage_records),
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

        problem_test_files=problem_test_files or [],
        not_processed_test_files=not_processed_test_files or [],
        no_tests_collected_test_files=no_tests_collected_test_files or [],
        warning_test_files=warning_test_files or [],
        source_file_coverage_records=visible_coverage_records,
    )


def _build_plain_dashboard(
    *,
    summary_data: AggregateTestSummary,
    test_function_records: tuple[TestFunctionRecord, ...] = (),
    coverage_warning_threshold: float | None = None,
    show_source_file_coverage: bool = False,
    show_skipped_and_xfailed: bool = False,
    dashboard_width: int = DEFAULT_DASHBOARD_WIDTH
) -> str:
    markup = module._build_dashboard(
        summary_data=summary_data,
        test_function_records=test_function_records,
        coverage_warning_threshold=coverage_warning_threshold,
        show_source_file_coverage=show_source_file_coverage,
        show_skipped_and_xfailed=show_skipped_and_xfailed,
        theme=_TEST_THEME,
        dashboard_width=dashboard_width
    )

    return Text.from_markup(markup).plain
