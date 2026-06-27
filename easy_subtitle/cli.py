"""Command-line interface for easy-subtitle."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from easy_subtitle import __version__
from easy_subtitle.aligner import align_segments, load_original_text
from easy_subtitle.srt_writer import write_srt
from easy_subtitle.transcriber import transcribe

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `easy-subtitle` command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"easy-subtitle v{__version__}")
        return 0

    _setup_logging(args.verbose)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else input_path.with_suffix(".srt")

    try:
        logger.info("Transcribing %s …", input_path.name)

        segments, detected_lang = transcribe(
            input_path,
            model_size=args.model,
            language=args.language or None,
            device=args.device,
            compute_type=args.compute_type,
            beam_size=args.beam_size,
            vad_filter=not args.no_vad,
            vad_min_silence_duration_ms=args.vad_min_silence,
        )

        logger.info(
            "Detected language: %s | %d segments",
            detected_lang,
            len(segments),
        )

        if args.original_text:
            logger.info("Aligning with original text: %s", args.original_text)
            original = load_original_text(args.original_text)
            segments = align_segments(
                segments,
                original,
                min_match_ratio=args.min_match_ratio,
                search_window_chars=args.search_window,
            )
            logger.info("Alignment complete — %d segments", len(segments))

        write_srt(segments, output_path)
        logger.info("SRT written to: %s", output_path)
        print(f"✓ SRT saved to: {output_path}")

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        prog="easy-subtitle",
        description="Offline audio/video to SRT subtitle converter using faster-whisper.",
    )

    p.add_argument(
        "-i",
        "--input",
        required=True,
        help="Path to audio or video file.",
    )
    p.add_argument(
        "-o",
        "--output",
        help="Output SRT path (default: same name as input with .srt extension).",
    )
    p.add_argument(
        "-m",
        "--model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size (default: medium).",
    )
    p.add_argument(
        "-l",
        "--language",
        default=None,
        help="Language code hint (e.g. zh, en, ja). Auto-detected if omitted.",
    )
    p.add_argument(
        "--original-text",
        help="Path to original spoken-text script for subtitle correction.",
    )
    p.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Compute device (default: auto).",
    )
    p.add_argument(
        "--compute-type",
        default="auto",
        choices=["auto", "float16", "int8", "int8_float16", "int8_bfloat16"],
        help="Quantization type (default: auto).",
    )
    p.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding (default: 5).",
    )
    p.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable voice activity detection.",
    )
    p.add_argument(
        "--vad-min-silence",
        type=int,
        default=500,
        help="Minimum silence duration for VAD split (ms, default: 500).",
    )
    p.add_argument(
        "--min-match-ratio",
        type=float,
        default=0.3,
        help="Minimum match ratio for original-text alignment (default: 0.3).",
    )
    p.add_argument(
        "--search-window",
        type=int,
        default=300,
        help="Search window size in chars for alignment (default: 300).",
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit.",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v, -vv).",
    )

    return p


def _setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level."""
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(message)s",
    )
