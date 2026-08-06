"""
test_record_builder.py

Last edited: 2026-07-16
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import pytest_harness.record_builder as module
from pytest_harness.constants_and_classes import TestFileStatus

# === Fakes ===================================================================

class _FakeStdout:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def __iter__(self) -> Iterator[str]:
        return iter(self._lines)


class _FakeProcess:
    def __init__(
        self,
        lines: list[str],
        returncode: int,
    ) -> None:
        self.stdout = _FakeStdout(lines)
        self.returncode = returncode
        self.wait_called = False

    def wait(self) -> None:
        self.wait_called = True


class _FakeLog:
    def __init__(self) -> None:
        self.join_calls = 0
        self.new_logger_calls: list[
            tuple[tuple[Any, ...], dict[str, Any]]
        ] = []
        self.logged_lines: list[str] = []

    def join(self) -> None:
        self.join_calls += 1

    def new_logger(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        self.new_logger_calls.append((args, kwargs))

        def logger(message: str) -> None:
            self.logged_lines.append(message)

        return logger


# === Tests ===================================================================
# --- test_01_builds_record_from_json_report_and_constructs_expected_command()
def test_01_builds_record_from_json_report_and_constructs_expected_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_ok():\n"
        "    pass\n",
        encoding="utf-8",
    )

    coverage_data = tmp_path / ".coverage.test_example"
    coverage_config = tmp_path / ".coveragerc"
    log_path = tmp_path / "test_example.log"

    report = _report(
        summary={
            "passed": 1,
            "failed": 1,
            "skipped": 1,
            "xfailed": 1,
            "xpassed": 1,
        },
        tests=[
            {
                "nodeid": f"{test_file}::test_pass",
                "outcome": "passed",
            },
            {
                "nodeid": f"{test_file}::test_fail",
                "outcome": "failed",
            },
            {
                "nodeid": f"{test_file}::test_skip",
                "outcome": "skipped",
            },
            {
                "nodeid": f"{test_file}::test_xfail",
                "outcome": "xfailed",
            },
            {
                "nodeid": f"{test_file}::test_xpass",
                "outcome": "xpassed",
            },
        ],
    )

    fake_log, fake_process, popen_call = _install_fake_runtime(
        monkeypatch,
        report=report,
        returncode=1,
        output_lines=["\x1b[31mfailed output\x1b[0m\n"],   # noqa intentional
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=log_path,
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=coverage_data,
        extra_pytest_args=["-k", "selected"],
        coverage_config_file_path=coverage_config,
        individual_logs=True,
    )

    assert result.test_file_exit_code == 1
    assert result.duration_seconds == 1.25
    assert result.status is TestFileStatus.PROCESSED
    assert result.file_error_message is None

    assert result.passed_test_function_count == 1
    assert result.failed_test_function_count == 1
    assert result.error_test_function_count == 0
    assert result.skipped_test_function_count == 1
    assert result.xfailed_test_function_count == 1
    assert result.xpassed_test_function_count == 1

    assert result.passed_test_function_names == ["test_pass"]
    assert result.failed_test_function_names == ["test_fail"]
    assert result.error_test_function_names == []
    assert result.skipped_test_function_names == ["test_skip"]
    assert result.xfailed_test_function_names == ["test_xfail"]
    assert result.xpassed_test_function_names == ["test_xpass"]

    assert result.total_test_function_count == 5
    assert result.executed_any_tests is True

    cmd = popen_call["cmd"]

    assert cmd[:3] == [
        module.sys.executable,
        "-m",
        "pytest",
    ]
    assert "-o" in cmd
    assert "addopts=" in cmd
    assert f"--cov={tested_code_dir}" in cmd
    assert f"--cov-config={coverage_config}" in cmd
    assert "--cov-report=term-missing" in cmd
    assert str(test_file) in cmd
    assert cmd[-2:] == ["-k", "selected"]

    env = popen_call["kwargs"]["env"]
    assert env["COVERAGE_FILE"] == str(coverage_data)

    assert fake_process.wait_called is True
    assert fake_log.join_calls == 1
    assert fake_log.new_logger_calls

    # assert "failed output\n" in fake_log.logged_lines[0] TODO delete
    assert fake_log.logged_lines[0] == "failed output"
    assert "pytest exit code: 1" in fake_log.logged_lines
    assert "duration: 1.25 seconds" in fake_log.logged_lines


# --- test_02_marks_nonstandard_exit_as_not_processed_and_records_error_output()
def test_02_marks_nonstandard_exit_as_not_processed_and_records_error_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_error.py"
    test_file.write_text("", encoding="utf-8")

    report = _report(
        summary={"errors": 1},
        tests=[
            {
                "nodeid": f"{test_file}::test_import_error",
                "outcome": "error",
            },
        ],
    )

    _install_fake_runtime(
        monkeypatch,
        report=report,
        returncode=2,
        output_lines=["collection failed\n"],
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_error.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=(tmp_path / ".coverage.test_error"),
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.test_file_exit_code == 2
    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.file_error_message == "collection failed"

    assert result.error_test_function_count == 1
    assert result.error_test_function_names == [
        "test_import_error"
    ]


# --- test_03_disables_terminal_coverage_report_when_individual_logs_are_off()
def test_03_disables_terminal_coverage_report_when_individual_logs_are_off(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_ok.py"
    test_file.write_text(
        "def test_ok():\n"
        "    pass\n",
        encoding="utf-8",
    )

    report = _report(
        summary={"passed": 1},
        tests=[
            {
                "nodeid": f"{test_file}::test_ok",
                "outcome": "passed",
            },
        ],
    )

    fake_log, _, popen_call = _install_fake_runtime(
        monkeypatch,
        report=report,
        returncode=0,
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "unused.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=(tmp_path / ".coverage.test_ok"),
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.PROCESSED
    assert result.file_error_message is None
    assert result.passed_test_function_names == ["test_ok"]

    assert "--cov-report=" in popen_call["cmd"]
    assert "--cov-report=term-missing" not in popen_call["cmd"]
    assert fake_log.new_logger_calls == []


# --- test_04_marks_unexpected_outcome_as_invalid_json_report() ----------------
def test_04_marks_unexpected_outcome_as_invalid_json_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_unknown.py"
    test_file.write_text("", encoding="utf-8")

    report = _report(
        summary={},
        tests=[
            {
                "nodeid": f"{test_file}::test_unknown",
                "outcome": "mystery",
            },
        ],
    )

    _install_fake_runtime(
        monkeypatch,
        report=report,
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_unknown.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=tmp_path / ".coverage.test_unknown",
        coverage_config_file_path=tmp_path / ".coveragerc",
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.JSON_REPORT_ERROR_CODE
    assert result.not_processed_reason == "invalid pytest report"
    assert result.file_error_message is not None
    assert "Unexpected pytest outcome" in result.file_error_message
    assert "mystery" in result.file_error_message


# --- test_05_marks_file_when_no_tests_are_collected() -------------------------
def test_05_marks_file_when_no_tests_are_collected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_empty.py"
    test_file.write_text("", encoding="utf-8")

    _install_fake_runtime(
        monkeypatch,
        report=_report(
            summary={},
            tests=[],
        ),
        returncode=5,
        output_lines=["no tests ran\n"],
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_empty.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=(tmp_path / ".coverage.test_empty"),
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.test_file_exit_code == 5
    assert result.status is TestFileStatus.NO_TESTS_COLLECTED
    assert result.file_error_message is None
    assert result.total_test_function_count == 0
    assert result.executed_any_tests is False


# --- test_06_marks_selected_path_that_is_not_a_file_as_not_processed() --------
def test_06_marks_selected_path_that_is_not_a_file_as_not_processed(
    tmp_path: Path,
) -> None:
    selected_path = tmp_path / "test_group.py"
    selected_path.mkdir()

    result = module._build_test_file_record(
        test_file_path=selected_path,
        test_file_log_path=tmp_path / "test_group.log",
        tested_code_dir=tmp_path / "src",
        coverage_data_file_path=tmp_path / ".coverage.test_group",
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.PREFLIGHT_ERROR_CODE
    assert result.not_processed_reason == "invalid test-file path"
    assert result.file_error_message is not None
    assert "Expected a test file but found something else" in result.file_error_message


# --- test_07_marks_test_file_read_error_as_not_processed() --------------------
def test_07_marks_test_file_read_error_as_not_processed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_file = tmp_path / "test_one.py"
    test_file.write_text("", encoding="utf-8")

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

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_one.log",
        tested_code_dir=tmp_path / "src",
        coverage_data_file_path=tmp_path / ".coverage.test_one",
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.PREFLIGHT_ERROR_CODE
    assert result.not_processed_reason == "unreadable test file"
    assert result.file_error_message is not None
    assert "Unable to read test file" in result.file_error_message
    assert "permission denied" in result.file_error_message


# --- test_08_marks_missing_test_file_as_not_processed() -----------------------
def test_08_marks_missing_test_file_as_not_processed(
    tmp_path: Path,
) -> None:
    test_file = tmp_path / "test_missing.py"

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_missing.log",
        tested_code_dir=tmp_path / "src",
        coverage_data_file_path=tmp_path / ".coverage.test_missing",
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.PREFLIGHT_ERROR_CODE
    assert result.not_processed_reason == "missing test file"
    assert result.file_error_message is not None
    assert "Selected test file no longer exists" in result.file_error_message

# --- test_09_subprocess_launch_failure_returns_not_processed_record() ---
def test_09_subprocess_launch_failure_returns_not_processed_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()

    test_file = tmp_path / "test_example.py"
    test_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "logduo.log",
        _FakeLog(),
    )

    def fake_popen(*args: Any, **kwargs: Any) -> None:
        raise OSError("cannot start process")

    monkeypatch.setattr(
        module.subprocess,
        "Popen",
        fake_popen,
    )

    times = iter([100.0, 100.5])
    monkeypatch.setattr(
        module.time,
        "perf_counter",
        lambda: next(times),
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_example.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=tmp_path / ".coverage",
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.SUBPROCESS_LAUNCH_ERROR_CODE
    assert result.not_processed_reason == "subprocess launch failure"
    assert "cannot start process" in result.file_error_message
    assert result.duration_seconds == pytest.approx(0.5)


# --- test_10_empty_json_report_returns_not_processed_record() ---
def test_10_empty_json_report_returns_not_processed_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tested_code_dir = tmp_path / "src"
    tested_code_dir.mkdir()
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_example():\n"
        "    pass\n",
        encoding="utf-8",
    )

    fake_log = _FakeLog()
    fake_process = _FakeProcess(
        ["pytest output\n"],
        returncode=0,
    )

    def fake_popen(cmd: list[str], **kwargs: Any) -> _FakeProcess:
        return fake_process

    monkeypatch.setattr("logduo.log", fake_log)
    monkeypatch.setattr(module.subprocess, "Popen", fake_popen,)

    times = iter([100.0, 101.0])
    monkeypatch.setattr(
        module.time,
        "perf_counter",
        lambda: next(times),
    )

    result = module._build_test_file_record(
        test_file_path=test_file,
        test_file_log_path=tmp_path / "test_example.log",
        tested_code_dir=tested_code_dir,
        coverage_data_file_path=tmp_path / ".coverage",
        coverage_config_file_path=tmp_path / ".coveragerc",
        individual_logs=False,
    )

    assert result.status is TestFileStatus.NOT_PROCESSED
    assert result.test_file_exit_code == module.JSON_REPORT_ERROR_CODE
    assert result.not_processed_reason == "invalid pytest report"
    assert result.file_error_message is not None
    assert "did not create a JSON test report" in result.file_error_message


# --- test_11_extract_warning_messages_formats_location_and_category() ---
def test_11_extract_warning_messages_formats_location_and_category() -> None:
    report = {
        "warnings": [
            {
                "message": "example warning",
                "category": "UserWarning",
                "filename": "/project/test_example.py",
                "lineno": 12,
            }
        ]
    }

    assert module._extract_warning_messages(report) == [
        "/project/test_example.py:12: UserWarning: example warning"
    ]


# --- test_12_extract_warning_messages_rejects_non_list() ---
def test_12_extract_warning_messages_rejects_non_list() -> None:
    with pytest.raises(ValueError, match="valid warnings list"):
        module._extract_warning_messages({"warnings": "invalid"})


# --- test_13_extract_warning_messages_rejects_invalid_record()  ---
def test_13_extract_warning_messages_rejects_invalid_record() -> None:
    with pytest.raises(ValueError, match="invalid warning record"):
        module._extract_warning_messages({"warnings": ["invalid"]})


@pytest.mark.parametrize(
    ("exit_code", "message", "expected"),
    [
        (2, "", "pytest interrupted"),
        (3, "", "pytest internal error"),
        (4, "", "pytest usage error"),
        (6, "", "pytest warning limit exceeded"),
        (2, "ModuleNotFoundError: missing", "missing module"),
        (2, "ImportError: failed import", "import error"),
        (2, "SyntaxError: invalid syntax", "syntax error"),
        (2, "ERROR collecting test_file.py", "collection error"),
    ],
)
# --- test_14_resolve_not_processed_reason() ---
def test_14_resolve_not_processed_reason(
    exit_code: int,
    message: str,
    expected: str,
) -> None:
    assert module._resolve_not_processed_reason(
        test_file_exit_code=exit_code,
        file_error_message=message,
    )


# === Internal helpers =========================================================

def _report(
    *,
    summary: dict[str, int],
    tests: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "summary": summary,
        "tests": tests,
    }


def _install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    report: dict[str, Any],
    returncode: int = 0,
    output_lines: list[str] | None = None,
) -> tuple[_FakeLog, _FakeProcess, dict[str, Any]]:
    fake_log = _FakeLog()

    fake_process = _FakeProcess(
        output_lines or ["pytest output\n"],
        returncode,
    )

    popen_call: dict[str, Any] = {}

    def fake_popen(
        cmd: list[str],
        **kwargs: Any,
    ) -> _FakeProcess:
        popen_call["cmd"] = cmd
        popen_call["kwargs"] = kwargs

        report_arg = next(
            arg
            for arg in cmd
            if arg.startswith("--json-report-file=")
        )

        report_path = Path(
            report_arg.split("=", maxsplit=1)[1]
        )

        report_path.write_text(
            json.dumps(report),
            encoding="utf-8",
        )

        return fake_process

    # Imports occur lazily inside _build_test_file_record.
    monkeypatch.setattr(
        "logduo.log",
        fake_log,
    )
    monkeypatch.setattr(
        "logduo.utils.wrap.wrap_text.strip_ansi",
        lambda text: (
            text
            .replace("\x1b[31m", "")
            .replace("\x1b[0m", "")
        ),
    )
    monkeypatch.setattr(
        module.subprocess,
        "Popen",
        fake_popen,
    )

    times = iter([100.0, 101.25])


    monkeypatch.setattr(
        module.time,
        "perf_counter",
        lambda: next(times),
    )

    return fake_log, fake_process, popen_call

