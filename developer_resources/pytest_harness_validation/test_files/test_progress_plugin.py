"""
test_progress_plugin.py

Tests for the internal pytest progress plugin.

Last edited: 2026-08-08
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import pytest_harness.progress_plugin as module

# === Tests ===================================================================

# --- test_01_write_progress_does_nothing_when_no_progress_file_configured() ---
def test_01_write_progress_does_nothing_when_no_progress_file_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "_progress_file_path",
        None,
    )

    module._write_progress(
        "START",
        "test_example.py::test_one",
    )


# --- test_02_write_progress_appends_event_and_node_id() -----------------------
def test_02_write_progress_appends_event_and_node_id(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    module._write_progress(
        "START",
        "test_example.py::test_one",
    )
    module._write_progress(
        "FINISH",
        "test_example.py::test_one",
    )

    assert progress_file.read_text(
        encoding="utf-8",
    ) == (
        "START\ttest_example.py::test_one\n"
        "FINISH\ttest_example.py::test_one\n"
    )


# --- test_03_collection_finish_records_all_collected_node_ids() ---------------
def test_03_collection_finish_records_all_collected_node_ids(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    session = SimpleNamespace(
        items=[
            SimpleNamespace(
                nodeid="test_example.py::test_one"
            ),
            SimpleNamespace(
                nodeid="test_example.py::test_two"
            ),
        ]
    )

    module.pytest_collection_finish(session)

    assert progress_file.read_text(
        encoding="utf-8",
    ).splitlines() == [
        "COLLECT\ttest_example.py::test_one",
        "COLLECT\ttest_example.py::test_two",
    ]


def test_04_logstart_and_logfinish_record_execution_progress(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    times = iter([100.0, 101.25])
    monkeypatch.setattr(
        module.time,
        "perf_counter",
        lambda: next(times),
    )

    node_id = "test_example.py::test_one"

    module.pytest_runtest_logstart(node_id)
    module.pytest_runtest_logfinish(node_id)

    assert progress_file.read_text(
        encoding="utf-8",
    ).splitlines() == [
        f"START\t{node_id}",
        f"DURATION\t{node_id}\t1.25",
        f"FINISH\t{node_id}",
    ]


# --- test_05_logreport_ignores_non_call_phases() ------------------------------
@pytest.mark.parametrize(
    "when",
    [
        "setup",
        "teardown",
    ],
)
def test_05_logreport_ignores_non_call_phases(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    when: str,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    report = SimpleNamespace(
        when=when,
        nodeid="test_example.py::test_one",
        outcome="passed",
    )

    module.pytest_runtest_logreport(report)

    assert progress_file.exists() is False


# --- test_06_logreport_records_normal_pytest_outcome() ------------------------
@pytest.mark.parametrize(
    "outcome",
    [
        "passed",
        "failed",
        "skipped",
    ],
)
def test_06_logreport_records_normal_pytest_outcome(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    report = SimpleNamespace(
        when="call",
        nodeid="test_example.py::test_one",
        outcome=outcome,
    )

    module.pytest_runtest_logreport(report)

    assert progress_file.read_text(
        encoding="utf-8",
    ) == (
        "OUTCOME\t"
        "test_example.py::test_one\t"
        f"{outcome}\n"
    )


# --- test_07_logreport_converts_expected_failure_to_xfailed() -----------------
def test_07_logreport_converts_expected_failure_to_xfailed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    report = SimpleNamespace(
        when="call",
        nodeid="test_example.py::test_expected_failure",
        outcome="skipped",
        skipped=True,
        wasxfail="known issue",
    )

    module.pytest_runtest_logreport(report)

    assert progress_file.read_text(
        encoding="utf-8",
    ) == (
        "OUTCOME\t"
        "test_example.py::test_expected_failure\t"
        "xfailed\n"
    )


# --- test_08_logreport_converts_unexpected_pass_to_xpassed() ------------------
def test_08_logreport_converts_unexpected_pass_to_xpassed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    report = SimpleNamespace(
        when="call",
        nodeid="test_example.py::test_unexpected_pass",
        outcome="passed",
        skipped=False,
        wasxfail="known issue",
    )

    module.pytest_runtest_logreport(report)

    assert progress_file.read_text(
        encoding="utf-8",
    ) == (
        "OUTCOME\t"
        "test_example.py::test_unexpected_pass\t"
        "xpassed\n"
    )


def test_09_plugin_records_complete_normal_test_lifecycle(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_file = tmp_path / "progress.txt"

    monkeypatch.setattr(
        module,
        "_progress_file_path",
        str(progress_file),
    )

    times = iter([100.0, 101.25])
    monkeypatch.setattr(
        module.time,
        "perf_counter",
        lambda: next(times),
    )

    node_id = "test_example.py::test_one"

    session = SimpleNamespace(
        items=[
            SimpleNamespace(
                nodeid=node_id,
            )
        ]
    )

    report = SimpleNamespace(
        when="call",
        nodeid=node_id,
        outcome="passed",
    )

    module.pytest_collection_finish(session)
    module.pytest_runtest_logstart(node_id)
    module.pytest_runtest_logreport(report)
    module.pytest_runtest_logfinish(node_id)

    assert progress_file.read_text(
        encoding="utf-8",
    ).splitlines() == [
        f"COLLECT\t{node_id}",
        f"START\t{node_id}",
        f"OUTCOME\t{node_id}\tpassed",
        f"DURATION\t{node_id}\t1.25",
        f"FINISH\t{node_id}",
    ]
