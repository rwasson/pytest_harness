"""
summary_table_builder.py

Last edited: 2026-07-16
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from rich.markup import escape

from pytest_harness.constants_and_classes import (
    _DIVIDER_WIDTH,
    _ROUND_DIGIT,
    AggregateTestSummary,
)
from pytest_harness.style_helpers import (
    _build_section_heading,
    _build_summary_styles,
    _styled,
    _styled_field,
    _SummaryStyles,
)


# --- _build_summary_table() ----------------------------------------------
def _build_summary_table(
    *,
    summary_data: AggregateTestSummary,
    coverage_warning_threshold: float | None,
    show_source_file_coverage: bool,
    show_skipped_and_xfailed: bool,
    theme: Mapping[str, str],
) -> str:
    """
    Builds text string for reporting testing output from an instance of
    AggregateTestSummary.
    """
    divider_width = _DIVIDER_WIDTH
    round_digit = _ROUND_DIGIT
    styles = _build_summary_styles(theme)


    # --- test file section ---
    lines = [
        _styled("═" * divider_width, style=styles.divider),
        _styled("TEST SUMMARY".center(divider_width),style=styles.title),
        _styled("═" * divider_width, style=styles.divider ),
        "",
        "",
    ]

    lines.extend(
        _build_section_heading(
            "Test file summary",
            divider="-" * divider_width,
            styles=styles,
        )
    )

    test_file_rows = [
        ("Source files covered:", summary_data.source_file_count),
        ("Test files run:", summary_data.test_file_count),
        ("Test files passed all tests:", summary_data.passed_test_file_count),
    ]

    test_file_label_width = max(
        len(label)
        for label, _ in test_file_rows
    )

    test_file_count_width = max(
        len(str(count))
        for _, count in test_file_rows
    )

    for label, count in test_file_rows:
        lines.append(
            f"{label:<{test_file_label_width}}  "
            f"{count:>{test_file_count_width}}"
        )

    lines.extend(_build_test_file_problem_lines(
        summary_data=summary_data,
        styles=styles,
    ))

    # --- test function section ---
    lines.extend(["", ""])
    lines.extend(
        _build_section_heading(
            "Test function summary",
            divider="-" * divider_width,
            styles=styles,
        )
    )
    outcome_rows = [
        ("Passed:", summary_data.passed_test_function_count, theme["success"]),
        ("Failed:", summary_data.failed_test_function_count, theme["error"]),
        ("Error:", summary_data.error_test_function_count, theme["error"]),
        ("XPassed:", summary_data.xpassed_test_function_count, theme["error"]),
        ("Skipped:", summary_data.skipped_test_function_count, theme["muted"]),
        ("XFailed:", summary_data.xfailed_test_function_count, theme["muted"]),
    ]

    for label, count, style in outcome_rows:
        padded_count = f"{count:>4}"

        count_text = (
            padded_count
            if count == 0
            else _styled(
                padded_count,
                style=style,
            )
        )

        lines.append(
            f"    {label:<10}"
            f"{count_text}"
        )

    lines.extend(
        _build_test_function_problem_lines(
            summary_data=summary_data,
            show_skipped_and_xfailed=show_skipped_and_xfailed,
            styles=styles,
        )
    )

    # --- Coverage section ---
    lines.extend(["", ""])
    lines.extend(
        _build_section_heading(
            "Coverage",
            divider="-" * divider_width,
            styles=styles,
        )
    )
    coverage_rows = [
        ("Statements:", summary_data.statement_coverage_pct),
        ("Branches:", summary_data.branch_coverage_pct),
        ("Total:", summary_data.total_coverage_pct),
    ]

    coverage_label_width = max(
        len(label)
        for label, _ in coverage_rows
    )

    for label, percentage in coverage_rows:
        lines.append(
            f"    {label:<{coverage_label_width}}  "
            f"{percentage:>3.{round_digit}f}%"
        )

    rounded_total = round(summary_data.total_coverage_pct, round_digit)

    rounded_threshold = (
        round(coverage_warning_threshold, round_digit)
        if coverage_warning_threshold is not None
        else None
    )

    if rounded_threshold is not None and rounded_total < rounded_threshold:
        lines.extend(
            [
                "",
                (
                    f"{_styled("WARNING", style=styles.warning)}: Total coverage "
                    f"({rounded_total:.{round_digit}f}%) "
                    "is below recommended threshold "
                    f"{rounded_threshold:.{round_digit}f}%."
                ),
            ]
        )

    if show_source_file_coverage:
        lines.extend(_build_source_file_coverage_lines(summary_data=summary_data))

    return "\n".join(lines)


# === Internal helpers =========================================================
def _build_test_file_problem_lines(
    *,
    summary_data: AggregateTestSummary,
    styles: _SummaryStyles,
) -> list[str]:
    lines: list[str] = []

    if summary_data.not_processed_test_files:
        heading = (
            "Test files not processed, often due to an import error "
            f"({summary_data.not_processed_test_file_count}):"
        )

        lines.extend(["", _styled(heading, style=styles.problem,)])
        lines.extend(
            "    "
            + _styled_field(test_file_name, style=styles.file_name)
            for test_file_name
            in summary_data.not_processed_test_files
        )

    if summary_data.no_tests_collected_test_files:
        heading = (
            "Test files with no collected tests "
            f"({summary_data.no_tests_collected_test_file_count}):"
        )

        lines.extend(["", _styled(heading, style=styles.problem )])
        lines.extend(
            "    "
            + _styled_field(
                test_file_name,
                style=styles.file_name,
            )
            for test_file_name
            in summary_data.no_tests_collected_test_files
        )

    return lines



def _build_test_function_problem_lines(
    *,
    summary_data: AggregateTestSummary,
    show_skipped_and_xfailed: bool,
    styles: _SummaryStyles,
) -> list[str]:
    if not summary_data.problem_test_files:
        return []

    problem_file_count = len(
        summary_data.problem_test_files
    )

    file_word = (
        "file"
        if problem_file_count == 1
        else "files"
    )

    lines = [
        "",
        (
            "Flagged test functions "
            f"(in {problem_file_count} test {file_word}):"
        ),
    ]

    for problem_record in summary_data.problem_test_files:
        lines.append(
            "    "
            + _styled_field(problem_record.test_file_name, style=styles.file_name)
        )

        if problem_record.has_failures:
            label = (
                "Failed "
                f"({problem_record.failed_test_count}):"
            )
            lines.append(
                "        "
                + _styled(label, style=styles.problem)
            )
            lines.extend(
                f"            {escape(test_name)}"
                for test_name
                in problem_record.failed_test_function_names
            )

        if problem_record.has_errors:
            label = (
                "Error "
                f"({problem_record.error_test_count}):"
            )
            lines.append(
                "        "
                + _styled(label, style=styles.problem)
            )
            lines.extend(
                f"            {escape(test_name)}"
                for test_name
                in problem_record.error_test_function_names
            )

        if problem_record.has_xpasses:
            label = (
                "XPassed "
                f"({problem_record.xpassed_test_count}):"
            )
            lines.append(
                "        "
                + _styled(label, style=styles.problem)
            )
            lines.extend(
                f"            {escape(test_name)}"
                for test_name
                in problem_record.xpassed_test_function_names
            )

        if (
            show_skipped_and_xfailed
            and problem_record.has_skips
        ):
            label = (
                "Skipped "
                f"({problem_record.skipped_test_count}):"
            )
            lines.append(
                "        "
                + _styled(label, style=styles.muted)
            )
            lines.extend(
                f"            {escape(test_name)}"
                for test_name
                in problem_record.skipped_test_function_names
            )

        if (
            show_skipped_and_xfailed
            and problem_record.has_xfails
        ):
            label = (
                "XFailed "
                f"({problem_record.xfailed_test_count}):"
            )
            lines.append(
                "        "
                + _styled(label, style=styles.muted)
            )
            lines.extend(
                f"            {escape(test_name)}"
                for test_name
                in problem_record.xfailed_test_function_names
            )

    return lines


def _build_source_file_coverage_lines(
    *,
    summary_data: AggregateTestSummary,
) -> list[str]:
    visible_records = [
        record
        for record in summary_data.source_file_coverage_records
        if record.total_line_count > 0
    ]

    if not visible_records:
        return []

    coverage_values = [
        f"{record.statement_coverage_pct:.0f}%"
        for record in visible_records
    ]

    count_values = [
        (
            f"{record.executed_line_count}"
            f"/"
            f"{record.total_line_count}"
        )
        for record in visible_records
    ]

    coverage_width = max(
        [
            len("Coverage"),
            *(len(value) for value in coverage_values),
        ]
    )

    count_width = max(
        [
            len("Statements"),
            *(len(value) for value in count_values),
        ]
    )

    lines = [
        "",
        "",
        f"{'Source':<{coverage_width}}",
        (
            f"{'file':<{coverage_width}}  "
            f"{'Executed/':<{count_width}}"
        ),
        (
            f"{'Coverage':<{coverage_width}}  "
            f"{'Statements':<{count_width}}  "
            f"Source file"
        ),
        (
            f"{'-' * coverage_width}  "
            f"{'-' * count_width}  "
            f"{'-' * len('Source file')}"
        ),
    ]

    for record, coverage_text, count_text in zip(
        visible_records,
        coverage_values,
        count_values,
        strict=True,
    ):
        lines.append(
            f"{coverage_text:<{coverage_width}}  "
            f"{count_text:<{count_width}}  "
            f"{escape(Path(record.source_file_path).name)}"
        )

    return lines


