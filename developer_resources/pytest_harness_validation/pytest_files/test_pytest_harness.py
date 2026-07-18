"""
test_pytest_harness.py

Last edited: 2026-7-16
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

module: ModuleType = import_module("pytest_harness.pytest_harness")


from test_helpers.helpers import _run_harness

from pytest_harness.constants_and_classes import (
    CombinedCoverageResult,
    TestFileRecord,
    TestFileStatus,
)

# === Fakes ===================================================================

class _FakeLog:
    def __init__(self, output_dir_path: Path) -> None:
        self.output_dir_path = output_dir_path
        self.configure_calls: list[dict[str, Any]] = []
        self.messages: list[str] = []
        self.warnings: list[str] = []
        self.close_call_count = 0

    def configure(self, **kwargs: Any) -> None:
        self.configure_calls.append(kwargs)

    def __call__(self, message: str) -> None:
        self.messages.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def close(self) -> None:
        self.close_call_count += 1


class _FakeTemporaryDirectory:
    def __init__(
        self,
        *,
        prefix: str,
        temp_dir: Path,
    ) -> None:
        self.name = str(Path(temp_dir) / f"{prefix}fake")
        Path(self.name).mkdir(parents=True)
        self.cleaned = False

    def cleanup(self) -> None:
        self.cleaned = True



# === Tests ===================================================================

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
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"

    log_dir.mkdir()

    if missing_name != "test":
        test_dir.mkdir()

    if missing_name != "source":
        source_dir.mkdir()

    with pytest.raises(RuntimeError, match=message):
        module.pytest_harness(
            test_dir=test_dir,
            log_dir=log_dir,
            source_dir=source_dir,
        )


def test_02_creates_missing_log_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "new" / "logs"
    source_dir = tmp_path / "src"

    test_dir.mkdir()
    source_dir.mkdir()

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    # log.output_dir_path must exist after log.configure() would normally run.
    output_dir = tmp_path / "fake_output"
    output_dir.mkdir()
    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(kwargs["test_file_path"]),
    )
    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        lambda **kwargs: _empty_combined_result(),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_data",
        lambda **kwargs: _successful_summary(),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_table",
        lambda **kwargs: "summary",
    )

    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
    )

    assert log_dir.is_dir()
    assert fake_log.close_call_count == 1

def test_03_orchestrates_test_run_and_builds_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # === Arrange: project directories ========================================

    test_dir = (tmp_path / "tests").resolve()
    log_dir = (tmp_path / "logs").resolve()
    source_dir = (tmp_path / "src").resolve()
    output_dir = log_dir / "pytest_harness" / "run"

    for path in (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    first_test_file = test_dir / "test_one.py"
    second_test_file = test_dir / "nested" / "test_two.py"

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

    # === Arrange: fakes and captured calls ==================================

    fake_log = _FakeLog(output_dir)

    fake_temp_dir = _FakeTemporaryDirectory(
        prefix="coverage_",
        temp_dir=output_dir,
    )

    monkeypatch.setattr(module, "log", fake_log)

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

    record_builder_calls: list[dict[str, Any]] = []

    def fake_build_test_file_record(
        **kwargs: Any,
    ) -> TestFileRecord:
        record_builder_calls.append(kwargs)
        return _record(kwargs["test_file_path"])

    monkeypatch.setattr(
        module,
        "_build_test_file_record",
        fake_build_test_file_record,
    )

    combined_result = _empty_combined_result(
        total_coverage_pct=92.0,
    )

    captured_combine_args: dict[str, Any] = {}

    def fake_combine_coverage(
        **kwargs: Any,
    ) -> CombinedCoverageResult:
        captured_combine_args.update(kwargs)
        return combined_result

    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        fake_combine_coverage,
    )

    summary_result = _successful_summary()
    captured_summary_args: dict[str, Any] = {}

    def fake_build_summary_data(
        **kwargs: Any,
    ) -> object:
        captured_summary_args.update(kwargs)
        return summary_result

    monkeypatch.setattr(
        module,
        "_build_summary_data",
        fake_build_summary_data,
    )

    captured_table_args: dict[str, Any] = {}

    def fake_build_summary_table(
        **kwargs: Any,
    ) -> str:
        captured_table_args.update(kwargs)
        return "SUMMARY TEXT"

    monkeypatch.setattr(
        module,
        "_build_summary_table",
        fake_build_summary_table,
    )

    # === Act ================================================================
    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        include_list=["test_one", "nested"],
        exclude_list=["ignored"],
        individual_logs=True,
        coverage_warning_threshold=85.0,
        show_source_file_coverage=True,
    )

    # === Assert: Logduo configuration =======================================

    assert len(fake_log.configure_calls) == 1

    configure_args = fake_log.configure_calls[0]

    assert configure_args["log_dir_path"] == log_dir
    assert configure_args["log_file_layout"] == "run"
    assert configure_args["log_verbosity"] == 3
    assert configure_args["keep"] is None
    assert configure_args["write_config_table"] is False
    assert configure_args["console_prefix"] == "off"
    assert configure_args["console_wrap_width"] == 150
    assert configure_args["log_prefix"] == "off"

    # === Assert: each selected test file was run =============================

    assert len(record_builder_calls) == 2

    first_call = record_builder_calls[0]
    second_call = record_builder_calls[1]

    assert first_call["test_file_path"] == first_test_file
    assert first_call["test_file_log_path"].name == "test_one.log"

    assert second_call["test_file_path"] == second_test_file
    assert (
        second_call["test_file_log_path"].name
        == "nested__test_two.log"
    )

    for call in record_builder_calls:
        assert call["source_dir"] == source_dir
        assert call["individual_logs"] is True
        assert call["coverage_config_file_path"].exists()

    # === Assert: coverage was combined ======================================

    assert captured_combine_args["coverage_dir_path"] == Path(
        fake_temp_dir.name
    )
    assert captured_combine_args["source_dir"] == source_dir
    assert fake_temp_dir.cleaned is True

    # === Assert: aggregate summary was built ================================

    test_file_records = captured_summary_args[
        "pytest_test_file_records"
    ]

    assert len(test_file_records) == 2
    assert test_file_records[0].test_file_path == str(
        first_test_file
    )
    assert test_file_records[1].test_file_path == str(
        second_test_file
    )

    assert (
        captured_summary_args["combined_coverage_result"]
        is combined_result
    )

    # === Assert: reporting options reached the table builder =================

    assert captured_table_args["summary_data"] is summary_result
    assert (
        captured_table_args["coverage_warning_threshold"]
        == 85.0
    )
    assert (
        captured_table_args["show_source_file_coverage"]
        is True
    )

    # === Assert: final summary was logged ===================================

    assert fake_log.messages == ["SUMMARY TEXT"]
    assert fake_log.warnings == []
    assert fake_log.close_call_count == 1

def test_04_rejects_selected_path_that_disappears_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("missing.py")],
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: _FakeTemporaryDirectory(
            prefix="coverage_",
            temp_dir=output_dir,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Unrecognized test file",
    ):
        module.pytest_harness(
            test_dir=test_dir,
            log_dir=log_dir,
            source_dir=source_dir,
        )


def test_05_passes_coverage_warning_threshold_to_summary_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(
            kwargs["test_file_path"]
        ),
    )
    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        lambda **kwargs: _empty_combined_result(
            total_coverage_pct=84.0,
        ),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_data",
        lambda **kwargs: _successful_summary(),
    )

    table_calls: list[dict[str, Any]] = []

    def fake_build_summary_table(
        **kwargs: Any,
    ) -> str:
        table_calls.append(kwargs)
        return (
            "Coverage\n"
            "    Total: 84%\n\n"
            "WARNING: Total coverage (84%) "
            "is below warning threshold 85%."
        )

    monkeypatch.setattr(
        module,
        "_build_summary_table",
        fake_build_summary_table,
    )

    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        coverage_warning_threshold=85.0,
    )

    assert table_calls[0]["coverage_warning_threshold"] == 85.0

    assert len(fake_log.messages) == 1
    assert "84%" in fake_log.messages[0]
    assert "85%" in fake_log.messages[0]

    # Warning is embedded in the summary rather than logged afterward.
    assert fake_log.warnings == []


def test_06_allows_coverage_warning_to_be_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(
            kwargs["test_file_path"]
        ),
    )
    monkeypatch.setattr(
        module,
        "_combine_coverage_data_files",
        lambda **kwargs: _empty_combined_result(
            total_coverage_pct=10.0,
        ),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_data",
        lambda **kwargs: _successful_summary(),
    )

    table_calls: list[dict[str, Any]] = []

    def fake_build_summary_table(
        **kwargs: Any,
    ) -> str:
        table_calls.append(kwargs)
        return "summary"

    monkeypatch.setattr(
        module,
        "_build_summary_table",
        fake_build_summary_table,
    )

    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        coverage_warning_threshold=None,
    )

    assert (
        table_calls[0]["coverage_warning_threshold"]
        is None
    )


def test_07_passes_log_keep_to_logduo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(
            kwargs["test_file_path"]
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
        lambda **kwargs: _successful_summary(),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_table",
        lambda **kwargs: "summary",
    )

    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        log_keep=7,
    )

    assert len(fake_log.configure_calls) == 1
    assert fake_log.configure_calls[0]["keep"] == 7


def test_08_debug_mode_lists_selected_test_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(module, "log", fake_log)
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(
            kwargs["test_file_path"]
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
        lambda **kwargs: _successful_summary(),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_table",
        lambda **kwargs: "summary",
    )

    _run_harness(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        debug_pytest_harness=True,
    )

    output = capsys.readouterr().out

    assert "DEBUG: Exact test files" in output
    assert "1. test_one.py" in output
    assert "DEBUG: Exact test-file count: 1" in output


def test_09_rejects_selected_path_that_is_not_a_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    selected_dir = test_dir / "test_group.py"
    selected_dir.mkdir()

    monkeypatch.setattr(
        module,
        "log",
        _FakeLog(output_dir),
    )
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_group.py")],
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: _FakeTemporaryDirectory(
            prefix="coverage_",
            temp_dir=output_dir,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Expected file but found something else",
    ):
        module.pytest_harness(
            test_dir=test_dir,
            log_dir=log_dir,
            source_dir=source_dir,
        )


def test_10_wraps_test_file_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "log",
        _FakeLog(output_dir),
    )
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: _FakeTemporaryDirectory(
            prefix="coverage_",
            temp_dir=output_dir,
        ),
    )

    original_read_text = Path.read_text

    def fake_read_text(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if path == test_file:
            raise OSError("permission denied")

        return original_read_text(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "read_text",
        fake_read_text,
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to read test file",
    ):
        module.pytest_harness(
            test_dir=test_dir,
            log_dir=log_dir,
            source_dir=source_dir,
        )

def test_11_exits_with_code_one_when_run_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        test_dir,
        log_dir,
        source_dir,
        output_dir,
    ) = _make_required_dirs(tmp_path)

    test_file = test_dir / "test_one.py"
    test_file.write_text(
        "def test_one():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog(output_dir)

    monkeypatch.setattr(
        module,
        "log",
        fake_log,
    )
    monkeypatch.setattr(
        module,
        "_resolve_test_file_paths",
        lambda **kwargs: [Path("test_one.py")],
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
        "_build_test_file_record",
        lambda **kwargs: _record(
            kwargs["test_file_path"]
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
        lambda **kwargs: _failed_summary(),
    )
    monkeypatch.setattr(
        module,
        "_build_summary_table",
        lambda **kwargs: "summary",
    )

    _run_harness(
        expected_exit_code=1,
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
    )

    assert fake_log.close_call_count == 1


# === Helpers =================================================================

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


def _record(path: Path) -> TestFileRecord:
    return TestFileRecord(
        test_file_path=str(path),
        exit_code=0,
        duration_seconds=0.1,
        status=TestFileStatus.PROCESSED,
        file_error_message=None,
        passed_test_function_count=1,
        failed_test_function_count=0,
        error_test_function_count=0,
        skipped_test_function_count=0,
        xfailed_test_function_count=0,
        xpassed_test_function_count=0,
        passed_test_function_names=["test_ok"],
        failed_test_function_names=[],
        error_test_function_names=[],
        skipped_test_function_names=[],
        xfailed_test_function_names=[],
        xpassed_test_function_names=[],
    )


def _make_required_dirs(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"
    output_dir = log_dir / "run"

    test_dir.mkdir()
    log_dir.mkdir()
    source_dir.mkdir()
    output_dir.mkdir()

    return test_dir, log_dir, source_dir, output_dir


def _successful_summary() -> SimpleNamespace:
    return SimpleNamespace(
        failed_test_function_count=0,
        error_test_function_count=0,
        xpassed_test_function_count=0,
        not_processed_test_file_count=0,
        no_tests_collected_test_file_count=0,

    )

def _failed_summary() -> SimpleNamespace:
    return SimpleNamespace(
        failed_test_function_count=1,
        error_test_function_count=0,
        xpassed_test_function_count=0,
        not_processed_test_file_count=0,
        no_tests_collected_test_file_count=0,
    )
