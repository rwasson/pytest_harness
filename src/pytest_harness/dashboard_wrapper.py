"""
dashboard_wrapper.py

Last edited: 2026-08-10
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MIN_WRAP_WIDTH = 3

@dataclass
class WrappedLine:
    """
    Represents one wrapped line segment.
    Attributes:
        start:
            Start index in original string (inclusive).

        end:
            End index in original string (exclusive).

        text:
            Wrapped line text with ANSI sequences preserved.

    """
    start: int
    end: int
    text: str


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# --- _wrap_dashboard_text() ---------------------------------------------------
def _wrap_dashboard_text(
    text: str,
    *,
    dashboard_width: int,
    indent: int,
) -> str:
    wrapped_lines = wrap_text(
        text,
        width=dashboard_width - indent,
        continuation_width=dashboard_width - indent,
        hanging_indent=4,
    )

    prefix = " " * indent
    return "\n".join(
        prefix + line
        for line in wrapped_lines
    )


# === Internal helpers =========================================================

# --- wrap_text() -------------------------------------------------------------
def wrap_text(
    text: str,
    *,
    width: int,
    continuation_width: int | None = None,
    hanging_indent: int | None = None,
) -> list[str]:
    """
    Wrap a single-line string with different widths for first and continuation lines.

    Args:
        text:
            Single-line text to wrap.
        width:
            Maximum width of the first line.
        continuation_width:
            Optional maximum width of continuation lines,
            including any hanging indent.
            If None, uses first-line width.
        hanging_indent:
            Optional number of indent spaces for continuation lines.

    Raises:
        ValueError:
            If text contains newline characters.

    Returns:
        Wrapped lines as a list of strings.
    """
    if "\n" in text:
        raise ValueError("wrap_text expects a single-line string (no '\\n')")

    if width < _MIN_WRAP_WIDTH:
        raise ValueError(f"wrap_text expects a width >= {_MIN_WRAP_WIDTH}")

    if continuation_width is not None and continuation_width < _MIN_WRAP_WIDTH:
        raise ValueError(f"wrap_text expects a continuation width >= {_MIN_WRAP_WIDTH}")

    continuation_wrap_width = continuation_width if continuation_width is not None else width

    if hanging_indent is not None and hanging_indent >= continuation_wrap_width - _MIN_WRAP_WIDTH:
        raise ValueError(
            f"Invalid hanging_indent={hanging_indent}. "
            "Must leave at least 10 characters of continuation width."
        )

    # --- first line ---
    wrapped = _wrap_text_with_ansi(text, width)
    if not wrapped:
        return [""]

    first = wrapped[0]
    remaining = text[first.end :]

    if not remaining:
        return [first.text]

    # --- continuation lines ---
    if hanging_indent is not None and hanging_indent > 0:
        continuation_wrap_width = continuation_wrap_width - hanging_indent - 1

    continuation = _wrap_text_with_ansi(remaining, continuation_wrap_width)
    continuation_lines = [w.text for w in continuation]

    if hanging_indent is not None and hanging_indent > 0:
        prefix = " " * hanging_indent
        continuation_lines = [prefix + line for line in continuation_lines]

    return [first.text, *continuation_lines]

# --- strip_ansi() -------------------------------------------------------------
def strip_ansi(s: str) -> str:
    """
    Remove ANSI escape sequences from a string.
    Used for accurate visible-length calculations.
    """
    return _ANSI_RE.sub("", s)



# --- _wrap_text_with_ansi() ---------------------------------------------------
def _wrap_text_with_ansi(
    text: str,
    width: int,
    break_chars: tuple[str, ...] = ("/", "_", "-", " ", ".", "|"),
) -> list[WrappedLine]:
    """
    Wrap a single-line string to a given width using natural breakpoints.
    - Prefers breaking at characters in `break_chars`
    - Falls back to hard wrap when needed
    - ANSI sequences are preserved in output, later when:
        - emit to console: ANSI used for console styling
             (do not appear as characters on console)
        - emit to log files: ANSI stripped prior to logging
    - ANSI sequences are preserved in output and excluded from visible-width calculations.

    Returns:
        list[WrappedLine]
    """
    if not text:
        return []

    if len(strip_ansi(text)) <= width:
        wrapped = WrappedLine(start=0, end=len(text), text=text)
        assert text[wrapped.start: wrapped.end] == wrapped.text
        return [wrapped]

    out_lines: list[WrappedLine] = []

    character_position_index = 0
    # position in the original string of the next character being processed

    line_item_list = []
    # list of items (individual characters or blocks of ANSI code)
    # in current line under construction - used in loops

    item_start_positions = []
    item_end_positions = []
    # Raw-string start/end positions for each item in line_item_list.
    # Text characters occupy one raw position; ANSI blocks occupy multiple.

    visible_line_len = 0
    # length of current line (excluding ANSI)

    last_safe_break_count = None
    # number of items from the start of the current line where it is safe to split

    segment_pairs = _split_ansi_segments(text)

    for segment_text, segment_is_ansi in segment_pairs:

        if segment_is_ansi:
            line_item_list.append((segment_text, True))
            item_start_positions.append(character_position_index)

            character_position_index += len(segment_text)

            item_end_positions.append(character_position_index - 1)
            continue

        for char in segment_text:

            line_item_list.append((char, False))
            item_start_positions.append(character_position_index)
            item_end_positions.append(character_position_index)

            character_position_index += 1
            visible_line_len += 1

            if char in break_chars and visible_line_len <= width:
                last_safe_break_count = len(line_item_list)

            if visible_line_len > width:

                (
                    line_item_list,
                    item_start_positions,
                    item_end_positions,
                    visible_line_len,
                    last_safe_break_count,
                ) = _wrap_current_line(
                    text=text,
                    width=width,
                    out_lines=out_lines,
                    line_item_list=line_item_list,
                    item_start_positions=item_start_positions,
                    item_end_positions=item_end_positions,
                    last_safe_break_count=last_safe_break_count,
                )

    # Output any remaining text that did not trigger a wrap (final line)
    if line_item_list:
        text_out = "".join(txt for txt, _ in line_item_list)

        start = item_start_positions[0]
        end = item_end_positions[-1] + 1

        assert text[start:end] == text_out

        out_lines.append(
            WrappedLine(start, end, text_out)
        )

    return out_lines

# --- _split_ansi_segments() ---------------------------------------------------
def _split_ansi_segments(
    text: str,
) -> list[tuple[str, bool]]:
    """
    Convert text into (segment_text, segment_is_ansi) pairs.

    Example:
        "hi \\x1b[31mERROR\\x1b[0m occurred"

    becomes:

        [
            ("hi ", False),
            ("\\x1b[31m", True),
            ("ERROR", False),
            ("\\x1b[0m", True),
            (" occurred", False),
        ]
    """
    segment_pairs = []
    segment_pos = 0

    for ansi_block in _ANSI_RE.finditer(text):

        if ansi_block.start() > segment_pos:
            segment_pairs.append(
                (text[segment_pos: ansi_block.start()], False)
            )

        segment_pairs.append(
            (ansi_block.group(0), True)
        )

        segment_pos = ansi_block.end()

    if segment_pos < len(text):
        segment_pairs.append(
            (text[segment_pos:], False)
        )

    return segment_pairs


# --- _wrap_current_line() -----------------------------------------------------
def _wrap_current_line(
    *,
    text: str,
    width: int,
    out_lines: list[WrappedLine],
    line_item_list: list[tuple[str, bool]],
    item_start_positions: list[int],
    item_end_positions: list[int],
    last_safe_break_count: int | None,
) -> tuple[
    list[tuple[str, bool]],
    list[int],
    list[int],
    int,
    int | None,
]:
    """
    Emit one wrapped line and return the remaining working buffers.
    """

    if last_safe_break_count is not None:
        cut_index = last_safe_break_count
    else:
        cum_len = 0
        cut_index = 0

        for idx, (item_text, item_is_ansi) in enumerate(line_item_list):

            if item_is_ansi:
                continue

            cum_len += len(item_text)
            cut_index = idx + 1

            if cum_len >= width:
                break

    text_out = "".join(
        txt
        for txt, _ in line_item_list[:cut_index]
    )

    start = item_start_positions[0]
    end = item_end_positions[cut_index - 1] + 1

    assert text[start:end] == text_out

    out_lines.append(
        WrappedLine(start, end, text_out)
    )

    line_item_list = line_item_list[cut_index:]
    item_start_positions = item_start_positions[cut_index:]
    item_end_positions = item_end_positions[cut_index:]

    visible_line_len = sum(
        len(txt)
        for txt, is_ansi in line_item_list
        if not is_ansi
    )

    # Trim leading space
    if (
        line_item_list
        and not line_item_list[0][1]
        and line_item_list[0][0].startswith(" ")
    ):
        trim_len = (
            len(line_item_list[0][0])
            - len(line_item_list[0][0].lstrip(" "))
        )

        line_item_list[0] = (
            line_item_list[0][0].lstrip(" "),
            False,
        )

        item_start_positions[0] += trim_len

    last_safe_break_count = None

    return (
        line_item_list,
        item_start_positions,
        item_end_positions,
        visible_line_len,
        last_safe_break_count,
    )


