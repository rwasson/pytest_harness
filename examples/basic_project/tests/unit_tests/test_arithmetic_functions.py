"""
test_calculator.py

Tests for successful calculator operations.

Printed diagnostic details are included in this test file's individual log.
This can be useful for recording inputs, intermediate values, and calculated
results without adding them to the main pytest_harness summary.

To remove unresolved-reference warnings in the IDE editor, right-click the
src directory and select:

    Mark Directory As > Sources Root

PyCharm may need to restart or reindex before the warnings disappear.
These editor warnings do not affect test execution. A project can have more
than one Sources Root, including a Sources Root inside a nested example or
subproject.
"""

from __future__ import annotations

import pytest
from sample_package.helpers.arithmetic_functions import add, divide, percentage


def test_02_adds_positive_numbers() -> None:
    print("")
    print("test_02_adds_positive_numbers")
    result = add(4, 7)
    print(f" add(4,7) -> {result}")
    assert result == 11


def test_03_adds_negative_numbers() -> None:
    assert add(-4, -7) == -11


def test_04_adds_mixed_sign_numbers() -> None:
    assert add(-4, 7) == 3


@pytest.mark.parametrize(
    ("dividend", "divisor", "expected"),
    [
        pytest.param(
            12,
            3,
            4,
            id="whole-number-result",
        ),
        pytest.param(
            5,
            2,
            2.5,
            id="decimal-result",
        ),
        pytest.param(
            -12,
            3,
            -4,
            id="negative-result",
        ),
    ],
)
def test_05_divides_numbers(
    dividend: float,
    divisor: float,
    expected: float,
) -> None:
    result = divide(dividend, divisor)
    print("")
    print("test_05_divides_numbers")
    print(
        f"divide({dividend}, {divisor}) "
        f"returned {result}; expected {expected}"
    )

    assert result == expected


@pytest.mark.parametrize(
    ("part", "whole", "expected"),
    [
        pytest.param(
            25,
            100,
            25,
            id="quarter",
        ),
        pytest.param(
            1,
            4,
            25,
            id="fraction",
        ),
        pytest.param(
            15,
            60,
            25,
            id="non-round-inputs",
        ),
    ],
)
def test_06_calculates_percentage(
    part: float,
    whole: float,
    expected: float,
) -> None:
    result = percentage(part, whole)

    print("")
    print("test_06_calculates_percentage")
    print(
        f"percentage(part={part}, whole={whole}) "
        f"returned {result}; expected {expected}"
    )

    assert result == expected
