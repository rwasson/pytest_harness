"""
test_resolve_test_file_paths.py

Last edited: 2026-07-16
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_harness.resolve_test_file_paths import (
    _resolve_test_file_paths,
)

# === Tests ===================================================================

def test_01_discovers_test_files_recursively_and_returns_relative_sorted_paths(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_z.py")
    _write(tmp_path / "nested" / "test_a.py")
    _write(tmp_path / "nested" / "helper.py")

    result = _resolve_test_file_paths(
        test_dir_path=tmp_path,
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
        test_dir_path=tmp_path,
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
        test_dir_path=tmp_path,
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
        test_dir_path=tmp_path,
        include_list=None,
        exclude_list=["test_remove", "group"],
    )

    assert result == [Path("test_keep.py")]


def test_05_duplicate_include_entries_are_deduplicated(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "test_one.py")

    result = _resolve_test_file_paths(
        test_dir_path=tmp_path,
        include_list=[
            "test_one",
            "test_one.py",
            Path("test_one.py"),
        ],
        exclude_list=None,
    )

    assert result == [Path("test_one.py")]


def test_06_absolute_selector_inside_test_directory_is_supported(
    tmp_path: Path,
) -> None:
    test_file = _write(
        tmp_path / "nested" / "test_one.py"
    )

    result = _resolve_test_file_paths(
        test_dir_path=tmp_path,
        include_list=[test_file],
        exclude_list=None,
    )

    assert result == [Path("nested/test_one.py")]


def test_07_ambiguous_file_and_directory_selector_uses_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "group.py")
    _write(tmp_path / "group" / "test_nested.py")

    result = _resolve_test_file_paths(
        test_dir_path=tmp_path,
        include_list=["group"],
        exclude_list=None,
    )

    output = capsys.readouterr().out

    assert result == [Path("group/test_nested.py")]
    assert "Ambiguous pytest_harness selector" in output
    assert "Using directory" in output


def test_08_missing_test_directory_raises(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(
        RuntimeError,
        match="Test directory does not exist",
    ):
        _resolve_test_file_paths(
            test_dir_path=missing,
            include_list=None,
            exclude_list=None,
        )


def test_09_test_directory_path_must_be_directory(
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
            test_dir_path=file_path,
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
            test_dir_path=tmp_path,
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
            test_dir_path=tmp_path,
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
            test_dir_path=tmp_path,
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
            test_dir_path=tmp_path,
            include_list=None,
            exclude_list=["test_only"],
        )

'''
# --- test_14_exclude_list_is_applied_after_include_list() ---------------------
def test_14_exclude_list_is_applied_after_include_list(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "group" / "test_keep.py")
    _write(tmp_path / "group" / "test_remove.py")
    _write(tmp_path / "other" / "test_other.py")

    result = _resolve_test_file_paths(
        test_dir_path=tmp_path,
        include_list=["group"],
        exclude_list=["group/test_remove"],
    )

    assert result == [Path("group/test_keep.py")]

'''

# === Internal helpers ========================================================

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
