# __init__.py

from __future__ import annotations

from typing import Any, TYPE_CHECKING

__all__ = ["pytest_harness"]

if TYPE_CHECKING:
    from .pytest_harness import pytest_harness

# Keep this import lazy.
# pytest loads pytest_harness.progress_plugin before pytest-cov begins measuring.
# An eager import here would load the rest of pytest_harness too early and cause
# substantial under-reporting of source coverage.
def __getattr__(
    name: str,
) -> Any:
    if name == "pytest_harness":
        from .pytest_harness import pytest_harness

        globals()[name] = pytest_harness
        return pytest_harness

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
