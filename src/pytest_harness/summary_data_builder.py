"""
summary_data_builder.py

Last edited: 2026-07-14
"""
import json
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import NoDataError

from pytest_harness.constants_and_classes import (
    AggregateTestSummary,
    CombinedCoverageResult,
    NotProcessedTestFileRecord,
    ProblemTestFileRecord,
    SourceFileCoverageRecord,
    TestFileRecord,
    TestFileStatus,
    WarningTestFileRecord,
)


# --- _build_summary_data() -----------------------------------
def _build_summary_data(  # noqa: PLR0915
    *,
    pytest_test_file_records: list[TestFileRecord],
    combined_coverage_result: CombinedCoverageResult,
    test_file_dir: Path,
    show_skipped_and_xfailed: bool,
    debug_pytest_harness: bool,
) -> AggregateTestSummary:
    """
    Build aggregate test and official combined coverage summary data.
    """
    warning_test_files: list[WarningTestFileRecord] = []
    test_file_dir = test_file_dir.resolve()
    test_file_count = len(pytest_test_file_records)

    passed_test_function_count = 0
    failed_test_function_count = 0
    error_test_function_count = 0
    skipped_test_function_count = 0
    xfailed_test_function_count = 0
    xpassed_test_function_count = 0

    passed_test_file_count = 0
    failed_test_file_count = 0
    error_test_file_count = 0
    skipped_test_file_count = 0
    xfailed_test_file_count = 0
    xpassed_test_file_count = 0

    problem_test_files: list[ProblemTestFileRecord] = []
    not_processed_test_files: list[NotProcessedTestFileRecord] = []
    no_tests_collected_test_files: list[str] = []

    for test_file_record in pytest_test_file_records:
        passed_test_function_count += test_file_record.passed_test_function_count
        failed_test_function_count += test_file_record.failed_test_function_count
        error_test_function_count += test_file_record.error_test_function_count
        skipped_test_function_count += test_file_record.skipped_test_function_count
        xfailed_test_function_count += test_file_record.xfailed_test_function_count
        xpassed_test_function_count += test_file_record.xpassed_test_function_count

        test_file_path = Path(test_file_record.test_file_path).resolve()
        try:
            test_file_name = test_file_path.relative_to(test_file_dir).as_posix()
        except ValueError as exc:
            raise RuntimeError(
                "PYTEST HARNESS INTERNAL ERROR:\n"
                "Test file record is outside the configured test directory:\n"
                f"    Test file: {test_file_path}\n"
                f"    Test directory: {test_file_dir}"
            ) from exc

        if test_file_record.status is TestFileStatus.NO_TESTS_COLLECTED:
            no_tests_collected_test_files.append(test_file_name)

        elif test_file_record.status is TestFileStatus.NOT_PROCESSED:
            not_processed_test_files.append(
                NotProcessedTestFileRecord(
                    relative_test_file_path=test_file_name,
                    not_processed_reason=(
                        test_file_record.not_processed_reason or "processing error"),
                    file_error_message=(
                            test_file_record.file_error_message
                            or "No additional error information was reported."
                    ),
                )
            )

        problem_record = ProblemTestFileRecord(
            test_file_name=test_file_name,
            failed_test_function_names=test_file_record.failed_test_function_names,
            error_test_function_names=test_file_record.error_test_function_names,
            skipped_test_function_names=test_file_record.skipped_test_function_names,
            xfailed_test_function_names=test_file_record.xfailed_test_function_names,
            xpassed_test_function_names=test_file_record.xpassed_test_function_names,
        )

        if problem_record.has_failures:
            failed_test_file_count += 1
        if problem_record.has_errors:
            error_test_file_count += 1
        if problem_record.has_skips:
            skipped_test_file_count += 1
        if problem_record.has_xfails:
            xfailed_test_file_count += 1
        if problem_record.has_xpasses:
            xpassed_test_file_count += 1

        # show_skipped_and_xfailed controls detailed Skipped and XFailed entries.
        has_displayed_problems = (
            problem_record.has_failures
            or problem_record.has_errors
            or problem_record.has_xpasses
            or (show_skipped_and_xfailed and (problem_record.has_skips or problem_record.has_xfails)
            )
        )

        if has_displayed_problems:
            problem_test_files.append(problem_record)

        all_tests_passed = (
            test_file_record.status is TestFileStatus.PROCESSED
            and 0 < test_file_record.total_test_function_count == test_file_record.passed_test_function_count
        )


        if all_tests_passed:
            passed_test_file_count += 1

        if test_file_record.warning_count > 0:
            warning_test_files.append(
                WarningTestFileRecord(
                    relative_test_file_path=test_file_name,
                    warning_count=test_file_record.warning_count,
                )
            )

    source_file_coverage_records = sorted(
        (
            record
            for record
            in combined_coverage_result.source_file_coverage_records.values()
            if record.total_line_count > 0
        ),
        key=lambda record: record.statement_coverage_pct,
    )

    executed_line_count = combined_coverage_result.executed_line_count
    total_line_count = combined_coverage_result.total_line_count
    executed_branch_count = combined_coverage_result.executed_branch_count
    total_branch_count = combined_coverage_result.total_branch_count

    statement_coverage_pct = combined_coverage_result.statement_coverage_pct
    branch_coverage_pct = combined_coverage_result.branch_coverage_pct
    total_coverage_pct = combined_coverage_result.total_coverage_pct

    if debug_pytest_harness:
        print("Official combined Coverage.py counts of: executed / total")
        print(
            f"statements: {executed_line_count} / "
            f"{total_line_count}"
        )
        print(
            f"branches:   {executed_branch_count} / "
            f"{total_branch_count}\n"
        )

    return AggregateTestSummary(
        source_file_count=len(source_file_coverage_records),
        test_file_count=test_file_count,
        passed_test_file_count=passed_test_file_count,
        failed_test_file_count=failed_test_file_count,
        error_test_file_count=error_test_file_count,
        skipped_test_file_count=skipped_test_file_count,
        xfailed_test_file_count=xfailed_test_file_count,
        xpassed_test_file_count=xpassed_test_file_count,
        passed_test_function_count=passed_test_function_count,
        failed_test_function_count=failed_test_function_count,
        error_test_function_count=error_test_function_count,
        skipped_test_function_count=skipped_test_function_count,
        xfailed_test_function_count=xfailed_test_function_count,
        xpassed_test_function_count=xpassed_test_function_count,
        executed_line_count=executed_line_count,
        total_line_count=total_line_count,
        executed_branch_count=executed_branch_count,
        total_branch_count=total_branch_count,

        statement_coverage_pct=statement_coverage_pct,
        branch_coverage_pct=branch_coverage_pct,
        total_coverage_pct=total_coverage_pct,

        problem_test_files=problem_test_files,
        no_tests_collected_test_files=no_tests_collected_test_files,
        not_processed_test_files=not_processed_test_files,
        warning_test_files=warning_test_files,
        source_file_coverage_records=source_file_coverage_records,
    )

# --- _combine_coverage_data_files() ------------------------------------------
def _combine_coverage_data_files(
    *,
    coverage_temp_dir_path: Path,
    tested_code_dir: Path,
) -> CombinedCoverageResult:
    """Combine per-test-file coverage data and return official totals."""

    combined_data_file_path = coverage_temp_dir_path / ".coverage"
    combined_json_file_path = coverage_temp_dir_path / "combined_coverage.json"

    coverage_obj = Coverage(
        data_file=str(combined_data_file_path),
        branch=True,
    )

    try:
        coverage_obj.combine(
            data_paths=[str(coverage_temp_dir_path)],
            strict=True,
            keep=True,
        )
    except NoDataError:
        return CombinedCoverageResult(
            source_file_coverage_records={},
            executed_line_count=0,
            total_line_count=0,
            executed_branch_count=0,
            total_branch_count=0,
            statement_coverage_pct=0.0,
            branch_coverage_pct=0.0,
            total_coverage_pct=0.0,
        )

    coverage_obj.save()

    coverage_obj.json_report(
        outfile=str(combined_json_file_path),
        pretty_print=False,
    )

    report = json.loads(
        combined_json_file_path.read_text(
            encoding="utf-8",
        )
    )

    totals = report["totals"]

    executed_line_count = int(
        totals["covered_lines"]
    )
    total_line_count = int(
        totals["num_statements"]
    )


    # Coverage.py omits these fields when no branches exist.
    executed_branch_count = int(totals.get("covered_branches", 0))
    total_branch_count = int(totals.get("num_branches", 0))
    statement_coverage_pct = (
        100 * executed_line_count / total_line_count
        if total_line_count > 0
        else 0.0
    )
    branch_coverage_pct = (
        100 * executed_branch_count / total_branch_count
        if total_branch_count > 0
        else 0.0
    )
    total_coverage_pct = float(totals["percent_covered"])

    tested_code_dir = tested_code_dir.resolve()

    records: dict[
        str,
        SourceFileCoverageRecord,
    ] = {}

    for reported_path, file_data in report["files"].items():
        source_file_path = Path(reported_path)

        if not source_file_path.is_absolute():
            source_file_path = (
                Path.cwd() / source_file_path
            )

        source_file_path = source_file_path.resolve()

        # Ignore coverage entries outside the configured tested-code directory.
        if not source_file_path.is_relative_to(tested_code_dir):
            continue

        # Internal safety check: is_relative_to() above should guarantee success.
        try:
            relative_source_file_path = source_file_path.relative_to(tested_code_dir).as_posix()
        except ValueError as exc:
            raise RuntimeError(
                "PYTEST_HARNESS INTERNAL ERROR:\n"
                "Source file is outside tested_code_dir:\n"
                f"    Source file: {source_file_path}\n"
                f"    Tested-code directory: {tested_code_dir}"
            ) from exc

        executed_lines: set[int] = {
            int(line_number)
            for line_number
            in file_data["executed_lines"]
        }

        missing_lines: set[int] = {
            int(line_number)
            for line_number
            in file_data["missing_lines"]
        }

        # Coverage.py omits these fields when no branches exist.
        executed_branch_pairs: set[
            tuple[int, int]
        ] = {
            (
                int(first_line),
                int(second_line),
            )
            for first_line, second_line
            in file_data.get(
                "executed_branches",
                [],
            )
        }

        missing_branch_pairs: set[
            tuple[int, int]
        ] = {
            (
                int(first_line),
                int(second_line),
            )
            for first_line, second_line
            in file_data.get(
                "missing_branches",
                [],
            )
        }

        total_branch_pairs = (
            executed_branch_pairs
            | missing_branch_pairs
        )

        branch_destinations: dict[
            int,
            set[int],
        ] = {}

        for first_line, second_line in total_branch_pairs:
            branch_destinations.setdefault(
                first_line,
                set(),
            ).add(second_line)

        branch_source: set[
            tuple[int, int]
        ] = {
            (
                first_line,
                len(destinations),
            )
            for first_line, destinations
            in branch_destinations.items()
        }

        source_file_path_str = str(
            source_file_path
        )

        records[
            source_file_path_str
        ] = SourceFileCoverageRecord(
            source_file_path=source_file_path_str,
            relative_source_file_path=relative_source_file_path,
            executed_lines=executed_lines,
            missing_lines=missing_lines,
            total_line_count=int(
                file_data["summary"][
                    "num_statements"
                ]
            ),
            branch_source=branch_source,
            total_branch_pairs=total_branch_pairs,
            executed_branch_pairs=(
                executed_branch_pairs
            ),
        )

    return CombinedCoverageResult(
        source_file_coverage_records=records,
        executed_line_count=executed_line_count,
        total_line_count=total_line_count,
        executed_branch_count=executed_branch_count,
        total_branch_count=total_branch_count,
        statement_coverage_pct=statement_coverage_pct,
        branch_coverage_pct=branch_coverage_pct,
        total_coverage_pct=total_coverage_pct,
    )
