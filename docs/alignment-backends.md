# Alignment Backends

Alignment assigns start and end times to Norwegian sentence segments.

## Modes

- `fallback`: deterministic sentence-level timing. It uses audio duration and sentence count, so it is approximate but always available.
- `auto`: tries an existing `alignment.external.json`, then faster-whisper, then WhisperX, then fallback.
- `fastwhisper`: runs `tools/alignment/faster_whisper_runner.py` in the separate conda ASR environment.
- `whisperx`: optional legacy external runner. It is not required.
- `external`: reads a standardized `alignment.external.json`.

## Norwegian Language Codes

Lesson metadata uses `nb` for Bokmål. ASR runners use `no`, which is the expected language code for faster-whisper/Whisper-style transcription.

## faster-whisper

`npm run env:setup` creates a separate conda environment named `shadowing-asr` when conda is available. The main `.venv` does not receive heavy ASR packages.

`run_ingestion.sh` exposes the runner through `SHADOWING_FASTWHISPER_CMD` when the environment passes its self-check.

## External JSON Shape

An external alignment file should look like:

```json
{
  "schemaVersion": 1,
  "lessonId": "test-norwegian",
  "aligner": "faster-whisper-external",
  "language": "no",
  "segments": [
    {
      "id": "s1",
      "text": "Hei, og velkommen.",
      "start": 0.0,
      "end": 2.4,
      "words": [
        { "word": "Hei", "start": 0.1, "end": 0.4, "confidence": 0.95 }
      ]
    }
  ],
  "warnings": [],
  "notes": []
}
```

`language` may be `no` or `nb`. `no` is preferred for ASR output.

## Choosing A Mode

Use `fallback` while editing text or checking that the lesson builds. Use `auto` for normal ingestion once the ASR environment is ready. Use `fastwhisper` when you want the build to fail if faster-whisper is unavailable.

