"""Stage E-prep: normalize and probe audio."""

from __future__ import annotations

from ..audio_convert import convert_to_mp3, get_duration_seconds, normalize_to_wav, probe_audio
from ..errors import AudioConversionError
from .context import BuildContext, StageDiagnostics


def stage_normalize_audio(context: BuildContext) -> BuildContext:
    raw = context.raw_lesson
    if raw is None:
        raise AudioConversionError(
            f"Stage normalize-audio failed for {context.lesson_id}: raw lesson not loaded."
        )

    context.output_dir.mkdir(parents=True, exist_ok=True)
    normalized_wav = normalize_to_wav(raw.audio_path, context.output_dir / "audio.normalized.wav")
    audio_mp3 = convert_to_mp3(raw.audio_path, context.output_dir / "audio.mp3")
    probe = probe_audio(normalized_wav)
    context.normalized_audio_path = normalized_wav
    context.audio_mp3_path = audio_mp3
    context.audio_probe = probe
    context.duration_seconds = get_duration_seconds(normalized_wav)
    context.add_diagnostics(
        StageDiagnostics(
            stage="normalize-audio",
            artifacts={"normalizedAudio": str(normalized_wav), "webAudio": str(audio_mp3)},
        )
    )
    return context
