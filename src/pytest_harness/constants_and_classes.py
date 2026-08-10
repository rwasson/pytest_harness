"""
constants_and_classes.py

Last edited: 2026-08-10
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

MAX_LOGDUO_STEM_LENGTH = 200
WINDOWS_SAFE_PATH_LENGTH = 259
HASH_LENGTH = 8

MIN_COVERAGE_WARNING_THRESHOLD = 0.0
MAX_COVERAGE_WARNING_THRESHOLD = 100.0

MIN_WRAP_WIDTH = 80
DEFAULT_COVERAGE_WARNING_THRESHOLD = 85.0
DEFAULT_DASHBOARD_WIDTH = 150


# --- Set up classes -----------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ValidatedHarnessArgs:
    test_file_dir: Path
    log_dir: Path
    tested_code_dir: Path
    include_list: list[str | Path] | None
    exclude_list: list[str | Path] | None
    runner_log: bool
    test_file_logs: bool
    coverage_warning_threshold: float | None
    show_source_file_coverage: bool
    log_keep: int | None
    console_dashboard: bool
    console_theme: str
    dashboard_width: int
    show_skipped_and_xfailed: bool
    debug_harness: bool
    random_order: bool
    random_order_seed: int | None
    test_function_timeout: float | None


@dataclass(slots=True, frozen=True)
class FilePaths:
    test_file_path: Path
    test_file_log_path: Path
    coverage_data_file_path: Path
    progress_file_path: Path
    test_file_log_name_was_shortened: bool


# --- Test function class ------------------------------------------------------
@dataclass(slots=True)
class TestFunctionRecord:
    __test__ = False
    node_id: str

    outcome: str | None = None
    # Final values:
    # passed, failed, error, skipped, xfailed, xpassed, timed_out, or not_run.

    test_order_id: int = 0
    # Stable deterministic ID assigned after all test nodes are known.
    # 0 means not yet assigned during construction.

    run_order: int = 0
    # Actual execution position across the complete harness run.
    # 0 means the test was collected but never run.

    duration_seconds: float | None = None

    @property
    def test_function_name(self) -> str:
        return self.node_id.rsplit("::", maxsplit=1)[-1]


# --- Test file classes and methods --------------------------------------------
class TestFileStatus(Enum):  # Todo why is this on its own and not part of TestFileRecord?
    __test__ = False
    PROCESSED = "processed"
    NOT_PROCESSED = "not_processed"
    NO_TESTS_COLLECTED = "no_tests_collected"


@dataclass(slots=True)
class TestFileRecord:
    __test__ = False
    test_file_path: Path
    test_file_label: str
    test_file_exit_code: int
    duration_seconds: float
    status: TestFileStatus
    timed_out_test_function_node_id: str | None
    not_processed_reason: str | None
    file_error_message: str | None
    warning_messages: list[str]

    collected_test_function_node_ids: list[str]
    # All test-function node IDs pytest successfully collected for this file.

    started_test_function_node_ids: list[str]
    # Test-function node IDs in the actual order execution began.

    test_function_records: list[TestFunctionRecord]
    # Function-level results for successfully identified test functions.


    # --- Internal outcome helpers --------------------------------------------
    def _names_for_outcome(
        self,
        outcome: str,
    ) -> list[str]:
        return [
            record.test_function_name
            for record in self.test_function_records
            if record.outcome == outcome
        ]

    def _count_for_outcome(
        self,
        outcome: str,
    ) -> int:
        return sum(
            record.outcome == outcome
            for record in self.test_function_records
        )

    # --- Warning data ---------------------------------------------------------
    @property
    def warning_count(self) -> int:
        return len(self.warning_messages)

    # --- Test-function counts -------------------------------------------------
    @property
    def passed_test_function_count(self) -> int:
        return self._count_for_outcome("passed")

    @property
    def failed_test_function_count(self) -> int:
        return self._count_for_outcome("failed")

    @property
    def error_test_function_count(self) -> int:
        return self._count_for_outcome("error")

    @property
    def skipped_test_function_count(self) -> int:
        return self._count_for_outcome("skipped")

    @property
    def xfailed_test_function_count(self) -> int:
        return self._count_for_outcome("xfailed")

    @property
    def xpassed_test_function_count(self) -> int:
        return self._count_for_outcome("xpassed")

    @property
    def timed_out_test_function_count(self) -> int:
        return self._count_for_outcome("timed_out")

    # --- Test-function names --------------------------------------------------
    @property
    def passed_test_function_names(self) -> list[str]:
        return self._names_for_outcome("passed")

    @property
    def failed_test_function_names(self) -> list[str]:
        return self._names_for_outcome("failed")

    @property
    def error_test_function_names(self) -> list[str]:
        return self._names_for_outcome("error")

    @property
    def skipped_test_function_names(self) -> list[str]:
        return self._names_for_outcome("skipped")

    @property
    def xfailed_test_function_names(self) -> list[str]:
        return self._names_for_outcome("xfailed")

    @property
    def xpassed_test_function_names(self) -> list[str]:
        return self._names_for_outcome("xpassed")

    @property
    def timed_out_test_function_names(self) -> list[str]:
        return self._names_for_outcome("timed_out")

    # --- Aggregate function information --------------------------------------
    @property
    def total_test_function_count(self) -> int:
        return len(self.test_function_records)

    @property
    def executed_any_tests(self) -> bool:
        return bool(self.test_function_records)

    @property
    def executed_test_count(self) -> int:
        return sum(
            record.outcome not in {None, "skipped", "not_run"}
            for record in self.test_function_records
        )

    # --- File information -----------------------------------------------------
    @property
    def test_file_name(self) -> str:
        return Path(self.test_file_label).name

    # --- Problem flags --------------------------------------------------------
    @property
    def has_failures(self) -> bool:
        return self.failed_test_function_count > 0

    @property
    def has_errors(self) -> bool:
        return self.error_test_function_count > 0

    @property
    def has_skips(self) -> bool:
        return self.skipped_test_function_count > 0

    @property
    def has_xfails(self) -> bool:
        return self.xfailed_test_function_count > 0

    @property
    def has_xpasses(self) -> bool:
        return self.xpassed_test_function_count > 0

    @property
    def has_timeouts(self) -> bool:
        return self.timed_out_test_function_count > 0

    @property
    def problem_count(self) -> int:
        return (
            self.failed_test_function_count
            + self.error_test_function_count
            + self.skipped_test_function_count
            + self.xfailed_test_function_count
            + self.xpassed_test_function_count
            + self.timed_out_test_function_count
        )

    @property
    def has_problems(self) -> bool:
        return self.problem_count > 0


# --- Summary classes ----------------------------------------------------------
# internal summary
@dataclass(slots=True)
class AggregateTestSummary:
    random_order_seed: int | None
    test_function_timeout_seconds: float | None
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

    problem_test_files: list[TestFileRecord]
    not_processed_test_files: list[TestFileRecord]
    no_tests_collected_test_files: list[TestFileRecord]
    warning_test_files: list[TestFileRecord]
    source_file_coverage_records: list[SourceFileCoverageRecord]

    @property
    def not_processed_test_file_count(self) -> int:
        return len(self.not_processed_test_files)

    @property
    def no_tests_collected_test_file_count(self) -> int:
        return len(self.no_tests_collected_test_files)

    @property
    def warning_test_file_count(self) -> int:
        return len(self.warning_test_files)

    @property
    def warning_count(self) -> int:
        return sum(
            record.warning_count
            for record in self.warning_test_files
        )


# public summary
@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    pytest_harness_exit_code: int
    output_dir_path: Path

    # --- Run configuration/result metadata ---
    random_order_seed: int | None
    test_function_timeout_seconds: float | None

    # --- Test-file results ---
    test_file_count: int
    passed_test_file_count: int
    failed_test_file_count: int
    error_test_file_count: int
    skipped_test_file_count: int
    xfailed_test_file_count: int
    xpassed_test_file_count: int
    not_processed_test_file_count: int
    no_tests_collected_test_file_count: int
    warning_test_file_count: int
    warning_count: int

    # --- Test-function results ---
    passed_test_function_count: int
    failed_test_function_count: int
    error_test_function_count: int
    skipped_test_function_count: int
    xfailed_test_function_count: int
    xpassed_test_function_count: int

    # Flat calculation-ready test-function data.
    # Each record contains:
    #     node_id
    #     test_order_id
    #     run_order
    #     outcome
    # Designed for easy flaky test analysis
    test_function_records: tuple[TestFunctionRecord, ...]

    # Detailed file-level records.
    test_file_records: tuple[TestFileRecord, ...]

    # --- Coverage ---
    source_file_count: int
    executed_line_count: int
    total_line_count: int
    executed_branch_count: int
    total_branch_count: int
    statement_coverage_pct: float
    branch_coverage_pct: float
    total_coverage_pct: float

    source_file_coverage_records: tuple[SourceFileCoverageRecord, ...]


# --- Coverage Classes ---------------------------------------------------------
@dataclass(slots=True)
class SourceFileCoverageRecord:
    source_file_path: str
    relative_source_file_path: str

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


