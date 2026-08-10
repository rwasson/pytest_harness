"""
dashboard_builder.py

Last edited: 2026-08-10
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from rich.markup import escape

from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    TestFileRecord,
    TestFunctionRecord,
)
from pytest_harness.dashboard_wrapper import _wrap_dashboard_text
from pytest_harness.style_helpers import (
    _build_section_heading,
    _build_summary_styles,
    _styled,
    _styled_field,
    _SummaryStyles,
)

_ROUND_DIGIT = 0
_DIVIDER_WIDTH = 40
_SLOW_TEST_FUNCTION_SECONDS = 0.5
_SLOW_TEST_FUNCTION_LIMIT = 10


# --- _build_dashboard() -------------------------------------------------------
def _build_dashboard(
    *,
    summary_data: AggregateTestSummary,
    test_function_records: tuple[TestFunctionRecord, ...],
    coverage_warning_threshold: float | None,
    show_source_file_coverage: bool,
    show_skipped_and_xfailed: bool,
    theme: Mapping[str, str],
    dashboard_width: int,
) -> str:
    """Build the pytest_harness summary dashboard."""
    divider_width = _DIVIDER_WIDTH
    round_digit = _ROUND_DIGIT
    styles = _build_summary_styles(theme)


    # --- header section ---
    lines = [
        _styled("Pytest Harness Summary", style=styles.title),
        _styled("═" * divider_width, style=styles.divider),
        (
            f'{_styled("Random-order seed: ", style=styles.sub_header)}'
            f"{summary_data.random_order_seed}"
        ),
        (
            f'{_styled("Test-function timeout (in seconds): ", style=styles.sub_header)}'
            f"{summary_data.test_function_timeout_seconds}"
        ),
        "",
        "",
    ]

    # --- test file section ---
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

    label_width = max(len(label) for label, _ in test_file_rows)
    count_width = max(len(str(count)) for _, count in test_file_rows)

    lines.extend(
        f"{label:<{label_width}}  {count:>{count_width}}"
        for label, count in test_file_rows
    )

    lines.extend(
        _build_test_file_problem_lines(
            summary_data=summary_data,
            dashboard_width=dashboard_width,
            styles=styles,
        )
    )

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
        count_text = padded_count if count == 0 else _styled(padded_count, style=style)
        lines.append(f"    {label:<10}{count_text}")

    lines.extend(
        _build_test_function_problem_lines(
            summary_data=summary_data,
            show_skipped_and_xfailed=show_skipped_and_xfailed,
            dashboard_width=dashboard_width,
            styles=styles,
        )
    )

    # --- coverage section ---
    lines.extend(["", ""])
    lines.extend(
        _build_section_heading(
            "Total coverage",
            divider="-" * divider_width,
            styles=styles,
        )
    )

    coverage_rows = [
        ("Statements:", summary_data.statement_coverage_pct),
        ("Branches:", summary_data.branch_coverage_pct),
        ("Total:", summary_data.total_coverage_pct),
    ]

    label_width = max(len(label) for label, _ in coverage_rows)

    lines.extend(
        f"    {label:<{label_width}}  {percentage:>3.{round_digit}f}%"
        for label, percentage in coverage_rows
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
                    f"{_styled('WARNING', style=styles.warning)}: Total coverage "
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
                dashboard_width=dashboard_width,
                styles=styles,
            )
        )

    lines.extend(
        _build_slowest_test_function_lines(
            test_function_records=test_function_records,
            styles=styles,
            dashboard_width=dashboard_width,
        )
    )

    return "\n".join(lines)


# === Internal helpers =========================================================

def _build_test_file_problem_lines(
    *,
    summary_data: AggregateTestSummary,
    dashboard_width: int,
    styles: _SummaryStyles,
) -> list[str]:
    lines: list[str] = []

    def wrap4(text: str) -> str:
        return _wrap_dashboard_text(text, dashboard_width=dashboard_width, indent=4)

    def wrap8(text: str) -> str:
        return _wrap_dashboard_text(text, dashboard_width=dashboard_width, indent=8)

    def wrap16(text: str) -> str:
        return _wrap_dashboard_text(text, dashboard_width=dashboard_width, indent=16)

    if summary_data.not_processed_test_files:
        heading = (
            "Test files not processed successfully "
            f"({summary_data.not_processed_test_file_count}):"
        )
        lines.extend(["", _styled(heading, style=styles.problem)])

        grouped_records: dict[str, list[TestFileRecord]] = defaultdict(list)

        for record in summary_data.not_processed_test_files:
            reason = record.not_processed_reason or "processing error"
            grouped_records[reason].append(record)

        for reason in sorted(grouped_records, key=str.casefold):
            records = grouped_records[reason]

            lines.append("    " + _styled(f"{reason.capitalize()} ({len(records)}):", style=styles.error))

            for record in sorted(records, key=lambda rec: rec.test_file_label.casefold()):
                lines.append(
                    _styled_field(
                        wrap8(record.test_file_label),
                        style=styles.file_name,
                    )
                )

                if record.timed_out_test_function_node_id is not None:
                    test_function_name = (
                        record.timed_out_test_function_node_id
                        .rsplit("::", maxsplit=1)[-1]
                    )

                    lines.append(
                        _styled_field(
                            wrap16(f"in: {test_function_name}"),
                            style=styles.muted,
                        )
                    )

    if summary_data.no_tests_collected_test_files:
        heading = (
            "Test files with no collected tests "
            f"({summary_data.no_tests_collected_test_file_count}):"
        )
        lines.extend(["", _styled(heading, style=styles.problem)])

        lines.extend(
            _styled_field(wrap4(record.test_file_label), style=styles.file_name)
            for record in sorted(
                summary_data.no_tests_collected_test_files,
                key=lambda rec: rec.test_file_label.casefold(),
            )
        )

    if summary_data.warning_test_files:
        heading = (
            "Test files with warnings (details in individual test-file logs) "
            f"({summary_data.warning_test_file_count}):"
        )
        lines.extend(["", _styled(heading, style=styles.warning)])

        for record in sorted(
            summary_data.warning_test_files,
            key=lambda rec: rec.test_file_label.casefold(),
        ):
            warning_word = "warning" if record.warning_count == 1 else "warnings"
            warning_text = (
                f"{record.test_file_label} "
                f"({record.warning_count} {warning_word})"
            )

            lines.append(_styled_field(wrap4(warning_text), style=styles.file_name))

    return lines


# --- _build_test_function_problem_lines() -------------------------------------
def _build_test_function_problem_lines(
    *,
    summary_data: AggregateTestSummary,
    show_skipped_and_xfailed: bool,
    dashboard_width: int,
    styles: _SummaryStyles,
) -> list[str]:
    if not summary_data.problem_test_files:
        return []

    def wrap4(text: str) -> str:
        return _wrap_dashboard_text(text, dashboard_width=dashboard_width, indent=4)
    def wrap12(text: str) -> str:
        return _wrap_dashboard_text(text, dashboard_width=dashboard_width, indent=12)


    problem_file_count = len(summary_data.problem_test_files)
    file_word = "file" if problem_file_count == 1 else "files"

    lines = [
        "",
        _styled(
            f"Flagged test functions (in {problem_file_count} test {file_word}):",
            style=styles.problem,
        ),
    ]

    for record in sorted(
        summary_data.problem_test_files,
        key=lambda rec: rec.test_file_label.casefold(),
    ):
        lines.append(
            _styled_field(
                wrap4(record.test_file_label),
                style=styles.file_name,
            )
        )

        if record.has_failures:
            label = f"Failed ({record.failed_test_function_count}):"
            lines.append("        " + _styled(label, style=styles.error))
            lines.extend(
                wrap12(escape(name))
                for name in sorted(
                    record.failed_test_function_names,
                    key=str.casefold,
                )
            )

        if record.has_errors:
            label = f"Error ({record.error_test_function_count}):"
            lines.append("        " + _styled(label, style=styles.error))
            lines.extend(
                wrap12(escape(name))
                for name in sorted(
                    record.error_test_function_names,
                    key=str.casefold,
                )
            )

        if record.has_xpasses:
            label = f"XPassed ({record.xpassed_test_function_count}):"
            lines.append("        " + _styled(label, style=styles.error))
            lines.extend(
                wrap12(escape(name))
                for name in sorted(
                    record.xpassed_test_function_names,
                    key=str.casefold,
                )
            )

        if show_skipped_and_xfailed and record.has_skips:
            label = f"Skipped ({record.skipped_test_function_count}):"
            lines.append("        " + _styled(label, style=styles.muted))
            lines.extend(
                wrap12(escape(name))
                for name in sorted(
                    record.skipped_test_function_names,
                    key=str.casefold,
                )
            )

        if show_skipped_and_xfailed and record.has_xfails:
            label = f"XFailed ({record.xfailed_test_function_count}):"
            lines.append("        " + _styled(label, style=styles.muted))
            lines.extend(
                wrap12(escape(name))
                for name in sorted(
                    record.xfailed_test_function_names,
                    key=str.casefold,
                )
            )

    return lines


# --- _build_source_file_coverage_lines() --------------------------------------
# --- _build_source_file_coverage_lines() --------------------------------------
def _build_source_file_coverage_lines(
    *,
    summary_data: AggregateTestSummary,
    dashboard_width: int,
    styles: _SummaryStyles,
) -> list[str]:
    records = summary_data.source_file_coverage_records

    if not records:
        return []

    # Keep numeric columns fixed so unusually large values cannot consume
    # space reserved for the source-file column.
    coverage_column_width = 12
    count_column_width = 11

    # Two spaces separate each of the three columns.
    source_column_width = (
        dashboard_width
        - coverage_column_width
        - count_column_width
        - 4
    )

    header_style = styles.header

    top_header_line = (
        f"{_styled(f"{'Source file':<{coverage_column_width}}", style=header_style)}  "
        f"{_styled(f"{'Executed/':<{count_column_width}}", style=header_style)}  "
        f"{_styled('Source', style=header_style)}"
    )

    bottom_header_line = (
        f"{_styled(f"{'coverage':<{coverage_column_width}}", style=header_style)}  "
        f"{_styled(f"{'statements':<{count_column_width}}", style=header_style)}  "
        f"{_styled('file', style=header_style)}"
    )

    divider_line = (
        f"{'-' * coverage_column_width}  "
        f"{'-' * count_column_width}  "
        f"{'-' * 14}"
    )

    lines = [
        "",
        "",
        top_header_line,
        bottom_header_line,
        _styled(divider_line, style=styles.divider),
    ]

    for record in records:
        coverage_text = f"{record.statement_coverage_pct:.0f}%"
        count_text = (
            f"{record.executed_line_count}/"
            f"{record.total_line_count}"
        )

        if len(coverage_text) > coverage_column_width:
            coverage_text = "+" * coverage_column_width

        if len(count_text) > count_column_width:
            count_text = "+" * count_column_width

        wrapped_source_lines = _wrap_dashboard_text(
            escape(record.relative_source_file_path),
            dashboard_width=source_column_width,
            indent=0,
        ).splitlines()

        lines.append(
            f"{coverage_text:<{coverage_column_width}}  "
            f"{count_text:<{count_column_width}}  "
            f"{wrapped_source_lines[0]}"
        )

        lines.extend(
            f"{'':<{coverage_column_width}}  "
            f"{'':<{count_column_width}}  "
            f"{source_line}"
            for source_line in wrapped_source_lines[1:]
        )

    return lines


def _fit_count_text(
    text: str,
    *,
    width: int,
) -> str:
    if len(text) <= width:
        return text

    return "+" * width


# --- _build_slowest_test_function_lines() -------------------------------------
def _build_slowest_test_function_lines(
    *,
    test_function_records: tuple[TestFunctionRecord, ...],
    styles: _SummaryStyles,
    dashboard_width: int,
) -> list[str]:
    slow_records = sorted(
        (
            record
            for record in test_function_records
            if (
                record.duration_seconds is not None
                and record.duration_seconds >= _SLOW_TEST_FUNCTION_SECONDS
            )
        ),
        key=lambda record: record.duration_seconds or 0.0,
        reverse=True,
    )[:_SLOW_TEST_FUNCTION_LIMIT]

    if not slow_records:
        return []

    lines = [
        "",
        "",
        _styled(
            "Slowest test functions",
            style=styles.title,
        ),
        _styled(
            "-" * _DIVIDER_WIDTH,
            style=styles.divider,
        ),
    ]

    duration_width = max(
        len(f"{record.duration_seconds:.2f} s")
        for record in slow_records
        if record.duration_seconds is not None
    )

    node_id_indent = duration_width + 2

    for record in slow_records:
        assert record.duration_seconds is not None

        duration_text = f"{record.duration_seconds:.2f} s"

        wrapped_node_id_lines = _wrap_dashboard_text(
            escape(record.node_id),
            dashboard_width=dashboard_width,
            indent=node_id_indent,
        ).splitlines()

        # _wrap_dashboard_text() applies the indent itself. Strip it from
        # the first line so the duration can occupy that space.
        first_node_line = wrapped_node_id_lines[0][node_id_indent:]

        lines.append(
            f"{duration_text:>{duration_width}}  "
            f"{first_node_line}"
        )

        lines.extend(
            wrapped_node_id_lines[1:]
        )

    return lines

