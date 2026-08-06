"""
test_import_error.py

Tests for intentional import error.



To remove unresolved-reference warnings in the IDE editor, right-click the
src directory and select:

    Mark Directory As > Sources Root

PyCharm may need to restart or reindex before the warnings disappear.
These editor warnings do not affect test execution. A project can have more
than one Sources Root, including a Sources Root inside a nested example or
subproject.
"""

from __future__ import annotations

from sample_package.helpers.arithmetic_functions import ad


def test_01_adds_positive_numbers() -> None:
    print("test_01_adds_positive_numbers")
    result = add(4, 7)
    print(f" add(4,7) -> {result}")
    assert result == 11

