"""
test_helpers
"""

from importlib import import_module
from types import ModuleType
from typing import Any

from pytest_harness import pytest_harness
from pytest_harness.constants_and_classes import RunResult

module: ModuleType = import_module("pytest_harness.pytest_harness")


def _run_harness(
    *,
    expected_exit_code: int = 0,
    **kwargs: Any,
) -> RunResult:
    run_result = pytest_harness(**kwargs)
    assert (
        run_result.pytest_harness_exit_code
        == expected_exit_code
    )

    return run_result
