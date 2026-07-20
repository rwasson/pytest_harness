"""
test_flagged.py

Intentional pytest outcomes used to validate pytest_harness reporting.
"""

from __future__ import annotations

import pytest


def test_01_pass() -> None:
    assert 2 + 2 == 4


@pytest.mark.skip(reason="Intentional skip for pytest_harness testing")
def test_02_skip() -> None:
    assert True


def test_03_intentional_fail() -> None:
    assert 2 + 2 == 5


@pytest.mark.xfail(reason="Intentional expected failure")
def test_04_expected_failure() -> None:
    assert 2 + 2 == 5


'''
@pytest.mark.xfail(reason="Intentional unexpected pass")
def test_05_unexpected_pass() -> None:
    assert 2 + 2 == 4


@pytest.fixture
def broken_fixture() -> None:
    raise RuntimeError(
        "Intentional fixture setup error for pytest_harness testing"
    )


def test_06_error_during_setup(
    broken_fixture: None,
) -> None:
    # This body is never reached.
    pass
'''
