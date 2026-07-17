"""
test_arg_resolver.py

Last edited: 2026-07-16
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pytest_harness.arg_resolver as module

# === Tests ===================================================================

def test_01_resolves_and_normalizes_valid_arguments(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"

    test_dir.mkdir()
    source_dir.mkdir()

    result = module._resolve_harness_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        include_list=[" test_one ", Path("nested/test_two.py")],
        exclude_list=[" ignored "],
        coverage_warning_threshold=85,
        individual_logs=False,
        show_source_file_coverage=False,
        log_keep=3,
        console_wrap_width=120,
        debug_pytest_harness=True,
    )

    assert result.test_dir == test_dir.resolve()
    assert result.log_dir == log_dir.resolve()
    assert result.source_dir == source_dir.resolve()

    assert result.include_list == [
        "test_one",
        Path("nested/test_two.py"),
    ]
    assert result.exclude_list == ["ignored"]

    assert result.coverage_warning_threshold == 85.0
    assert result.individual_logs is False
    assert result.show_source_file_coverage is False
    assert result.log_keep == 3
    assert result.console_wrap_width == 120
    assert result.debug_pytest_harness is True

    assert log_dir.is_dir()


def test_02_creates_missing_log_directory_and_prints_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "nested" / "logs"
    source_dir = tmp_path / "src"

    test_dir.mkdir()
    source_dir.mkdir()

    result = module._resolve_harness_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
        include_list=None,
        exclude_list=None,
        coverage_warning_threshold=None,
        individual_logs=True,
        show_source_file_coverage=True,
        log_keep=None,
        console_wrap_width=150,
        debug_pytest_harness=False,
    )

    output = capsys.readouterr().out

    assert result.log_dir == log_dir.resolve()
    assert log_dir.is_dir()
    assert "Creating log directory:" in output
    assert str(log_dir.resolve()) in output


@pytest.mark.parametrize(
    ("argument_name", "value"),
    [
        pytest.param("test_dir", "tests", id="test-dir-string"),
        pytest.param("log_dir", "logs", id="log-dir-string"),
        pytest.param("source_dir", "src", id="source-dir-string"),
    ],
)
def test_03_path_arguments_must_be_path_instances(
    tmp_path: Path,
    argument_name: str,
    value: object,
) -> None:
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"

    test_dir.mkdir()
    source_dir.mkdir()

    kwargs = _valid_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
    )
    kwargs[argument_name] = value

    with pytest.raises(
        TypeError,
        match=rf"{argument_name} must be a pathlib\.Path instance",
    ):
        module._resolve_harness_args(**kwargs)


@pytest.mark.parametrize(
    ("argument_name", "message"),
    [
        pytest.param(
            "test_dir",
            "Test directory does not exist",
            id="missing-test-directory",
        ),
        pytest.param(
            "source_dir",
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
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"

    if argument_name != "test_dir":
        test_dir.mkdir()

    if argument_name != "source_dir":
        source_dir.mkdir()

    kwargs = _valid_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
    )

    with pytest.raises(RuntimeError, match=message):
        module._resolve_harness_args(**kwargs)


@pytest.mark.parametrize(
    ("argument_name", "message"),
    [
        pytest.param(
            "test_dir",
            "Test directory path is not a directory",
            id="test-path-is-file",
        ),
        pytest.param(
            "source_dir",
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
    test_dir = tmp_path / "tests"
    log_dir = tmp_path / "logs"
    source_dir = tmp_path / "src"

    test_dir.mkdir()
    source_dir.mkdir()

    invalid_path = tmp_path / f"{argument_name}.txt"
    invalid_path.write_text("not a directory", encoding="utf-8")

    kwargs = _valid_args(
        test_dir=test_dir,
        log_dir=log_dir,
        source_dir=source_dir,
    )
    kwargs[argument_name] = invalid_path

    with pytest.raises(RuntimeError, match=message):
        module._resolve_harness_args(**kwargs)


def test_06_existing_log_path_must_be_directory(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "tests"
    source_dir = tmp_path / "src"
    log_dir = tmp_path / "logs.txt"

    test_dir.mkdir()
    source_dir.mkdir()
    log_dir.write_text("not a directory", encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="Log directory path exists but is not a directory",
    ):
        module._resolve_harness_args(
            **_valid_args(
                test_dir=test_dir,
                log_dir=log_dir,
                source_dir=source_dir,
            )
        )


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


@pytest.mark.parametrize(
    "argument_name",
    [
        "individual_logs",
        "show_source_file_coverage",
        "debug_pytest_harness",
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(80, 80, id="minimum"),
        pytest.param(150, 150, id="default"),
    ],
)
def test_14_console_wrap_width_accepts_valid_values(
    tmp_path: Path,
    value: int,
    expected: int,
) -> None:
    result = module._resolve_harness_args(
        **_valid_args(
            tmp_path=tmp_path,
            console_wrap_width=value,
        )
    )

    assert result.console_wrap_width == expected


@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        pytest.param(
            True,
            TypeError,
            "console_wrap_width must be an int",
            id="bool",
        ),
        pytest.param(
            100.5,
            TypeError,
            "console_wrap_width must be an int",
            id="float",
        ),
        pytest.param(
            79,
            ValueError,
            "console_wrap_width must be at least 80",
            id="below-minimum",
        ),
    ],
)
def test_15_console_wrap_width_rejects_invalid_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        module._resolve_harness_args(
            **_valid_args(
                tmp_path=tmp_path,
                console_wrap_width=value,
            )
        )


def test_16_log_directory_is_not_created_when_validation_fails(
    tmp_path: Path,
) -> None:
    test_dir = tmp_path / "tests"
    source_dir = tmp_path / "src"
    log_dir = tmp_path / "new" / "logs"

    test_dir.mkdir()
    source_dir.mkdir()

    with pytest.raises(
        TypeError,
        match="individual_logs must be bool",
    ):
        module._resolve_harness_args(
            **_valid_args(
                test_dir=test_dir,
                log_dir=log_dir,
                source_dir=source_dir,
                individual_logs="yes",
            )
        )

    assert not log_dir.exists()


# === Internal helpers ========================================================

def _valid_args(
    *,
    tmp_path: Path | None = None,
    test_dir: Path | None = None,
    log_dir: Path | None = None,
    source_dir: Path | None = None,
    include_list: object = None,
    exclude_list: object = None,
    coverage_warning_threshold: object = 85.0,
    individual_logs: object = True,
    show_source_file_coverage: object = True,
    log_keep: object = None,
    console_wrap_width: object = 150,
    debug_pytest_harness: object = False,
) -> dict[str, object]:
    if tmp_path is not None:
        test_dir = tmp_path / "tests"
        log_dir = tmp_path / "logs"
        source_dir = tmp_path / "src"

        test_dir.mkdir(exist_ok=True)
        source_dir.mkdir(exist_ok=True)

    assert test_dir is not None
    assert log_dir is not None
    assert source_dir is not None

    return {
        "test_dir": test_dir,
        "log_dir": log_dir,
        "source_dir": source_dir,
        "include_list": include_list,
        "exclude_list": exclude_list,
        "coverage_warning_threshold": coverage_warning_threshold,
        "individual_logs": individual_logs,
        "show_source_file_coverage": show_source_file_coverage,
        "log_keep": log_keep,
        "console_wrap_width": console_wrap_width,
        "debug_pytest_harness": debug_pytest_harness,
    }
