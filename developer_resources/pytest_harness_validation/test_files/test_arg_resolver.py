"""
test_arg_resolver.py

Last edited: 2026-08-07
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import pytest_harness.arg_resolver as module

# === Tests ===================================================================

# --- test_01_resolves_and_normalizes_valid_arguments() ------------------------
def test_01_resolves_and_normalizes_valid_arguments(
    tmp_path: Path,
) -> None:
    test_file_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    tested_code_dir = tmp_path / "src"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()

    result = module._resolve_harness_args(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
        include_list=[" test_one ", Path("nested/test_two.py")],
        exclude_list=[" ignored "],
        test_file_logs=False,
        coverage_warning_threshold=85,
        show_source_file_coverage=False,
        log_keep=3,
        console_theme="light",
        dashboard_width=120,
        console_dashboard=False,
        runner_log=False,
        show_skipped_and_xfailed=True,
        debug_harness=True,
        random_order=False,
        random_order_seed=None,
        test_function_timeout=2.5,
    )

    assert result.test_file_dir == test_file_dir.resolve()
    assert result.log_dir == log_dir.resolve()
    assert result.tested_code_dir == tested_code_dir.resolve()

    assert result.include_list == [
        "test_one",
        Path("nested/test_two.py"),
    ]
    assert result.exclude_list == ["ignored"]

    assert result.test_file_logs is False
    assert result.coverage_warning_threshold == 85.0
    assert result.show_source_file_coverage is False
    assert result.log_keep == 3
    assert result.console_theme == "light"
    assert result.dashboard_width == 120
    assert result.console_dashboard is False
    assert result.runner_log is False
    assert result.show_skipped_and_xfailed is True
    assert result.debug_harness is True

    assert result.random_order is False
    assert result.random_order_seed is None

    assert result.test_function_timeout == 2.5

    assert log_dir.is_dir()


# --- test_02_creates_missing_log_directory() ----------------------------------
def test_02_creates_missing_log_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_file_dir = tmp_path / "tests"
    log_dir = tmp_path / "nested" / "logs"
    tested_code_dir = tmp_path / "src"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()

    result = module._resolve_harness_args(
        **_valid_args(
            test_file_dir=test_file_dir,
            log_dir=log_dir,
            tested_code_dir=tested_code_dir,
        )
    )

    output = capsys.readouterr().out

    assert result.log_dir == log_dir.resolve()
    assert log_dir.is_dir()
    assert "Creating log directory:" in output
    assert str(log_dir.resolve()) in output


# --- test_03_path_arguments_require_path_instances() --------------------------
@pytest.mark.parametrize(
    ("argument_name", "value"),
    [
        pytest.param("test_file_dir", "tests", id="test-dir-string"),
        pytest.param("log_dir", "logs", id="log-dir-string"),
        pytest.param("tested_code_dir", "src", id="source-dir-string"),
    ],
)
def test_03_path_arguments_require_path_instances(
    tmp_path: Path,
    argument_name: str,
    value: object,
) -> None:
    kwargs = _valid_args(tmp_path=tmp_path)
    kwargs[argument_name] = value

    with pytest.raises(
        TypeError,
        match=rf"{argument_name} must be a pathlib\.Path instance",
    ):
        module._resolve_harness_args(**kwargs)


# --- test_04_required_input_directories_must_exist() --------------------------
@pytest.mark.parametrize(
    ("argument_name", "message"),
    [
        pytest.param(
            "test_file_dir",
            "Test directory does not exist",
            id="missing-test-directory",
        ),
        pytest.param(
            "tested_code_dir",
            "Source directory does not exist",
            id="missing-source-directory",
        ),
    ],
)
def test_04_required_input_directories_must_exist(
    tmp_path: Path,
    argument_name: str,
    message: str,
) -> None:
    test_file_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    tested_code_dir = tmp_path / "src"

    if argument_name != "test_file_dir":
        test_file_dir.mkdir()

    if argument_name != "tested_code_dir":
        tested_code_dir.mkdir()

    kwargs = _valid_args(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
    )

    with pytest.raises(RuntimeError, match=message):
        module._resolve_harness_args(**kwargs)


# --- test_05_required_input_paths_must_be_directories() -----------------------
@pytest.mark.parametrize(
    ("argument_name", "message"),
    [
        pytest.param(
            "test_file_dir",
            "Test directory path is not a directory",
            id="test-path-is-file",
        ),
        pytest.param(
            "tested_code_dir",
            "Source directory path is not a directory",
            id="source-path-is-file",
        ),
    ],
)
def test_05_required_input_paths_must_be_directories(
    tmp_path: Path,
    argument_name: str,
    message: str,
) -> None:
    test_file_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    tested_code_dir = tmp_path / "src"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()

    invalid_path = tmp_path / f"{argument_name}.txt"
    invalid_path.write_text(
        "not a directory",
        encoding="utf-8",
    )

    kwargs = _valid_args(
        test_file_dir=test_file_dir,
        log_dir=log_dir,
        tested_code_dir=tested_code_dir,
    )
    kwargs[argument_name] = invalid_path

    with pytest.raises(RuntimeError, match=message):
        module._resolve_harness_args(**kwargs)


# --- test_06_existing_log_path_must_be_directory() ----------------------------
def test_06_existing_log_path_must_be_directory(
    tmp_path: Path,
) -> None:
    test_file_dir = tmp_path / "tests"
    tested_code_dir = tmp_path / "src"
    log_dir = tmp_path / "logs.txt"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()
    log_dir.write_text(
        "not a directory",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="Log directory path exists but is not a directory",
    ):
        module._resolve_harness_args(
            **_valid_args(
                test_file_dir=test_file_dir,
                log_dir=log_dir,
                tested_code_dir=tested_code_dir,
            )
        )


# --- test_07_include_list_validation() ----------------------------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            "test_one",
            TypeError,
            "include_list must be a list",
            id="not-list",
        ),
        pytest.param(
            [],
            ValueError,
            "include_list cannot be empty",
            id="empty-list",
        ),
        pytest.param(
            [1],
            TypeError,
            r"include_list\[0\] must be str or Path",
            id="invalid-entry-type",
        ),
        pytest.param(
            ["   "],
            ValueError,
            r"include_list\[0\] cannot be an empty string",
            id="blank-string",
        ),
    ],
)
def test_07_include_list_validation(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                include_list=value,
            )
        )


# --- test_08_exclude_list_validation() ----------------------------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            "test_one",
            TypeError,
            "exclude_list must be a list",
            id="not-list",
        ),
        pytest.param(
            [],
            ValueError,
            "exclude_list cannot be empty",
            id="empty-list",
        ),
        pytest.param(
            [object()],
            TypeError,
            r"exclude_list\[0\] must be str or Path",
            id="invalid-entry-type",
        ),
        pytest.param(
            [""],
            ValueError,
            r"exclude_list\[0\] cannot be an empty string",
            id="blank-string",
        ),
    ],
)
def test_08_exclude_list_validation(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                exclude_list=value,
            )
        )


# --- test_09_coverage_warning_threshold_accepts_valid_values() ----------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="disabled"),
        pytest.param(0, 0.0, id="zero"),
        pytest.param(85, 85.0, id="integer"),
        pytest.param(85.5, 85.5, id="float"),
        pytest.param(100, 100.0, id="one-hundred"),
    ],
)
def test_09_coverage_warning_threshold_accepts_valid_values(
    tmp_path: Path,
    value: float | int | None,
    expected: float | None,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            coverage_warning_threshold=value,
        )
    )

    assert result.coverage_warning_threshold == expected


# --- test_10_coverage_warning_threshold_rejects_invalid_values() --------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "coverage_warning_threshold must be a number or None",
            id="bool",
        ),
        pytest.param(
            "85",
            TypeError,
            "coverage_warning_threshold must be a number or None",
            id="string",
        ),
        pytest.param(
            -0.1,
            ValueError,
            "coverage_warning_threshold must be between",
            id="below-zero",
        ),
        pytest.param(
            100.1,
            ValueError,
            "coverage_warning_threshold must be between",
            id="above-one-hundred",
        ),
    ],
)
def test_10_coverage_warning_threshold_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                coverage_warning_threshold=value,
            )
        )


# --- test_11_boolean_arguments_require_actual_bool() --------------------------
@pytest.mark.parametrize(
    "argument_name",
    [
        "test_file_logs",
        "show_source_file_coverage",
        "console_dashboard",
        "runner_log",
        "show_skipped_and_xfailed",
        "debug_harness",
        "random_order",
    ],
)
@pytest.mark.parametrize(
    "value",
    [0, 1, "true", None],
)
def test_11_boolean_arguments_require_actual_bool(
    tmp_path: Path,
    argument_name: str,
    value: object,
) -> None:
    kwargs = _valid_args(tmp_path=tmp_path)
    kwargs[argument_name] = value

    with pytest.raises(
        TypeError,
        match=rf"{argument_name} must be bool",
    ):
        module._resolve_harness_args(**kwargs)


# --- test_12_log_keep_accepts_valid_values() ----------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="none"),
        pytest.param(1, 1, id="one"),
        pytest.param(7, 7, id="seven"),
    ],
)
def test_12_log_keep_accepts_valid_values(
    tmp_path: Path,
    value: int | None,
    expected: int | None,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            log_keep=value,
        )
    )

    assert result.log_keep == expected


# --- test_13_log_keep_rejects_invalid_values() --------------------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "log_keep must be an int or None",
            id="bool",
        ),
        pytest.param(
            1.5,
            TypeError,
            "log_keep must be an int or None",
            id="float",
        ),
        pytest.param(
            0,
            ValueError,
            "log_keep must be at least 1",
            id="zero",
        ),
        pytest.param(
            -1,
            ValueError,
            "log_keep must be at least 1",
            id="negative",
        ),
    ],
)
def test_13_log_keep_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                log_keep=value,
            )
        )


# --- test_14_dashboard_width_accepts_valid_values() ---------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(80, 80, id="minimum"),
        pytest.param(150, 150, id="default"),
        pytest.param(200, 200, id="wide"),
    ],
)
def test_14_dashboard_width_accepts_valid_values(
    tmp_path: Path,
    value: int,
    expected: int,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            dashboard_width=value,
        )
    )

    assert result.dashboard_width == expected


# --- test_15_dashboard_width_rejects_invalid_values() -------------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "dashboard_width must be an int",
            id="bool",
        ),
        pytest.param(
            100.5,
            TypeError,
            "dashboard_width must be an int",
            id="float",
        ),
        pytest.param(
            79,
            ValueError,
            "dashboard_width must be at least 80",
            id="below-minimum",
        ),
    ],
)
def test_15_dashboard_width_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                dashboard_width=value,
            )
        )


# --- test_16_random_order_generates_seed_when_not_supplied() ------------------
def test_16_random_order_generates_seed_when_not_supplied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "randbelow",
        lambda upper: 1233,
    )

    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            random_order=True,
            random_order_seed=None,
        )
    )

    assert result.random_order is True
    assert result.random_order_seed == 1234


# --- test_17_random_order_uses_supplied_seed() --------------------------------
def test_17_random_order_uses_supplied_seed(
    tmp_path: Path,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            random_order=True,
            random_order_seed=987654,
        )
    )

    assert result.random_order is True
    assert result.random_order_seed == 987654


# --- test_18_random_order_disabled_has_no_resolved_seed() ---------------------
def test_18_random_order_disabled_has_no_resolved_seed(
    tmp_path: Path,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            random_order=False,
            random_order_seed=1234,
        )
    )

    assert result.random_order is False
    assert result.random_order_seed is None


# --- test_19_random_order_seed_rejects_invalid_values() -----------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "random_order_seed must be an int or None",
            id="bool",
        ),
        pytest.param(
            1.5,
            TypeError,
            "random_order_seed must be an int or None",
            id="float",
        ),
        pytest.param(
            "1234",
            TypeError,
            "random_order_seed must be an int or None",
            id="string",
        ),
        pytest.param(
            0,
            ValueError,
            "random_order_seed must be at least 1",
            id="zero",
        ),
        pytest.param(
            -1,
            ValueError,
            "random_order_seed must be at least 1",
            id="negative",
        ),
    ],
)
def test_19_random_order_seed_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                random_order=True,
                random_order_seed=value,
            )
        )


# --- test_20_test_function_timeout_accepts_valid_values() ---------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="disabled"),
        pytest.param(1, 1.0, id="integer"),
        pytest.param(0.5, 0.5, id="fractional"),
        pytest.param(2.5, 2.5, id="float"),
    ],
)
def test_20_test_function_timeout_accepts_valid_values(
    tmp_path: Path,
    value: int | float | None,
    expected: float | None,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            test_function_timeout=value,
        )
    )

    assert result.test_function_timeout == expected


# --- test_21_test_function_timeout_rejects_invalid_values() -------------------
@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "test_function_timeout must be an int, float, or None",
            id="bool",
        ),
        pytest.param(
            "2",
            TypeError,
            "test_function_timeout must be an int, float, or None",
            id="string",
        ),
        pytest.param(
            0,
            ValueError,
            "test_function_timeout must be greater than 0 seconds",
            id="zero",
        ),
        pytest.param(
            -1,
            ValueError,
            "test_function_timeout must be greater than 0 seconds",
            id="negative",
        ),
    ],
)
def test_21_test_function_timeout_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                test_function_timeout=value,
            )
        )


# --- test_22_console_theme_normalizes_valid_values() --------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("dark", "dark", id="dark"),
        pytest.param("light", "light", id="light"),
        pytest.param(" LIGHT ", "light", id="normalized"),
    ],
)
def test_22_console_theme_normalizes_valid_values(
    tmp_path: Path,
    value: str,
    expected: str,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            console_theme=value,
        )
    )

    assert result.console_theme == expected


# --- test_23_log_directory_not_created_when_validation_fails() ---------------
def test_23_log_directory_not_created_when_validation_fails(
    tmp_path: Path,
) -> None:
    test_file_dir = tmp_path / "tests"
    tested_code_dir = tmp_path / "src"
    log_dir = tmp_path / "new" / "logs"

    test_file_dir.mkdir()
    tested_code_dir.mkdir()

    with pytest.raises(
        TypeError,
        match="test_file_logs must be bool",
    ):
        module._resolve_harness_args(
            **_valid_args(
                test_file_dir=test_file_dir,
                log_dir=log_dir,
                tested_code_dir=tested_code_dir,
                test_file_logs="yes",
            )
        )

    assert not log_dir.exists()

# --- test_24_invalid_console_theme_warns_and_uses_dark() ----------------------
def test_24_invalid_console_theme_warns_and_uses_dark(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            console_theme="invalid",
        )
    )

    output = capsys.readouterr().out

    assert result.console_theme == "dark"
    assert "WARNING:" in output
    assert 'console_theme must be either "dark" or "light"' in output
    assert '(default="dark")' in output


# --- test_25_console_theme_requires_string() ----------------------------------
def test_25_console_theme_requires_string(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match='console_theme must be "dark" or "light"',
    ):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                console_theme=123,
            )
        )


# === Internal helpers =========================================================

def _valid_args(
    *,
    tmp_path: Path | None = None,
    test_file_dir: Path | None = None,
    log_dir: Path | None = None,
    tested_code_dir: Path | None = None,
    include_list: object = None,
    exclude_list: object = None,
    test_file_logs: object = True,
    coverage_warning_threshold: object = 85.0,
    show_source_file_coverage: object = True,
    log_keep: object = None,
    console_theme: object = "dark",
    dashboard_width: object = 150,
    console_dashboard: object = True,
    runner_log: object = True,
    show_skipped_and_xfailed: object = False,
    debug_harness: object = False,
    random_order: object = False,
    random_order_seed: object = None,
    test_function_timeout: object = None,
) -> dict[str, Any]:
    if tmp_path is not None:
        test_file_dir = tmp_path / "tests"
        log_dir = tmp_path / "logs"
        tested_code_dir = tmp_path / "src"

        test_file_dir.mkdir(exist_ok=True)
        tested_code_dir.mkdir(exist_ok=True)

    assert test_file_dir is not None
    assert log_dir is not None
    assert tested_code_dir is not None

    return {
        "test_file_dir": test_file_dir,
        "log_dir": log_dir,
        "tested_code_dir": tested_code_dir,
        "include_list": include_list,
        "exclude_list": exclude_list,
        "test_file_logs": test_file_logs,
        "coverage_warning_threshold": coverage_warning_threshold,
        "show_source_file_coverage": show_source_file_coverage,
        "log_keep": log_keep,
        "console_theme": console_theme,
        "dashboard_width": dashboard_width,
        "console_dashboard": console_dashboard,
        "runner_log": runner_log,
        "show_skipped_and_xfailed": show_skipped_and_xfailed,
        "debug_harness": debug_harness,
        "random_order": random_order,
        "random_order_seed": random_order_seed,
        "test_function_timeout": test_function_timeout,
    }
