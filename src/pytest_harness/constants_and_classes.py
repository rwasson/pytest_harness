"""
constants_and_classes.py

Last edited: 2026-07-16
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

MIN_CONSOLE_WRAP_WIDTH = 80
MIN_COVERAGE_WARNING_THRESHOLD = 0.0
MAX_COVERAGE_WARNING_THRESHOLD = 100.0
DEFAULT_COVERAGE_WARNING_THRESHOLD = 85.0
DEFAULT_WIDTH = 150

@dataclass(frozen=True, slots=True)
class ValidatedHarnessArgs:
    test_dir: Path
    log_dir: Path
    source_dir: Path
    include_list: list[str | Path] | None
    exclude_list: list[str | Path] | None
    individual_logs: bool
    coverage_warning_threshold: float | None
    show_source_file_coverage: bool
    log_keep: int | None
    console_wrap_width: int
    show_skipped_and_xfailed: bool
    debug_pytest_harness: bool


@dataclass(slots=True)
class SourceFileCoverageRecord:
    source_file_path: str

    executed_lines: set[int]
    missing_lines: set[int]
    total_line_count: int

    branch_source: set[tuple[int, int]]
    # Derived from branch pairs in the combined Coverage.py JSON report.

    total_branch_pairs: set[tuple[int, int]]
    # Union of executed and missing branch pairs in the combined JSON report.

    executed_branch_pairs: set[tuple[int, int]]
    # Executed branch pairs in the combined Coverage.py JSON report.

    @property
    def executed_line_count(self) -> int:
        return len(self.executed_lines)

    @property
    def missing_line_count(self) -> int:
        return len(self.missing_lines)

    @property
    def total_branch_count(self) -> int:
        return len(self.total_branch_pairs)

    @property
    def executed_branch_count(self) -> int:
        return len(self.executed_branch_pairs)

    @property
    def missing_branch_count(self) -> int:
        return self.total_branch_count - self.executed_branch_count

    @property
    def statement_coverage_pct(self) -> float:
        if self.total_line_count == 0:
            return 0.0
        return self.executed_line_count / self.total_line_count * 100

    @property
    def branch_coverage_pct(self) -> float:
        if self.total_branch_count == 0:
            return 0.0
        return self.executed_branch_count / self.total_branch_count * 100

    @property
    def overall_coverage_pct(self) -> float:
        denominator = self.total_line_count + self.total_branch_count
        if denominator == 0:
            return 0.0
        numerator = self.executed_line_count + self.executed_branch_count
        return numerator / denominator * 100


class TestFileStatus(Enum):
    PROCESSED = "processed"
    NOT_PROCESSED = "not_processed"
    NO_TESTS_COLLECTED = "no_tests_collected"

@dataclass(slots=True)
class TestFileRecord:
    test_file_path: str
    exit_code: int
    duration_seconds: float
    status: TestFileStatus
    file_error_message: str | None

    passed_test_function_count: int
    failed_test_function_count: int
    error_test_function_count: int
    skipped_test_function_count: int
    xfailed_test_function_count: int
    xpassed_test_function_count: int
    passed_test_function_names: list[str]
    failed_test_function_names: list[str]
    error_test_function_names: list[str]
    skipped_test_function_names: list[str]
    xfailed_test_function_names: list[str]
    xpassed_test_function_names: list[str]

    @property
    def total_test_function_count(self) -> int:
        return (
                self.passed_test_function_count
                + self.failed_test_function_count
                + self.error_test_function_count
                + self.skipped_test_function_count
                + self.xfailed_test_function_count
                + self.xpassed_test_function_count
        )

    @property
    def executed_any_tests(self) -> bool:
        return self.total_test_function_count > 0

    @property
    def executed_test_count(self) -> int:
        return (
                self.passed_test_function_count
                + self.failed_test_function_count
                + self.error_test_function_count
                + self.xpassed_test_function_count
                + self.xfailed_test_function_count
        )



@dataclass(slots=True)
class AggregateTestSummary:
    source_file_count: int
    test_file_count: int

    passed_test_file_count: int
    failed_test_file_count: int
    error_test_file_count: int
    skipped_test_file_count: int
    xfailed_test_file_count: int
    xpassed_test_file_count: int

    passed_test_function_count: int
    failed_test_function_count: int
    error_test_function_count: int
    skipped_test_function_count: int
    xfailed_test_function_count: int
    xpassed_test_function_count: int

    executed_line_count: int
    total_line_count: int

    executed_branch_count: int
    total_branch_count: int

    statement_coverage_pct: float
    branch_coverage_pct: float
    total_coverage_pct: float

    problem_test_files: list[ProblemTestFileRecord]
    not_processed_test_files: list[str]
    no_tests_collected_test_files: list[str]
    source_file_coverage_records: list[SourceFileCoverageRecord]

    @property
    def not_processed_test_file_count(self) -> int:
        return len(self.not_processed_test_files)

    @property
    def no_tests_collected_test_file_count(self) -> int:
        return len(self.no_tests_collected_test_files)


@dataclass(slots=True)
class ProblemTestFileRecord:
    test_file_name: str
    failed_test_function_names: list[str]
    error_test_function_names: list[str]
    skipped_test_function_names: list[str]
    xfailed_test_function_names: list[str]
    xpassed_test_function_names: list[str]

    @property
    def failed_test_count(self) -> int:
        return len(self.failed_test_function_names)

    @property
    def error_test_count(self) -> int:
        return len(self.error_test_function_names)

    @property
    def skipped_test_count(self) -> int:
        return len(self.skipped_test_function_names)

    @property
    def xfailed_test_count(self) -> int:
        return len(self.xfailed_test_function_names)

    @property
    def xpassed_test_count(self) -> int:
        return len(self.xpassed_test_function_names)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_test_function_names)

    @property
    def has_errors(self) -> bool:
        return bool(self.error_test_function_names)

    @property
    def has_skips(self) -> bool:
        return bool(self.skipped_test_function_names)

    @property
    def has_xfails(self) -> bool:
        return bool(self.xfailed_test_function_names)

    @property
    def has_xpasses(self) -> bool:
        return bool(self.xpassed_test_function_names)

    @property
    def problem_count(self) -> int:
        return (
                self.failed_test_count
                + self.error_test_count
                + self.skipped_test_count
                + self.xfailed_test_count
                + self.xpassed_test_count
        )

    @property
    def has_problems(self) -> bool:
        return self.problem_count > 0


@dataclass(slots=True)
class CombinedCoverageResult:
    source_file_coverage_records: dict[str, SourceFileCoverageRecord]
    executed_line_count: int
    total_line_count: int
    executed_branch_count: int
    total_branch_count: int

    statement_coverage_pct: float
    branch_coverage_pct: float
    total_coverage_pct: float
