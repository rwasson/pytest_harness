"""
test_calculator.py

Tests for successful calculator operations.
"""

from __future__ import annotations

import pytest
from sample_package.calculator import (
    add,
    divide,
    percentage,
)


def test_adds_positive_numbers() -> None:
    assert add(4, 7) == 11


def test_adds_negative_numbers() -> None:
    assert add(-4, -7) == -11


def test_adds_mixed_sign_numbers() -> None:
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
def test_divides_numbers(
    dividend: float,
    divisor: float,
    expected: float,
) -> None:
    assert divide(dividend, divisor) == expected


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
def test_calculates_percentage(
    part: float,
    whole: float,
    expected: float,
) -> None:
    assert percentage(part, whole) == expected
