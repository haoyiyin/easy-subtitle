"""Aligner: fix Whisper segments by aligning with an original-spoken-text script.

When a user provides the original script that was read aloud (原口播文本),
this module aligns each Whisper segment to the best-matching span in the
original text and replaces the transcribed text with the correct original.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from easy_subtitle.srt_writer import Segment


def _normalize(text: str) -> str:
    """Normalize text for comparison: collapse whitespace, lowercase."""
    text = text.strip()
    # Collapse all whitespace (newlines, spaces, tabs) into single spaces
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _find_best_match(
    needle: str,
    haystack: str,
    haystack_offset: int,
) -> tuple[int, int] | None:
    """Find the best-matching span of needle within haystack.

    Uses difflib to find the longest contiguous match, then expands
    to include nearby matching characters.

    Returns (global_position, length) or None if no good match found.
    """
    if not needle.strip() or not haystack.strip():
        return None

    needle_norm = _normalize(needle)
    haystack_norm = _normalize(haystack)

    # First try: exact match
    idx = haystack_norm.find(needle_norm)
    if idx >= 0:
        # Map normalized index back to original text position
        return _map_norm_to_orig(haystack, idx, len(needle_norm))

    # Second try: find longest matching substring
    matcher = difflib.SequenceMatcher(None, haystack_norm, needle_norm)
    match = matcher.find_longest_match(0, len(haystack_norm), 0, len(needle_norm))

    if match.size < max(3, len(needle_norm) * 0.3):
        return None

    return _map_norm_to_orig(haystack, match.a, match.size)


def _map_norm_to_orig(original: str, norm_idx: int, norm_len: int) -> tuple[int, int]:
    """Map a normalized-text span back to original text positions.

    Normalization collapses whitespace, so we walk the original text
    and track which characters contribute to the normalized version.
    """
    orig_pos = 0
    norm_pos = 0
    start_in_orig = 0

    while orig_pos < len(original) and norm_pos < norm_idx:
        if not original[orig_pos].isspace() or (
            orig_pos > 0 and not original[orig_pos - 1].isspace()
        ):
            # This is tricky: normalization uses re.sub(r"\s+", " ", ...)
            # which collapses runs of whitespace into a single space.
            # For simplicity, we approximate: skip whitespace runs.
            pass
        if original[orig_pos].isspace():
            # Count as one space char in normalized text
            norm_pos += 1
            # Skip the rest of the whitespace run
            while orig_pos < len(original) and original[orig_pos].isspace():
                orig_pos += 1
            if norm_pos == norm_idx:
                start_in_orig = orig_pos
                break
        else:
            norm_pos += 1
            orig_pos += 1
    else:
        start_in_orig = orig_pos

    # Now find end position for norm_len chars
    end_in_orig = start_in_orig
    norm_count = 0
    while end_in_orig < len(original) and norm_count < norm_len:
        if original[end_in_orig].isspace():
            norm_count += 1
            end_in_orig += 1
            while end_in_orig < len(original) and original[end_in_orig].isspace():
                end_in_orig += 1
        else:
            norm_count += 1
            end_in_orig += 1

    return start_in_orig, end_in_orig - start_in_orig


def align_segments(
    whisper_segments: list[Segment],
    original_text: str,
    *,
    min_match_ratio: float = 0.3,
    search_window_chars: int = 300,
) -> list[Segment]:
    """Align Whisper segments with original spoken text, replacing transcriptions.

    Uses a greedy sliding-window approach:
    1. For each segment, search a window around the expected position in the
       original text for the best match.
    2. If a good match is found, replace the segment text with the
       corresponding original text.
    3. Track position monotonically to maintain order.

    Args:
        whisper_segments: Segments from Whisper transcription.
        original_text: The original script text (will be normalized internally).
        min_match_ratio: Minimum ratio of matched chars to segment length.
        search_window_chars: Characters to search before/after expected position.

    Returns:
        A new list of Segments with texts replaced from original_text where matched.
    """
    orig = original_text
    pos = 0  # current position in original_text

    aligned: list[Segment] = []

    for seg in whisper_segments:
        seg_text = seg.text.strip()
        if not seg_text:
            # Keep empty segments as-is
            aligned.append(seg)
            continue

        # Search window around expected position
        win_start = max(0, pos - search_window_chars)
        win_end = min(len(orig), pos + len(seg_text) + search_window_chars)
        window = orig[win_start:win_end]

        if not window.strip():
            # No more original text to match against
            aligned.append(seg)
            continue

        result = _find_best_match(seg_text, window, win_start)
        if result is None:
            # No good match found; keep original Whisper text
            aligned.append(seg)
            pos = min(pos + len(seg_text), len(orig))
            continue

        match_start, match_len = result
        matched_text = orig[match_start : match_start + match_len].strip()

        if matched_text:
            aligned.append(
                Segment(
                    index=seg.index,
                    start=seg.start,
                    end=seg.end,
                    text=matched_text,
                )
            )
            pos = match_start + match_len
        else:
            aligned.append(seg)
            pos = min(pos + len(seg_text), len(orig))

    return aligned


def load_original_text(path: str | Path) -> str:
    """Load the original spoken text from a file. Supports .txt and .md files."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Original text file not found: {path}")
    return path.read_text(encoding="utf-8")
