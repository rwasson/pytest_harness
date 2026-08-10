# test_test_function_timeout_example.py

import time


def test_finishes_quickly() -> None:
    assert True


def test_exceeds_test_function_timeout() -> None:
    time.sleep(5)


def test_after_test_function_timeout() -> None:
    assert True
