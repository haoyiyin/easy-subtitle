# easy-subtitle

**Offline audio/video to SRT subtitle converter** — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Features

- 🎙️ **Offline transcription** — no cloud API, no internet required
- 🌍 **Auto language detection** — 99 languages detected automatically
- 📝 **Original-text alignment** — fix Whisper errors by providing your script
- 🎬 **Video + audio support** — .mp4, .mkv, .mov, .mp3, .wav, and more
- 🔇 **Smart silence skipping** — VAD filters out long pauses

## Quick Start

```bash
# 1. Install Python package
pip install -e .

# 2. Install ffmpeg (system-level)
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Linux (Debian/Ubuntu)
choco install ffmpeg         # Windows (Chocolatey)

# 3. Basic use
easy-subtitle -i video.mp4

# With language hint
easy-subtitle -i audio.wav -l zh

# Fix transcription with your script
easy-subtitle -i video.mp4 --original-text script.txt
```

## How Original-Text Alignment Works

When you provide `--original-text script.txt`, the tool:

1. Transcribes the audio with faster-whisper (getting text + timestamps)
2. Uses a greedy sliding-window diff algorithm to map each Whisper segment to the best-matching span in your script
3. Replaces the Whisper text with the exact original script text while preserving timestamps

This is ideal for:

- Podcasts with a prepared script
- Video voiceovers read from a teleprompter
- Audiobook recordings from a manuscript

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-i, --input` | Input audio/video file | **required** |
| `-o, --output` | Output SRT path | `<input>.srt` |
| `-m, --model` | Model size: tiny/base/small/medium/large-v2/large-v3 | `medium` |
| `-l, --language` | Language code (zh, en, ja…) | auto-detect |
| `--original-text` | Script file for alignment | off |
| `--device` | auto / cpu / cuda | `auto` |
| `--beam-size` | Decoding beam size | `5` |
| `--no-vad` | Disable voice activity detection | on |
| `--vad-min-silence` | Min silence for VAD split (ms) | `500` |

## Requirements

- Python ≥ 3.10
- `pip install faster-whisper`
- `ffmpeg` (system-level):
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg` (Fedora)
  - **Windows**: `choco install ffmpeg` (Chocolatey), `scoop install ffmpeg` (Scoop), or <https://ffmpeg.org>
