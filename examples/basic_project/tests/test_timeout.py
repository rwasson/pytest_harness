# test_test_function_timeout_example.py


import time


def test_01_finishes_quickly() -> None:
    assert True


def test_02_exceeds_test_function_timeout() -> None:
    time.sleep(5)


def test_03_after_test_function_timeout() -> None:
    assert True


