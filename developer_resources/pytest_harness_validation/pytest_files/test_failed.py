"""
test_failed.py

Testing an intentionally failing test

Last edited: 2026-7-20
"""


def test_1_intentional_fail():
    print("intentional failed test to demonstrate dashboard")
    print("assert 2==3")

    assert 2 == 3
