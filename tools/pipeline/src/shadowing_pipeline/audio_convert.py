"""Audio conversion and probing utilities backed by ffmpeg/ffprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .errors import AudioConversionError


def convert_to_mp3(
    input_path: str | Path,
    output_path: str | Path,
    bitrate: str = "128k",
) -> Path:
    """Convert a source audio file to MP3 and return the output path."""
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            str(destination),
        ],
        f"Failed to convert audio {source} -> {destination}",
    )
    return destination


def normalize_to_wav(
    input_path: str | Path,
    output_path: str | Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """Convert audio to an alignment-friendly mono PCM WAV."""
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-codec:a",
            "pcm_s16le",
            str(destination),
        ],
        f"Failed to normalize audio {source} -> {destination}",
    )
    return destination


def get_duration_seconds(audio_path: str | Path) -> float:
    """Return the duration of an audio file in seconds."""
    metadata = probe_audio(audio_path)
    duration = metadata.get("format", {}).get("duration")
    try:
        return round(float(duration), 3)
    except (TypeError, ValueError) as exc:
        raise AudioConversionError(f"ffprobe did not report a valid duration for {audio_path}") from exc


def probe_audio(audio_path: str | Path) -> dict[str, Any]:
    """Return ffprobe metadata for an audio file."""
    _require_ffmpeg()
    source = Path(audio_path).resolve()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise AudioConversionError(f"Failed to probe audio {source}: {stderr}") from exc
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AudioConversionError(f"ffprobe returned invalid JSON for {source}") from exc
    return payload if isinstance(payload, dict) else {}


def _run_ffmpeg(command: list[str], message: str) -> None:
    _require_ffmpeg()
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise AudioConversionError(f"{message}: {stderr}") from exc


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    raise AudioConversionError(
        "ffmpeg and ffprobe are required for audio conversion/probing. Install ffmpeg "
        "and ensure both binaries are available on PATH."
    )
