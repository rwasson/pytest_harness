"""
summary_table_builder.py

Last edited: 2026-07-16
"""

from pathlib import Path

from pytest_harness.constants_and_classes import AggregateTestSummary


# --- _build_summary_table() ----------------------------------------------
def _build_summary_table(
    *,
    summary_data: AggregateTestSummary,
    coverage_warning_threshold: float | None,
    show_source_file_coverage: bool,
    show_skipped_and_xfailed: bool,
) -> str:
    """
    Builds text string for reporting testing output from an instance of
    AggregateTestSummary.
    """
    round_digit = 0
    divider_width = 60

    # --- test file section ---
    lines = [
        "═" * divider_width,
        "TEST SUMMARY".center(divider_width),
        "═" * divider_width,
        "",
        "Test file summary",
        "-" * divider_width,
        f"Source files covered:         {summary_data.source_file_count}",
        f"Test files run:               {summary_data.test_file_count}",
        f"Test files passed all tests:  {summary_data.passed_test_file_count}",
    ]

    lines.extend(_build_test_file_problem_lines(summary_data=summary_data))

    # --- test function section ---
    lines.extend(
        [
            "",
            "",
            "Test function summary",
            "-" * divider_width,
        ]
    )

    outcome_rows = [
        ("Passed:", summary_data.passed_test_function_count),
        ("Failed:", summary_data.failed_test_function_count),
        ("Error:", summary_data.error_test_function_count),
        ("XPassed:", summary_data.xpassed_test_function_count),
        ("Skipped:", summary_data.skipped_test_function_count),
        ("XFailed:", summary_data.xfailed_test_function_count),
    ]

    label_width = max(len(label) for label, _ in outcome_rows)
    count_width = max(len(str(count)) for _, count in outcome_rows)

    for label, count in outcome_rows:
        lines.append(
            f"    {label:<{label_width}}  {count:>{count_width}}"
        )

    lines.extend(
        _build_test_function_problem_lines(
            summary_data=summary_data,
            show_skipped_and_xfailed=show_skipped_and_xfailed,
        )
    )

    # --- Coverage section ---
    lines.extend(
        [
            "",
            "Coverage",
            "-" * divider_width,
        ]
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

    rounded_total = round(
        summary_data.total_coverage_pct,
        round_digit,
    )

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
                    "WARNING: Total coverage "
                    f"({rounded_total:.{round_digit}f}%) "
                    "is below recommended threshold "
                    f"{rounded_threshold:.{round_digit}f}%."
                ),
            ]
        )

    if show_source_file_coverage:
        lines.extend(
            _build_source_file_coverage_lines(
                summary_data=summary_data,
            )
        )

    return "\n".join(lines)


# === Internal helpers =========================================================
def _build_test_file_problem_lines(
    *,
    summary_data: AggregateTestSummary,
) -> list[str]:
    lines: list[str] = []

    if summary_data.not_processed_test_files:
        lines.extend(
            [
                "",
                (
                    "Test files not processed, often due to an import error "
                    f"({summary_data.not_processed_test_file_count}):"
                ),
            ]
        )

        lines.extend(
            f"    {test_file_name}"
            for test_file_name
            in summary_data.not_processed_test_files
        )

    if summary_data.no_tests_collected_test_files:
        lines.extend(
            [
                "",
                (
                    "Test files with no collected tests "
                    f"({summary_data.no_tests_collected_test_file_count}):"
                ),
            ]
        )

        lines.extend(
            f"    {test_file_name}"
            for test_file_name
            in summary_data.no_tests_collected_test_files
        )

    return lines


def _build_test_function_problem_lines(
    *,
    summary_data: AggregateTestSummary,
    show_skipped_and_xfailed: bool,
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
            f"    {problem_record.test_file_name}"
        )

        if problem_record.has_failures:
            lines.append(
                "        Failed "
                f"({problem_record.failed_test_count}):"
            )
            lines.extend(
                f"            {test_name}"
                for test_name
                in problem_record.failed_test_function_names
            )

        if problem_record.has_errors:
            lines.append(
                "        Error "
                f"({problem_record.error_test_count}):"
            )
            lines.extend(
                f"            {test_name}"
                for test_name
                in problem_record.error_test_function_names
            )

        if problem_record.has_xpasses:
            lines.append(
                "        XPassed "
                f"({problem_record.xpassed_test_count}):"
            )
            lines.extend(
                f"            {test_name}"
                for test_name
                in problem_record.xpassed_test_function_names
            )

        if (
            show_skipped_and_xfailed
            and problem_record.has_skips
        ):
            lines.append(
                "        Skipped "
                f"({problem_record.skipped_test_count}):"
            )
            lines.extend(
                f"            {test_name}"
                for test_name
                in problem_record.skipped_test_function_names
            )

        if (
            show_skipped_and_xfailed
            and problem_record.has_xfails
        ):
            lines.append(
                "        XFailed "
                f"({problem_record.xfailed_test_count}):"
            )
            lines.extend(
                f"            {test_name}"
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
            f"{Path(record.source_file_path).name}"
        )

    return lines
