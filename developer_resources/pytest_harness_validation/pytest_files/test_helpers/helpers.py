"""
test_helpers
"""

from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

module: ModuleType = import_module("pytest_harness.pytest_harness")


def _run_harness(
    *,
    expected_exit_code: int = 0,
    **kwargs: Any,
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        module.pytest_harness(**kwargs)
    assert exc_info.value.code == expected_exit_code
