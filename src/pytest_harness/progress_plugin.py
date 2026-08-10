"""
progress_plugin.py

Internal pytest plugin for recording test-function progress.

Last edited: 2026-08-10
"""

import os
import time
from pathlib import Path

import pytest

_test_start_times: dict[str, float] = {}
_progress_file_path = os.environ.get("PYTEST_HARNESS_PROGRESS_FILE")


def _write_progress(
    event: str,
    nodeid: str,
) -> None:
    if _progress_file_path is None:
        return

    with Path(_progress_file_path).open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(f"{event}\t{nodeid}\n")
        file.flush()


def pytest_collection_finish(session: pytest.Session) -> None:
    for item in session.items:
        _write_progress("COLLECT", item.nodeid)


def pytest_runtest_logstart(
    nodeid: str,
) -> None:
    _test_start_times[nodeid] = time.perf_counter()
    _write_progress("START", nodeid)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when != "call":
        return
    if hasattr(report, "wasxfail"):
        outcome = (
            "xfailed"
            if report.skipped
            else "xpassed"
        )
    else:
        outcome = report.outcome
    _write_progress(
        "OUTCOME",
        f"{report.nodeid}\t{outcome}",
    )


def pytest_runtest_logfinish(
    nodeid: str,
) -> None:
    start_time = _test_start_times.pop(
        nodeid,
        None,
    )

    if start_time is not None:
        duration_seconds = time.perf_counter() - start_time

        _write_progress(
            "DURATION",
            f"{nodeid}\t{duration_seconds}",
        )

    _write_progress("FINISH", nodeid)
