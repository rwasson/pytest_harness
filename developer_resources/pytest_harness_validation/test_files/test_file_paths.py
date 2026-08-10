"""
test_file_paths.py

Tests test-file discovery, selection, resolution, and generated artifact paths.

Last edited: 2026-08-08
"""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

import pytest

import pytest_harness.file_path_builder as file_path_builder
from pytest_harness.constants_and_classes import (
    HASH_LENGTH,
    MAX_LOGDUO_STEM_LENGTH,
    WINDOWS_SAFE_PATH_LENGTH,
)
from pytest_harness.resolve_test_file_paths import (
    _resolve_test_file_paths,
)

_IS_WINDOWS = os.name == "nt"


# === Test-file discovery and selection ========================================

def test_01_discovers_test_files_recursively_and_returns_relative_sorted_paths(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_z.py")
    _write(tmp_path / "nested" / "test_a.py")
    _write(tmp_path / "nested" / "helper.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=None,
        exclude_list=None,
    )

    assert result == [
        Path("nested/test_a.py"),
        Path("test_z.py"),
    ]


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        pytest.param(
            "test_one.py",
            [Path("test_one.py")],
            id="string-with-suffix",
        ),
        pytest.param(
            "test_one",
            [Path("test_one.py")],
            id="string-without-suffix",
        ),
        pytest.param(
            Path("test_one.py"),
            [Path("test_one.py")],
            id="path-with-suffix",
        ),
    ],
)
def test_02_include_list_accepts_file_selectors_with_or_without_suffix(
    tmp_path: Path,
    selector: str | Path,
    expected: list[Path],
) -> None:
    _write(tmp_path / "test_one.py")
    _write(tmp_path / "test_two.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=[selector],
        exclude_list=None,
    )

    assert result == expected


def test_03_include_directory_discovers_only_test_files_below_it(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "group" / "test_one.py")
    _write(tmp_path / "group" / "nested" / "test_two.py")
    _write(tmp_path / "other" / "test_three.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=["group"],
        exclude_list=None,
    )

    assert result == [
        Path("group/nested/test_two.py"),
        Path("group/test_one.py"),
    ]


def test_04_exclude_list_removes_files_and_directories(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_keep.py")
    _write(tmp_path / "test_remove.py")
    _write(tmp_path / "group" / "test_nested.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=None,
        exclude_list=[
            "test_remove",
            "group",
        ],
    )

    assert result == [
        Path("test_keep.py"),
    ]


def test_05_duplicate_include_entries_are_deduplicated(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_one.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=[
            "test_one",
            "test_one.py",
            Path("test_one.py"),
        ],
        exclude_list=None,
    )

    assert result == [
        Path("test_one.py"),
    ]


def test_06_absolute_selector_inside_test_file_directory_is_supported(
    tmp_path: Path,
) -> None:
    test_file = _write(
        tmp_path / "nested" / "test_one.py"
    )

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=[test_file],
        exclude_list=None,
    )

    assert result == [
        Path("nested/test_one.py"),
    ]


def test_07_ambiguous_file_and_directory_selector_uses_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "group.py")
    _write(tmp_path / "group" / "test_nested.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=["group"],
        exclude_list=None,
    )

    output = capsys.readouterr().out

    assert result == [
        Path("group/test_nested.py"),
    ]
    assert "Ambiguous pytest_harness selector" in output
    assert "Using directory" in output


def test_08_missing_test_file_directory_raises(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(
        RuntimeError,
        match="Test directory does not exist",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=missing,
            include_list=None,
            exclude_list=None,
        )


def test_09_test_file_directory_path_must_be_directory(
    tmp_path: Path,
) -> None:
    file_path = _write(
        tmp_path / "not_a_directory.py"
    )

    with pytest.raises(
        RuntimeError,
        match="is not a directory",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=file_path,
            include_list=None,
            exclude_list=None,
        )


def test_10_missing_explicit_py_file_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="Unrecognized test file in include_list",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=tmp_path,
            include_list=["missing.py"],
            exclude_list=None,
        )


def test_11_missing_suffixless_selector_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="Unrecognized test selector in include_list",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=tmp_path,
            include_list=["missing"],
            exclude_list=None,
        )


def test_12_raises_when_selection_is_empty(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "helper.py")

    with pytest.raises(
        RuntimeError,
        match="No pytest test files selected",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=tmp_path,
            include_list=None,
            exclude_list=None,
        )


def test_13_raises_when_exclusions_remove_everything(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_only.py")

    with pytest.raises(
        RuntimeError,
        match="No pytest test files selected",
    ):
        _resolve_test_file_paths(
            test_file_dir_path=tmp_path,
            include_list=None,
            exclude_list=["test_only"],
        )


def test_14_exclude_list_is_applied_after_include_list(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "group" / "test_keep.py")
    _write(tmp_path / "group" / "test_remove.py")
    _write(tmp_path / "other" / "test_other.py")

    result = _resolve_test_file_paths(
        test_file_dir_path=tmp_path,
        include_list=["group"],
        exclude_list=["group/test_remove"],
    )

    assert result == [
        Path("group/test_keep.py"),
    ]


# === Artifact path building ===================================================

def test_15_builds_expected_artifact_paths_for_simple_test_file(
    tmp_path: Path,
) -> None:
    test_file_dir = tmp_path / "tests"
    output_dir = tmp_path / "logs"
    coverage_dir = tmp_path / "coverage"

    result = file_path_builder._build_file_paths(
        relative_test_file_path=Path("test_example.py"),
        test_file_dir=test_file_dir,
        output_dir_path=output_dir,
        coverage_temp_dir_path=coverage_dir,
    )

    assert (
        result.test_file_path
        == test_file_dir / "test_example.py"
    )
    assert (
        result.test_file_log_path
        == output_dir / "test_example.log"
    )
    assert (
        result.coverage_data_file_path
        == coverage_dir / ".coverage.test_example"
    )
    assert (
        result.progress_file_path
        == coverage_dir / "progress_test_example.txt"
    )
    assert result.test_file_log_name_was_shortened is False


def test_16_nested_test_path_is_flattened_with_double_underscores(
    tmp_path: Path,
) -> None:
    result = file_path_builder._build_file_paths(
        relative_test_file_path=Path(
            "unit_tests/nested/test_calculator.py"
        ),
        test_file_dir=tmp_path / "tests",
        output_dir_path=tmp_path / "logs",
        coverage_temp_dir_path=tmp_path / "coverage",
    )

    assert result.test_file_path == (
        tmp_path
        / "tests"
        / "unit_tests"
        / "nested"
        / "test_calculator.py"
    )

    assert result.test_file_log_path.name == (
        "unit_tests__nested__test_calculator.log"
    )

    assert result.coverage_data_file_path.name == (
        ".coverage.unit_tests__nested__test_calculator"
    )

    assert result.progress_file_path.name == (
        "progress_unit_tests__nested__test_calculator.txt"
    )


def test_17_safe_stem_removes_python_suffix() -> None:
    stem, was_shortened = file_path_builder._build_safe_stem(
        Path("nested/test_example.py"),
        parent_dir_path=Path("/tmp"),
    )

    assert stem == "nested__test_example"
    assert was_shortened is False


def test_18_safe_stem_preserves_suffixless_path_parts() -> None:
    stem, was_shortened = file_path_builder._build_safe_stem(
        Path("group/test_example"),
        parent_dir_path=Path("/tmp"),
    )

    assert stem == "group__test_example"
    assert was_shortened is False


def test_19_safe_stem_shortens_long_name_and_adds_stable_hash() -> None:
    relative_path = Path(
        "nested"
    ) / (
        "a" * (MAX_LOGDUO_STEM_LENGTH + 50)
        + ".py"
    )

    original_stem = "__".join(
        relative_path.with_suffix("").parts
    )

    expected_hash = sha256(
        original_stem.encode("utf-8")
    ).hexdigest()[:HASH_LENGTH]

    stem, was_shortened = file_path_builder._build_safe_stem(
        relative_path,
        parent_dir_path=Path("/tmp"),
    )

    assert was_shortened is True
    assert len(stem) <= MAX_LOGDUO_STEM_LENGTH
    assert stem.endswith(
        f"__{expected_hash}"
    )


def test_20_safe_stem_shortening_is_deterministic() -> None:
    relative_path = Path(
        "nested"
    ) / (
        "z" * (MAX_LOGDUO_STEM_LENGTH + 100)
        + ".py"
    )

    first = file_path_builder._build_safe_stem(
        relative_path,
        parent_dir_path=Path("/tmp"),
    )

    second = file_path_builder._build_safe_stem(
        relative_path,
        parent_dir_path=Path("/tmp"),
    )

    assert first == second


def test_21_different_long_paths_receive_different_hash_suffixes() -> None:
    first_path = Path(
        "nested"
    ) / (
        "a" * (MAX_LOGDUO_STEM_LENGTH + 100)
        + ".py"
    )

    second_path = Path(
        "nested"
    ) / (
        "b" * (MAX_LOGDUO_STEM_LENGTH + 100)
        + ".py"
    )

    first_stem, first_shortened = (
        file_path_builder._build_safe_stem(
            first_path,
            parent_dir_path=Path("/tmp"),
        )
    )

    second_stem, second_shortened = (
        file_path_builder._build_safe_stem(
            second_path,
            parent_dir_path=Path("/tmp"),
        )
    )

    assert first_shortened is True
    assert second_shortened is True
    assert first_stem != second_stem


def test_22_build_file_paths_reports_when_log_stem_was_shortened(
    tmp_path: Path,
) -> None:
    long_name = (
        "x" * (MAX_LOGDUO_STEM_LENGTH + 100)
    )

    result = file_path_builder._build_file_paths(
        relative_test_file_path=Path(
            f"{long_name}.py"
        ),
        test_file_dir=tmp_path / "tests",
        output_dir_path=tmp_path / "logs",
        coverage_temp_dir_path=tmp_path / "coverage",
    )

    assert result.test_file_log_name_was_shortened is True
    assert len(result.test_file_log_path.stem) <= MAX_LOGDUO_STEM_LENGTH


def test_23_prefix_and_suffix_are_accounted_for_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_path_builder,
        "_IS_WINDOWS",
        True,
    )

    parent_dir = tmp_path / ("p" * 80)

    fixed_path = parent_dir / "progress_.txt"

    expected_max_length = min(
        MAX_LOGDUO_STEM_LENGTH,
        WINDOWS_SAFE_PATH_LENGTH - len(str(fixed_path)),
    )

    long_path = Path(
        "nested"
    ) / (
        "x" * (MAX_LOGDUO_STEM_LENGTH + 100)
        + ".py"
    )

    stem, was_shortened = file_path_builder._build_safe_stem(
        long_path,
        parent_dir_path=parent_dir,
        filename_prefix="progress_",
        filename_suffix=".txt",
    )

    assert was_shortened is True
    assert len(stem) <= expected_max_length


def test_24_windows_short_stem_is_not_shortened_unnecessarily(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_path_builder,
        "_IS_WINDOWS",
        True,
    )

    stem, was_shortened = file_path_builder._build_safe_stem(
        Path("nested/test_one.py"),
        parent_dir_path=tmp_path,
        filename_prefix=".coverage.",
    )

    assert stem == "nested__test_one"
    assert was_shortened is False


# === Internal helpers =========================================================

def _write(
    path: Path,
    text: str = "def test_placeholder():\n    pass\n",
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    return path
