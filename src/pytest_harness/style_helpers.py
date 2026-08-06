"""
style_helpers.py

Last edited: 2026-7-20
"""

from collections.abc import Mapping
from dataclasses import dataclass

from rich.markup import escape


@dataclass(frozen=True, slots=True)
class _SummaryStyles:
    header: str
    divider: str
    title: str
    file_name: str
    success: str
    problem: str
    warning: str
    muted: str
    text: str


def _build_summary_styles(
    theme: Mapping[str, str],
) -> _SummaryStyles:
    return _SummaryStyles(
        title=theme["title"],
        header=theme["title"],
        divider=theme["divider"],
        file_name="",  # filenames use normal console text
        success=theme["success"],
        problem=theme["critical"],
        warning=theme["warning"],
        muted=theme["muted"],
        text=theme["text"],
    )


def _styled(
    text: str,
    *,
    style: str,
) -> str:
    """
    Apply Rich markup styling to trusted internal text.

    Dynamic user or filesystem values must be escaped before being passed.
    """
    if not style:
        return text
    return f"[{style}]{text}[/{style}]"


def _build_section_heading(
    heading: str,
    *,
    divider: str,
    styles: _SummaryStyles,
) -> list[str]:
    return [
        _styled(heading, style=styles.header),
        _styled(divider, style=styles.divider),
    ]


def _styled_field(
    value: object,
    *,
    style: str,
) -> str:
    text = escape(str(value))
    if not style:
        return text

    return f"[{style}]{text}[/{style}]"
