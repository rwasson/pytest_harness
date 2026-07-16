"""
calculator.py

Small example module with ordinary calculations and input validation.
"""

from __future__ import annotations


class CalculatorError(ValueError):
    """Raised when a calculator operation receives an invalid value."""


def add(first: float, second: float) -> float:
    """Return the sum of two numbers."""
    return first + second


def divide(
    dividend: float,
    divisor: float,
) -> float:
    """
    Divide one number by another.

    Raises
    ------
    CalculatorError
        If divisor is zero.
    """
    if divisor == 0:
        raise CalculatorError("Divisor cannot be zero.")

    return dividend / divisor


def percentage(
    part: float,
    whole: float,
) -> float:
    """
    Return part as a percentage of whole.

    Raises
    ------
    CalculatorError
        If whole is zero.
    """
    if whole == 0:
        raise CalculatorError(
            "Cannot calculate a percentage of zero."
        )

    return part / whole * 100


def parse_number(value: str) -> float:
    """
    Convert a string to a floating-point number.

    Leading and trailing whitespace is ignored.

    Raises
    ------
    CalculatorError
        If value is empty or cannot be converted to a number.
    """
    normalized = value.strip()

    if not normalized:
        raise CalculatorError(
            "Number cannot be empty."
        )

    try:
        return float(normalized)
    except ValueError as exc:
        raise CalculatorError(
            f"Invalid number: {value!r}"
        ) from exc
