"""
test_validation.py

Tests for calculator validation and error handling.

Printed diagnostic details are included in this test file's individual log.
This can be useful for recording accepted inputs, rejected inputs, returned
values, and expected exceptions without adding them to the main summary.

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
from sample_package.calculator import (
    CalculatorError,
    divide,
    parse_number,
    percentage,
)


def test_01_divide_rejects_zero_divisor() -> None:
    with pytest.raises(
        CalculatorError,
        match="Divisor cannot be zero",
    ) as error_info:
        divide(10, 0)

    print("test_01_divide_rejects_zero_divisor")
    print(
        "divide(10, 0) raised "
        f"{type(error_info.value).__name__}: {error_info.value}"
    )


def test_02_percentage_rejects_zero_whole() -> None:
    with pytest.raises(
        CalculatorError,
        match="percentage of zero",
    ) as error_info:
        percentage(10, 0)

    print("")
    print("test_02_percentage_rejects_zero_whole")
    print(
        "percentage(10, 0) raised "
        f"{type(error_info.value).__name__}: {error_info.value}"
    )


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
def test_03_parse_number_accepts_valid_text(
    value: str,
    expected: float,
) -> None:
    result = parse_number(value)

    print("")
    print("test_03_parse_number_accepts_valid_text")
    print(
        f"parse_number({value!r}) returned {result}; "
        f"expected {expected}"
    )

    assert result == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace"),
    ],
)
def test_04_parse_number_rejects_empty_text(
    value: str,
) -> None:
    with pytest.raises(
        CalculatorError,
        match="Number cannot be empty",
    ) as error_info:
        parse_number(value)

    print("")
    print("test_04_parse_number_rejects_empty_text")
    print(
        f"parse_number({value!r}) raised "
        f"{type(error_info.value).__name__}: {error_info.value}"
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("twelve", id="word"),
        pytest.param("12.3.4", id="multiple-decimal-points"),
        pytest.param("$10", id="currency-symbol"),
    ],
)
def test_05_parse_number_rejects_invalid_text(
    value: str,
) -> None:
    with pytest.raises(
        CalculatorError,
        match="Invalid number",
    ) as error_info:
        parse_number(value)

    print("")
    print("test_05_parse_number_rejects_invalid_text")
    print(
        f"parse_number({value!r}) raised "
        f"{type(error_info.value).__name__}: {error_info.value}"
    )
