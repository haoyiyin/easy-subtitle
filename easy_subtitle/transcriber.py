"""Transcriber: audio/video → segments via faster-whisper."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from easy_subtitle.srt_writer import Segment

# Supported audio/video extensions for direct Whisper input
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"}
# Extensions that need ffmpeg extraction
_VIDEO_EXTS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
    ".3gp",
    ".ogv",
}

# Languages where faster-whisper's auto-detect may be unreliable;
# providing a hint improves accuracy for short clips.
_LANG_HINT_MAP: dict[str, str] = {
    "zh": "zh",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "pt": "pt",
    "ru": "ru",
    "ar": "ar",
    "hi": "hi",
    "it": "it",
    "nl": "nl",
    "pl": "pl",
    "tr": "tr",
    "vi": "vi",
    "th": "th",
    "id": "id",
    "ms": "ms",
    "uk": "uk",
    "sv": "sv",
    "da": "da",
    "fi": "fi",
    "no": "no",
    "cs": "cs",
    "ro": "ro",
    "hu": "hu",
    "el": "el",
    "bg": "bg",
    "he": "he",
    "fa": "fa",
    "ur": "ur",
    "bn": "bn",
    "ta": "ta",
    "te": "te",
    "mr": "mr",
    "gu": "gu",
    "kn": "kn",
    "ml": "ml",
    "pa": "pa",
    "sw": "sw",
    "yo": "yo",
    "ha": "ha",
    "am": "am",
    "my": "my",
    "km": "km",
    "lo": "lo",
    "si": "si",
    "ne": "ne",
    "ps": "ps",
    "ku": "ku",
    "sd": "sd",
    "bo": "bo",
    "ug": "ug",
    "mn": "mn",
    "kk": "kk",
    "uz": "uz",
    "az": "az",
    "hy": "hy",
    "ka": "ka",
    "et": "et",
    "lv": "lv",
    "lt": "lt",
    "sk": "sl",
    "sl": "sl",
    "hr": "hr",
    "sr": "sr",
    "mk": "mk",
    "sq": "sq",
    "is": "is",
    "mt": "mt",
    "ga": "ga",
    "cy": "cy",
    "br": "br",
    "eu": "eu",
    "gl": "gl",
    "ca": "ca",
    "oc": "oc",
    "tl": "tl",
    "jw": "jw",
    "su": "su",
    "mg": "mg",
    "so": "so",
    "ln": "ln",
    "sn": "sn",
    "zu": "zu",
    "xh": "xh",
    "st": "st",
    "tn": "tn",
    "ny": "ny",
    "ig": "ig",
}


def _extract_audio(video_path: str | Path, output_dir: str | None = None) -> str:
    """Extract audio track from video file to a 16kHz mono WAV for Whisper.

    Returns path to the extracted audio file.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Input file not found: {video_path}")

    output_dir = output_dir or tempfile.mkdtemp(prefix="easy_subtitle_")
    audio_path = os.path.join(output_dir, f"{video_path.stem}_extracted.wav")

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vn",  # drop video
        "-acodec",
        "pcm_s16le",  # 16-bit PCM
        "-ar",
        "16000",  # 16kHz sample rate
        "-ac",
        "1",  # mono
        "-y",  # overwrite
        str(audio_path),
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg failed to extract audio from {video_path}:\n{exc.stderr}"
        ) from exc
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg is not installed. Install it with: brew install ffmpeg"
        ) from None

    return audio_path


def _is_video(path: str | Path) -> bool:
    """Check if a file is a video (needs audio extraction) or direct audio."""
    ext = Path(path).suffix.lower()
    if ext in _VIDEO_EXTS:
        return True
    if ext in _AUDIO_EXTS:
        return False
    # Unknown extension: try as audio first, fall back to extraction
    return False


def _needs_extraction(path: str | Path) -> bool:
    """Determine if the file needs audio extraction via ffmpeg."""
    return _is_video(path)


def transcribe(
    input_path: str | Path,
    *,
    model_size: str = "medium",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
    beam_size: int = 5,
    vad_filter: bool = True,
    vad_min_silence_duration_ms: int = 500,
    output_dir: str | None = None,
) -> tuple[list[Segment], str]:
    """Transcribe an audio or video file and return segments with detected language.

    Args:
        input_path: Path to audio or video file.
        model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3).
        language: Language code hint or None for auto-detection.
        device: "auto", "cpu", or "cuda".
        compute_type: "auto", "float16", "int8", "int8_float16", etc.
        beam_size: Beam search size (higher = more accurate but slower).
        vad_filter: Enable voice activity detection to skip silence.
        vad_min_silence_duration_ms: Minimum silence to split on (ms).
        output_dir: Temp directory for extracted audio. Auto-cleaned if None.

    Returns:
        (list of Segment, detected_language_code)

    Raises:
        FileNotFoundError: If input file does not exist.
        RuntimeError: If ffmpeg or model download fails.
    """
    input_path = Path(input_path)
    cleanup_audio = False
    audio_file: str = ""

    try:
        if _needs_extraction(input_path):
            audio_file = _extract_audio(input_path, output_dir)
            if output_dir is None:
                cleanup_audio = True
        else:
            audio_file = str(input_path)

        # Load model
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

        # Run transcription
        segments_iter, info = model.transcribe(
            str(audio_file),
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            vad_parameters={
                "min_silence_duration_ms": vad_min_silence_duration_ms,
            },
        )

        detected_lang = info.language

        segments: list[Segment] = []
        index = 0

        for seg in segments_iter:
            text = seg.text.strip()
            if not text:
                continue
            index += 1
            segments.append(
                Segment(
                    index=index,
                    start=seg.start,
                    end=seg.end,
                    text=text,
                )
            )

        # Normalize language code
        if detected_lang and detected_lang not in _LANG_HINT_MAP:
            for key in _LANG_HINT_MAP:
                if detected_lang.startswith(key):
                    detected_lang = key
                    break

        return segments, detected_lang

    finally:
        if cleanup_audio and audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                tmpdir = os.path.dirname(audio_file)
                if tmpdir.startswith(tempfile.gettempdir()):
                    shutil.rmtree(tmpdir, ignore_errors=True)
            except OSError:
                pass
