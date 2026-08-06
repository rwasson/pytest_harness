"""
test_intentional_warning.py
"""

import warnings


def test_intentional_warning() -> None:
    warnings.warn(
        "This warning is intentional for pytest_harness testing.",
        UserWarning,
        stacklevel=2,
    )

    assert True