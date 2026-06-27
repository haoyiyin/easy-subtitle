"""SRT subtitle file writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    """A single subtitle segment with timing and text."""

    index: int
    start: float  # seconds
    end: float  # seconds
    text: str


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    try:
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise ValueError(f"Invalid timestamp: {seconds!r}")
        seconds = float(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    except Exception as e:
        raise ValueError(f"Failed to format timestamp {seconds!r}: {e}") from e


def segments_to_srt(segments: list[Segment]) -> str:
    """Convert a list of Segments to an SRT-formatted string."""
    blocks: list[str] = []
    for seg in segments:
        block = (
            f"{seg.index}\n"
            f"{_format_timestamp(seg.start)} --> {_format_timestamp(seg.end)}\n"
            f"{seg.text.strip()}\n"
        )
        blocks.append(block)
    return "\n".join(blocks)


def write_srt(segments: list[Segment], output_path: str | Path) -> None:
    """Write segments to an SRT file. Creates parent directories if needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = segments_to_srt(segments)
    output_path.write_text(content, encoding="utf-8")
