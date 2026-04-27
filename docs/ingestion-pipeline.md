# Ingestion Pipeline

The pipeline turns one Norwegian raw lesson into static web files.

Input:

```text
content/raw/<lesson-id>/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json
```

Run:

```bash
npm run lesson:ingest -- --lesson <lesson-id> --aligner fallback --force
```

## Stages

1. Load raw text, metadata, optional vocab/grammar summaries, and `audio.wav`.
2. Validate that the text files are non-empty and the audio exists.
3. Regenerate canonical annotated text from the original transcript and gloss reference.
4. Segment Norwegian sentences with `nb_core_news_sm`, or deterministic fallback if spaCy/model is unavailable.
5. Normalize audio and export `audio.mp3`.
6. Align sentence segments with the requested backend.
7. Export `lesson.json`, `captions.vtt`, alignment diagnostics, and build report.
8. Sync only web-serving files to `apps/web/public/lessons/<lesson-id>/`.

## Language Defaults

The Norwegian defaults live in `tools/pipeline/src/shadowing_pipeline/language_config.py`:

- Metadata language: `nb`
- ASR language: `no`
- spaCy model: `nb_core_news_sm`
- Primary raw suffix: `.no.txt`

## Processed Artifacts

`content/processed/<lesson-id>/` contains files for inspection:

```text
audio.mp3
lesson.json
captions.vtt
alignment.json
build-report.json
sentence-segments.json
annotated.canonical.no.txt
clean.no.txt
```

The public web folder receives only:

```text
audio.mp3
lesson.json
captions.vtt
```

