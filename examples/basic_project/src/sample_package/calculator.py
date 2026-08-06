"""
calculator.py

Small example module with ordinary calculations and input validation.
"""

from __future__ import annotations

from sample_package.helpers.arithmetic_functions import add, divide, percentage


def calculation_report(
    operation: str,
    first: float,
    second: float,
) -> str:
    """Return a formatted report for a completed calculation for add, divide, and percentage."""

    if operation == "add":
        result = add(first, second)
    elif operation == "divide":
        result = divide(first, second)
    elif operation == "percentage":
        result = percentage(first, second)
    else:
        result = "Not a valid operation"

    return (
        f"Calculation report\n"
        f"------------------\n"
        f"Operation: {operation}\n"
        f"First:     {first:g}\n"
        f"Second:    {second:g}\n"
        f"Result:    {result:g}"
    )


