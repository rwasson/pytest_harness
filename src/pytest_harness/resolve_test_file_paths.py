"""
resolve_test_file_paths.py

Last edited: 2026-08-05
"""

from pathlib import Path


# --- _resolve_test_file_paths() -----------------------------------------------
def _resolve_test_file_paths(
    *,
    test_file_dir_path: Path,
    include_list: list[str | Path] | None,
    exclude_list: list[str | Path] | None,
) -> list[Path]:
    """
    Return selected pytest test-file paths relative to test_file_dir_path.
    """

    test_file_dir_path = test_file_dir_path.resolve()

    if not test_file_dir_path.exists():
        raise RuntimeError(
            "Test directory does not exist:\n"
            f"    {test_file_dir_path}"
        )

    if not test_file_dir_path.is_dir():
        raise RuntimeError(
            "Test directory path is not a directory:\n"
            f"    {test_file_dir_path}"
        )

    if include_list is None:
        resolved_paths = _discover_test_files(test_file_dir_path)
    else:
        resolved_paths = []

        for entry in include_list:
            resolved_paths.extend(
                _resolve_selector(
                    entrypath=entry,
                    list_name="include_list",
                    test_file_dir_path=test_file_dir_path,
                )
            )

    resolved_paths = sorted(set(resolved_paths))

    if exclude_list is not None:
        excluded_paths: set[Path] = set()

        for entry in exclude_list:
            excluded_paths.update(
                _resolve_selector(
                    entrypath=entry,
                    list_name="exclude_list",
                    test_file_dir_path=test_file_dir_path,
                )
            )

        resolved_paths = [
            path
            for path in resolved_paths
            if path not in excluded_paths
        ]

    if not resolved_paths:
        raise RuntimeError(
            "No pytest test files selected.\n\n"
            f"Test directory:\n"
            f"    {test_file_dir_path}\n\n"
            f"include_list:\n"
            f"    {include_list}\n\n"
            f"exclude_list:\n"
            f"    {exclude_list}"
        )

    return [
        path.relative_to(test_file_dir_path)
        for path in resolved_paths
    ]


# === Internal helpers =========================================================

def _resolve_selector(
    *,
    entrypath: str | Path,
    list_name: str,
    test_file_dir_path: Path,
) -> list[Path]:
    entry_path = _resolve_selector_path(
        entrypath=entrypath,
        list_name=list_name,
        test_file_dir_path=test_file_dir_path,
    )

    if entry_path.suffix.lower() == ".py":
        return [
            _require_valid_test_file(
                path=entry_path,
                entrypath=entrypath,
                list_name=list_name,
            )
        ]

    file_candidate = entry_path.with_suffix(".py")
    dir_candidate = entry_path

    file_exists = file_candidate.is_file()
    dir_exists = dir_candidate.is_dir()

    if file_exists and not dir_exists:
        return [
            _require_valid_test_file(
                path=file_candidate,
                entrypath=entrypath,
                list_name=list_name,
            )
        ]

    if dir_exists and not file_exists:
        return _discover_test_files(dir_candidate)

    if file_exists and dir_exists:
        print(
            "WARNING: Ambiguous pytest_harness selector.\n"
            f"Both a file and directory match: {entrypath}\n"
            f"Using directory:\n"
            f"    {dir_candidate.relative_to(test_file_dir_path)}\n"
            f"Use this to select the file explicitly:\n"
            f"    {file_candidate.relative_to(test_file_dir_path)}"
        )

        return _discover_test_files(dir_candidate)

    raise RuntimeError(
        f"Unrecognized test selector in {list_name}:\n"
        f"    {entrypath}\n\n"
        f"Expected one of:\n"
        f"    {file_candidate}\n"
        f"    {dir_candidate}/"
    )


def _resolve_selector_path(
    *,
    entrypath: str | Path,
    list_name: str,
    test_file_dir_path: Path,
) -> Path:
    entry_path = Path(entrypath)

    if entry_path.is_absolute():
        resolved_path = entry_path.resolve()
    else:
        resolved_path = (
            test_file_dir_path / entry_path
        ).resolve()

    return _require_path_inside_test_directory(
        path=resolved_path,
        entrypath=entrypath,
        test_dir_path=test_file_dir_path,
        list_name=list_name,
    )


def _discover_test_files(
    directory_path: Path,
) -> list[Path]:
    return sorted(
        path.resolve()
        for path in directory_path.rglob("test_*.py")
        if path.is_file()
    )


def _require_valid_test_file(
    *,
    path: Path,
    entrypath: str | Path,
    list_name: str,
) -> Path:
    if not path.exists():
        raise RuntimeError(
            f"Unrecognized test file in {list_name}:\n"
            f"    {entrypath}\n\n"
            f"Expected file:\n"
            f"    {path}"
        )

    if not path.is_file():
        raise RuntimeError(
            f"Entry in {list_name} is not a file:\n"
            f"    {path}"
        )

    if path.suffix.lower() != ".py":
        raise RuntimeError(
            f"Test file in {list_name} must have a .py suffix:\n"
            f"    {path}"
        )

    if not path.name.startswith("test_"):
        raise RuntimeError(
            f"Test file in {list_name} must start with 'test_':\n"
            f"    {path}"
        )

    return path


def _require_path_inside_test_directory(
    *,
    path: Path,
    test_dir_path: Path,
    entrypath: str | Path,
    list_name: str,
) -> Path:
    try:
        path.relative_to(test_dir_path)
    except ValueError as exc:
        raise RuntimeError(
            f"Entry in {list_name} is outside the test directory:\n"
            f"    {entrypath}\n\n"
            f"Resolved path:\n"
            f"    {path}\n\n"
            f"Test directory:\n"
            f"    {test_dir_path}"
        ) from exc

    return path

