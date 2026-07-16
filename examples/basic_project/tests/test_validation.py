"""
test_validation.py

Tests for calculator validation and error handling.
"""

from __future__ import annotations

import pytest
from sample_package.calculator import (
    CalculatorError,
    divide,
    parse_number,
    percentage,
)


def test_divide_rejects_zero_divisor() -> None:
    with pytest.raises(
        CalculatorError,
        match="Divisor cannot be zero",
    ):
        divide(10, 0)


def test_percentage_rejects_zero_whole() -> None:
    with pytest.raises(
        CalculatorError,
        match="percentage of zero",
    ):
        percentage(10, 0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            "12",
            12.0,
            id="integer-text",
        ),
        pytest.param(
            "12.5",
            12.5,
            id="decimal-text",
        ),
        pytest.param(
            "  -3.25  ",
            -3.25,
            id="surrounding-whitespace",
        ),
        pytest.param(
            "1e2",
            100.0,
            id="scientific-notation",
        ),
    ],
)
def test_parse_number_accepts_valid_text(
    value: str,
    expected: float,
) -> None:
    assert parse_number(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace"),
    ],
)
def test_parse_number_rejects_empty_text(
    value: str,
) -> None:
    with pytest.raises(
        CalculatorError,
        match="Number cannot be empty",
    ):
        parse_number(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("twelve", id="word"),
        pytest.param("12.3.4", id="multiple-decimal-points"),
        pytest.param("$10", id="currency-symbol"),
    ],
)
def test_parse_number_rejects_invalid_text(
    value: str,
) -> None:
    with pytest.raises(
        CalculatorError,
        match="Invalid number",
    ):
        parse_number(value)
