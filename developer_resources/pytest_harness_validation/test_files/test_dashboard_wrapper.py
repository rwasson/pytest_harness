"""
test_dashboard_wrapper.py

Tests for dashboard text wrapping, including ANSI-aware visible widths,
natural breakpoints, hanging indentation, and source-position tracking.

Last edited: 2026-08-08
"""

from __future__ import annotations

import pytest

import pytest_harness.dashboard_wrapper as module
from pytest_harness.dashboard_wrapper import WrappedLine

# === Tests ===================================================================

# --- test_01_strip_ansi_removes_color_sequences() -----------------------------
def test_01_strip_ansi_removes_color_sequences() -> None:
    text = (
        "\x1b[31mERROR\x1b[0m "
        "\x1b[1;33mWARNING\x1b[0m"
    )

    assert module.strip_ansi(text) == "ERROR WARNING"


# --- test_02_split_ansi_segments_preserves_text_and_codes() -------------------
def test_02_split_ansi_segments_preserves_text_and_codes() -> None:
    text = "before \x1b[31mERROR\x1b[0m after"

    segments = module._split_ansi_segments(text)

    assert segments == [
        ("before ", False),
        ("\x1b[31m", True),
        ("ERROR", False),
        ("\x1b[0m", True),
        (" after", False),
    ]

    assert "".join(
        segment
        for segment, _ in segments
    ) == text


# --- test_03_split_ansi_segments_handles_plain_text() -------------------------
def test_03_split_ansi_segments_handles_plain_text() -> None:
    assert module._split_ansi_segments(
        "plain text"
    ) == [
        ("plain text", False),
    ]


# --- test_04_wrap_text_returns_empty_line_for_empty_string() ------------------
def test_04_wrap_text_returns_empty_line_for_empty_string() -> None:
    assert module.wrap_text(
        "",
        width=20,
    ) == [""]


# --- test_05_wrap_text_leaves_short_text_unchanged() --------------------------
def test_05_wrap_text_leaves_short_text_unchanged() -> None:
    text = "short text"

    assert module.wrap_text(
        text,
        width=20,
    ) == [text]


# --- test_06_wrap_text_rejects_multiline_input() ------------------------------
def test_06_wrap_text_rejects_multiline_input() -> None:
    with pytest.raises(
        ValueError,
        match="single-line",
    ):
        module.wrap_text(
            "first\nsecond",
            width=20,
        )


# --- test_07_wrap_text_rejects_too_small_first_width() ------------------------
def test_07_wrap_text_rejects_too_small_first_width() -> None:
    with pytest.raises(
        ValueError,
        match="width",
    ):
        module.wrap_text(
            "abcdef",
            width=2,
        )


# --- test_08_wrap_text_rejects_too_small_continuation_width() -----------------
def test_08_wrap_text_rejects_too_small_continuation_width() -> None:
    with pytest.raises(
        ValueError,
        match="continuation width",
    ):
        module.wrap_text(
            "abcdef",
            width=10,
            continuation_width=2,
        )


# --- test_09_wrap_text_rejects_excessive_hanging_indent() --------------------
def test_09_wrap_text_rejects_excessive_hanging_indent() -> None:
    with pytest.raises(
        ValueError,
        match="hanging_indent",
    ):
        module.wrap_text(
            "abcdefghijklmnopqrstuvwxyz",
            width=10,
            continuation_width=10,
            hanging_indent=7,
        )


# --- test_10_wrap_text_hard_wraps_long_unbroken_text() ------------------------
def test_10_wrap_text_hard_wraps_long_unbroken_text() -> None:
    lines = module.wrap_text(
        "abcdefghij",
        width=4,
    )

    assert lines == [
        "abcd",
        "efgh",
        "ij",
    ]

    assert "".join(lines) == "abcdefghij"


# --- test_11_wrap_text_uses_natural_breakpoints() -----------------------------
def test_11_wrap_text_uses_natural_breakpoints() -> None:
    text = "alpha/beta/gamma/delta"

    lines = module.wrap_text(
        text,
        width=10,
    )

    assert len(lines) > 1

    assert all(
        len(module.strip_ansi(line)) <= 10
        for line in lines
    )

    assert "".join(lines) == text


# --- test_12_wrap_text_uses_requested_continuation_width() --------------------
def test_12_wrap_text_uses_requested_continuation_width() -> None:
    lines = module.wrap_text(
        "abcdefghijklmnopqrstuv",
        width=8,
        continuation_width=6,
    )

    assert len(lines[0]) <= 8

    assert all(
        len(module.strip_ansi(line)) <= 6
        for line in lines[1:]
    )


# --- test_13_wrap_text_applies_hanging_indent() -------------------------------
def test_13_wrap_text_applies_hanging_indent() -> None:
    lines = module.wrap_text(
        "abcdefghijklmnopqrstuvwxyz",
        width=8,
        continuation_width=10,
        hanging_indent=3,
    )

    assert len(lines) > 1
    assert not lines[0].startswith("   ")

    assert all(
        line.startswith("   ")
        for line in lines[1:]
    )

    assert all(
        len(module.strip_ansi(line)) <= 10
        for line in lines[1:]
    )


# --- test_14_wrap_text_preserves_ansi_sequences() -----------------------------
def test_14_wrap_text_preserves_ansi_sequences() -> None:
    text = (
        "\x1b[31m"
        "abcdefghijkl"
        "\x1b[0m"
    )

    lines = module.wrap_text(
        text,
        width=5,
    )

    combined = "".join(lines)

    assert "\x1b[31m" in combined
    assert "\x1b[0m" in combined

    assert module.strip_ansi(combined) == "abcdefghijkl"

    assert all(
        len(module.strip_ansi(line)) <= 5
        for line in lines
    )


# --- test_15_wrap_with_ansi_returns_source_positions() ------------------------
def test_15_wrap_with_ansi_returns_source_positions() -> None:
    text = "abcdefghij"

    wrapped = module._wrap_text_with_ansi(
        text,
        width=4,
    )

    assert wrapped == [
        WrappedLine(
            start=0,
            end=4,
            text="abcd",
        ),
        WrappedLine(
            start=4,
            end=8,
            text="efgh",
        ),
        WrappedLine(
            start=8,
            end=10,
            text="ij",
        ),
    ]

    for line in wrapped:
        assert text[line.start:line.end] == line.text


# --- test_16_wrap_with_ansi_short_text_returns_single_record() ----------------
def test_16_wrap_with_ansi_short_text_returns_single_record() -> None:
    text = "\x1b[32mOK\x1b[0m"

    wrapped = module._wrap_text_with_ansi(
        text,
        width=5,
    )

    assert wrapped == [
        WrappedLine(
            start=0,
            end=len(text),
            text=text,
        ),
    ]


# --- test_17_wrap_with_ansi_empty_text_returns_no_records() -------------------
def test_17_wrap_with_ansi_empty_text_returns_no_records() -> None:
    assert module._wrap_text_with_ansi(
        "",
        width=10,
    ) == []


# --- test_18_custom_break_char_is_respected() ---------------------------------
def test_18_custom_break_char_is_respected() -> None:
    text = "abc:def:ghi"

    wrapped = module._wrap_text_with_ansi(
        text,
        width=5,
        break_chars=(":",),
    )

    assert len(wrapped) > 1

    assert all(
        len(module.strip_ansi(line.text)) <= 5
        for line in wrapped
    )

    assert "".join(
        line.text
        for line in wrapped
    ) == text


# --- test_19_dashboard_wrapper_adds_outer_indent() ----------------------------
def test_19_dashboard_wrapper_adds_outer_indent() -> None:
    text = module._wrap_dashboard_text(
        "short text",
        dashboard_width=40,
        indent=4,
    )

    assert text == "    short text"


# --- test_20_dashboard_wrapper_wraps_with_continuation_indent() ---------------
def test_20_dashboard_wrapper_wraps_with_continuation_indent() -> None:
    text = module._wrap_dashboard_text(
        "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz",
        dashboard_width=20,
        indent=4,
    )

    lines = text.splitlines()

    assert len(lines) > 1

    # Every dashboard line receives the requested outer indent.
    assert all(
        line.startswith("    ")
        for line in lines
    )

    # wrap_text() additionally gives continuation lines its hanging indent.
    assert all(
        line.startswith("        ")
        for line in lines[1:]
    )

    assert all(
        len(module.strip_ansi(line)) <= 20
        for line in lines
    )


# --- test_21_wrapped_line_is_mutable_record() ---------------------------------
def test_21_wrapped_line_is_mutable_record() -> None:
    record = WrappedLine(
        start=1,
        end=4,
        text="abc",
    )

    record.text = "xyz"

    assert record.start == 1
    assert record.end == 4
    assert record.text == "xyz"
