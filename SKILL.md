---
name: "easy-subtitle"
description: "Convert audio/video to SRT subtitles offline using faster-whisper with auto language detection and optional original-text alignment for automatic subtitle error correction."
version: 1
created: "2026-06-27"
updated: "2026-06-27"
---
## When to Use

Use this skill when the user needs to:

- Generate SRT subtitles from an audio or video file (offline, no API calls)
- Automatically detect the spoken language in a media file
- Fix/correct Whisper transcription errors using a provided original spoken script (原口播文本)
- Batch-process media files into subtitles

Do NOT use for:

- Real-time/live transcription (faster-whisper is offline/batch only)
- Non-SRT output formats (only SRT is supported)
- Cloud-based transcription (this is local-only)

## Procedure

1. Install dependencies: `pip install faster-whisper`. Install ffmpeg for your OS:
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)
   - **Windows**: `choco install ffmpeg` (Chocolatey) or `scoop install ffmpeg` (Scoop), or download from <https://ffmpeg.org>
2. Ensure the easy-subtitle package is installed: `pip install -e .` from the project root.
3. **Basic transcription**: Run `easy-subtitle -i video.mp4` to generate `video.srt` with auto-detected language.
4. **Specify language**: Run `easy-subtitle -i audio.wav -l zh` if you know the language (faster and more accurate than auto-detect).
5. **Fix with original script**: Run `easy-subtitle -i video.mp4 --original-text script.txt` to align and correct the transcription using the provided script.
6. **Tune model size**: Use `-m small` for speed or `-m large-v3` for accuracy. Default is `medium`.
7. **Adjust VAD**: Use `--vad-min-silence 1000` for more aggressive silence splitting (quieter content). Use `--no-vad` to disable.

## Pitfalls

- First run downloads the model (~1.5GB for medium) — allow extra time and disk space.
- Whisper auto language detection can be unreliable for very short clips (<5 seconds) — use -l to specify manually.
- Original-text alignment works best when the script matches the audio verbatim. Ad-libs, pauses, and improvisations will be left as Whisper output.
- faster-whisper uses INT8 quantization by default on CPU — this is fast but slightly less accurate than FP16 on GPU.
- ffmpeg must be installed separately (not a Python package).
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt install ffmpeg`
  - **Windows**: `choco install ffmpeg` or download from <https://ffmpeg.org>

## Verification

1. Run `easy-subtitle --version` to confirm installation.
2. Test basic transcription: `easy-subtitle -i test_audio.mp3 -m tiny` should produce a .srt file quickly.
3. Verify SRT output: open in a video player or check that it contains numbered blocks with `HH:MM:SS,mmm --> HH:MM:SS,mmm` timestamps.
4. Test original-text alignment: provide a script that matches the audio — the output should contain the exact script text, not Whisper's transcription.
