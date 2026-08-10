"""
test_pytest_harness.py

Test top-level pytest_harness orchestration.

Last edited: 2026-08-07
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from test_helpers.helpers import _run_harness

from pytest_harness.constants_and_classes import (
    CombinedCoverageResult,
    TestFileRecord,
    TestFileStatus,
    TestFunctionRecord,
)

module: ModuleType = import_module(
    "pytest_harness.pytest_harness"
)


# === Fakes ===================================================================

class _FakeLog:
    def __init__(
        self,
        output_dir_path: Path,
    ) -> None:
        self.output_dir_path = output_dir_path
        self.configure_calls: list[dict[str, Any]] = []
        self.messages: list[str] = []
        self.warnings: list[str] = []
        self.close_call_count = 0

        self.session_config = SimpleNamespace(
            console_theme_dict={
                "title": "bold bright_cyan",
                "header_label": "bright_cyan",
                "header_value": "grey70",
                "text": "white",
                "muted": "grey58",
                "divider": "cyan",
                "pipe": "grey50",
                "sink_tag": "bright_cyan",
                "critical": "bold red",
                "error": "bold red",
                "warning": "bold yellow",
                "success": "bold bright_green",
                "info": "grey58",
                "debug": "bold magenta",
                "trace": "bold grey70",
            }
        )

    def configure(
        self,
        **kwargs: Any,
    ) -> None:
        self.configure_calls.append(kwargs)

    def __call__(
        self,
        message: object,
    ) -> None:
        self.messages.append(str(message))

    def warning(
        self,
        message: object,
    ) -> None:
        self.warnings.append(str(message))

    def close(self) -> None:
        self.close_call_count += 1


class _FakeTemporaryDirectory:
    def __init__(
        self,
        *,
        prefix: str,
        temp_dir: Path,
    ) -> None:
        self.name = str(
            temp_dir / f"{prefix}fake"
        )
        Path(self.name).mkdir(parents=True)
        self.cleaned = False

    def __enter__(self) -> str:
        return self.name

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.cleaned = True


# === Tests ===================================================================

# --- test_01_rejects_missing_required_input_directories() ---------------------
@pytest.mark.parametrize(
    ("missing_name", "message"),
    [
        pytest.param(
            "test",
            "Test directory does not exist",
            id="missing-test-directory",
        ),
        pytest.param(
            "source",
            "Source directory does not exist",
            id="missing-source-directory",
        ),
    ],
)
def test_01_rejects_missing_required_input_directories(
    tmp_path: Path,
    missing_name: str,
    message: str,
) -> None:
    test_file_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    tested_code_dir = tmp_path / "src"

    log_dir.mkdir()

    if missing_name != "test":
        test_file_dir.mkdir()

    if missing_name != "source":
        tested_code_dir.mkdir()

    with pytest.raises(
        RuntimeError,
        match=message,
    ):
        module.pytest_harness(
            test_file_dir=test_file_dir,
            log_dir=log_dir,
            tested_code_dir=tested_code_dir,
        )


# --- test_02_creates_missing_log_directory() ----------------------------------
def test_02_creates_missing_log_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_file_dir = tmp_path / "tests"
    tested_code_dir = tmp_path / "src"
    log_dir = tmp_path / "new" / "logs"
    output_dir = tmp_path / "fake_output"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()
    output_dir.mkdir()

    (test_file_dir / "test_one.py").write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    _install_successful_pipeline(
        monkeypatch=monkeypatch,
        fake_log=fake_log,
        output_dir=output_dir,
        selected_test_files=[Path("test_one.py")],
    )

    _run_harness(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
    )

    assert log_dir.is_dir()
    assert fake_log.close_call_count == 1


# --- test_03_orchestrates_selected_test_files() -------------------------------
def test_03_orchestrates_selected_test_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_file_dir,
        log_dir,
        tested_code_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    first_test_file = (
        test_file_dir / "test_one.py"
    )
    second_test_file = (
        test_file_dir
        / "nested"
        / "test_two.py"
    )

    second_test_file.parent.mkdir()

    first_test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )
    second_test_file.write_text(
        "def test_two():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)
    fake_temp_dir = _FakeTemporaryDirectory(
        prefix="coverage_",
        temp_dir=output_dir,
    )

    record_builder_calls: list[
        dict[str, Any]
    ] = []
    combine_calls: list[
        dict[str, Any]
    ] = []
    summary_calls: list[
        dict[str, Any]
    ] = []
    dashboard_calls: list[
        dict[str, Any]
    ] = []

    monkeypatch.setattr(
        module,
        "log",
        fake_log,
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: fake_temp_dir,
    )
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [
            Path("test_one.py"),
            Path("nested/test_two.py"),
        ],
    )

    def fake_record_builder(
        **kwargs: Any,
    ) -> TestFileRecord:
        record_builder_calls.append(kwargs)
        return _processed_record(**kwargs)

    monkeypatch.setattr(
        module,
        "_build_test_file_record",
        fake_record_builder,
    )

    combined_result = _empty_combined_result(
        total_coverage_pct=92.0,
    )

    def fake_combine(
        **kwargs: Any,
    ) -> CombinedCoverageResult:
        combine_calls.append(kwargs)
        return combined_result

    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        fake_combine,
    )

    summary_result = _successful_summary()

    def fake_summary(
        **kwargs: Any,
    ) -> object:
        summary_calls.append(kwargs)
        return summary_result

    monkeypatch.setattr(
        module,
        "_build_summary_data",
        fake_summary,
    )

    def fake_dashboard(
        **kwargs: Any,
    ) -> str:
        dashboard_calls.append(kwargs)
        return "SUMMARY TEXT"

    monkeypatch.setattr(
        module,
        "_build_dashboard",
        fake_dashboard,
    )

    _run_harness(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        include_list=["test_one", "nested"],
        exclude_list=["ignored"],
        test_file_logs=True,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=True,
    )

    # --- Logduo configuration ---
    assert len(fake_log.configure_calls) == 1

    configure_args = fake_log.configure_calls[0]

    assert configure_args["log_dir_path"] == log_dir
    assert configure_args["log_file_layout"] == "run"
    assert configure_args["console_verbosity"] == 3
    assert configure_args["log_verbosity"] == 3
    assert configure_args["keep"] is None
    assert configure_args["write_config_table"] is False
    assert configure_args["console_prefix"] == "off"
    assert configure_args["log_prefix"] == "off"
    assert configure_args["console_wrap_width"] == 150
    assert configure_args["log_wrap_width"] == 150

    # --- One record-builder call per selected file ---
    assert len(record_builder_calls) == 2

    first_call = record_builder_calls[0]
    second_call = record_builder_calls[1]

    assert (
        first_call["test_file_path"]
        == first_test_file
    )
    assert (
        first_call["test_file_label"]
        == "test_one.py"
    )
    assert (
        first_call["test_file_log_path"].name
        == "test_one.log"
    )
    assert (
        first_call["progress_file_path"].name
        == "progress_test_one.txt"
    )

    assert (
        second_call["test_file_path"]
        == second_test_file
    )
    assert (
        second_call["test_file_label"]
        == "nested/test_two.py"
    )
    assert (
        second_call["test_file_log_path"].name
        == "nested__test_two.log"
    )
    assert (
        second_call["progress_file_path"].name
        == "progress_nested__test_two.txt"
    )

    for call in record_builder_calls:
        assert (
            call["tested_code_dir"]
            == tested_code_dir
        )
        assert call["test_file_logs"] is True
        assert (
            call["debug_harness"]
            is False
        )
        assert (
            call["coverage_config_file_path"].exists()
            is True
        )

    # --- Coverage combination ---
    assert len(combine_calls) == 1

    assert (
        combine_calls[0]["coverage_temp_dir_path"]
        == Path(fake_temp_dir.name)
    )
    assert (
        combine_calls[0]["tested_code_dir"]
        == tested_code_dir
    )

    # --- Records reached summary builder unchanged ---
    assert len(summary_calls) == 1

    records = summary_calls[0][
        "test_file_records"
    ]

    assert len(records) == 2

    assert (
        records[0].test_file_path
        == first_test_file
    )
    assert (
        records[0].test_file_label
        == "test_one.py"
    )

    assert (
        records[1].test_file_path
        == second_test_file
    )
    assert (
        records[1].test_file_label
        == "nested/test_two.py"
    )

    assert (
        summary_calls[0][
            "combined_coverage_result"
        ]
        is combined_result
    )

    # --- Summary reached dashboard ---
    assert len(dashboard_calls) == 1
    assert dashboard_calls[0]["summary_data"] is summary_result
    assert dashboard_calls[0]["coverage_warning_threshold"] == 85.0
    assert dashboard_calls[0]["show_source_file_coverage"] is True
    assert dashboard_calls[0]["dashboard_width"] == 150

    # --- Cleanup/reporting ---
    assert fake_temp_dir.cleaned is True
    assert "SUMMARY TEXT" in fake_log.messages
    assert (
        "Pytest Harness exit code: 0 "
        "(no test run errors detected)"
        in fake_log.messages
    )
    assert fake_log.close_call_count == 1


# --- test_04_passes_log_and_reporting_options() -------------------------------
def test_04_passes_log_and_reporting_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_file_dir,
        log_dir,
        tested_code_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    (test_file_dir / "test_one.py").write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    dashboard_calls: list[
        dict[str, Any]
    ] = []

    _install_successful_pipeline(
        monkeypatch=monkeypatch,
        fake_log=fake_log,
        output_dir=output_dir,
        selected_test_files=[Path("test_one.py")],
        dashboard_calls=dashboard_calls,
    )

    _run_harness(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        coverage_warning_threshold=None,
        show_source_file_coverage=False,
        show_skipped_and_xfailed=True,
        log_keep=7,
        console_theme="light",
        dashboard_width=120,
    )

    configure_args = fake_log.configure_calls[0]

    assert configure_args["keep"] == 7
    assert configure_args["console_theme"] == "light"
    assert configure_args["console_wrap_width"] == 120
    assert configure_args["log_wrap_width"] == 120

    assert dashboard_calls[0]["coverage_warning_threshold"] is None
    assert dashboard_calls[0]["show_source_file_coverage"] is False
    assert dashboard_calls[0]["show_skipped_and_xfailed"] is True
    assert dashboard_calls[0]["dashboard_width"] == 120


# --- test_05_debug_mode_lists_selected_test_files() ---------------------------
def test_05_debug_mode_lists_selected_test_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (
        test_file_dir,
        log_dir,
        tested_code_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    (test_file_dir / "test_one.py").write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    _install_successful_pipeline(
        monkeypatch=monkeypatch,
        fake_log=fake_log,
        output_dir=output_dir,
        selected_test_files=[Path("test_one.py")],
    )

    _run_harness(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        debug_harness=True,
    )

    output = capsys.readouterr().out

    assert (
        "DEBUG: --- List of test files "
        "pytest_harness will run ---"
        in output
    )
    assert "1. test_one.py" in output


# --- test_06_returns_code_one_when_run_failed() -------------------------------
def test_06_returns_code_one_when_run_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_file_dir,
        log_dir,
        tested_code_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    (test_file_dir / "test_one.py").write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    _install_successful_pipeline(
        monkeypatch=monkeypatch,
        fake_log=fake_log,
        output_dir=output_dir,
        selected_test_files=[Path("test_one.py")],
        summary_result=_failed_summary(),
    )

    _run_harness(
        expected_exit_code=1,
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
    )

    assert fake_log.close_call_count == 1
    assert (
        "Pytest Harness exit code: 1 "
        "(test run errors detected)"
        in fake_log.messages
    )


def test_07_package_exports_pytest_harness() -> None:

    import importlib

    import pytest_harness

    # pytest_harness is loaded as a pytest plugin before coverage starts.
    # Reload so the package-level public API is also exercised under coverage.
    # Bonus: __init__.py would not be covered without this

    importlib.reload(pytest_harness)

    assert callable(pytest_harness.pytest_harness)



# === Internal helpers =========================================================

def _install_successful_pipeline(
    *,
    monkeypatch: pytest.MonkeyPatch,
    fake_log: _FakeLog,
    output_dir: Path,
    selected_test_files: list[Path],
    dashboard_calls: list[dict[str, Any]] | None = None,
    summary_result: object | None = None,
) -> None:
    """
    Install simple successful fakes for pytest_harness dependencies.
    """
    if dashboard_calls is None:
        dashboard_calls = []

    if summary_result is None:
        summary_result = _successful_summary()

    monkeypatch.setattr(
        module,
        "log",
        fake_log,
    )

    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: _FakeTemporaryDirectory(
            prefix="coverage_",
            temp_dir=output_dir,
        ),
    )

    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: selected_test_files,
    )

    monkeypatch.setattr(
        module,
        "_build_test_file_record",
        lambda **kwargs: _processed_record(
            **kwargs
        ),
    )

    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        lambda **kwargs: _empty_combined_result(),
    )

    monkeypatch.setattr(
        module,
        "_build_summary_data",
        lambda **kwargs: summary_result,
    )

    def fake_dashboard(
        **kwargs: Any,
    ) -> str:
        dashboard_calls.append(kwargs)
        return "SUMMARY TEXT"

    monkeypatch.setattr(
        module,
        "_build_dashboard",
        fake_dashboard,
    )


def _processed_record(

    **kwargs: Any,

) -> TestFileRecord:

    """

    Build a minimal successful record from the values pytest_harness

    actually passed to the record builder.

    """

    node_id = f"{kwargs['test_file_label']}::test_placeholder"

    test_function_record = TestFunctionRecord(
        node_id=node_id,
        outcome="passed",
    )

    return TestFileRecord(
        test_file_path=kwargs["test_file_path"],
        test_file_label=kwargs["test_file_label"],
        test_file_exit_code=0,
        duration_seconds=0.1,
        status=TestFileStatus.PROCESSED,
        timed_out_test_function_node_id=None,
        not_processed_reason=None,
        file_error_message=None,
        warning_messages=[],
        collected_test_function_node_ids=[node_id],
        started_test_function_node_ids=[node_id],
        test_function_records=[test_function_record],
    )

def _empty_combined_result(
    total_coverage_pct: float = 100.0,
) -> CombinedCoverageResult:
    return CombinedCoverageResult(
        source_file_coverage_records={},
        executed_line_count=0,
        total_line_count=0,
        executed_branch_count=0,
        total_branch_count=0,
        statement_coverage_pct=0.0,
        branch_coverage_pct=0.0,
        total_coverage_pct=total_coverage_pct,
    )


def _make_required_dirs(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    test_file_dir = (
        tmp_path / "tests"
    ).resolve()
    log_dir = (
        tmp_path / "logs"
    ).resolve()
    tested_code_dir = (
        tmp_path / "src"
    ).resolve()
    output_dir = (
        log_dir / "run"
    ).resolve()

    test_file_dir.mkdir()
    log_dir.mkdir()
    tested_code_dir.mkdir()
    output_dir.mkdir()

    return (
        test_file_dir,
        log_dir,
        tested_code_dir,
        output_dir,
    )


def _successful_summary() -> SimpleNamespace:
    return SimpleNamespace(
        random_order_seed=None,
        test_function_timeout_seconds=200.0,
        source_file_count=0,
        test_file_count=1,
        passed_test_file_count=1,
        failed_test_file_count=0,
        error_test_file_count=0,
        skipped_test_file_count=0,
        xfailed_test_file_count=0,
        xpassed_test_file_count=0,
        passed_test_function_count=1,
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
        total_coverage_pct=100.0,
        not_processed_test_file_count=0,
        no_tests_collected_test_file_count=0,
        warning_test_file_count=0,
        warning_count=0,
        problem_test_files=[],
        not_processed_test_files=[],
        no_tests_collected_test_files=[],
        warning_test_files=[],
        source_file_coverage_records=[],
    )


def _failed_summary() -> SimpleNamespace:
    return SimpleNamespace(
        random_order_seed=None,
        test_function_timeout_seconds=200.0,

        source_file_count=0,
        test_file_count=1,

        passed_test_file_count=0,
        failed_test_file_count=1,
        error_test_file_count=0,
        skipped_test_file_count=0,
        xfailed_test_file_count=0,
        xpassed_test_file_count=0,

        passed_test_function_count=0,
        failed_test_function_count=1,
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

        not_processed_test_file_count=0,
        no_tests_collected_test_file_count=0,
        warning_test_file_count=0,
        warning_count=0,

        problem_test_files=[],
        not_processed_test_files=[],
        no_tests_collected_test_files=[],
        warning_test_files=[],
        source_file_coverage_records=[],
    )
