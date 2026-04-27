# Norwegian Shadowing App — AI Coding Context

This is a local/static Norwegian language shadowing app. Learners listen to Norwegian audio, follow a synchronized transcript with optional inline English glosses, and repeat sentence-sized audio segments.

## Core Flow

```text
content/raw/<lesson-id>/
  original.no.txt        -> sentence segmentation
  annotated.no.txt       -> gloss parser
  audio.wav              -> audio conversion
  meta.json              -> lesson metadata

content/processed/<lesson-id>/
  lesson.json
  captions.vtt
  audio.mp3
  alignment.json
  clean.no.txt
  build-report.json
```

Only `lesson.json`, `captions.vtt`, and `audio.mp3` are synced to `apps/web/public/lessons/<lesson-id>/`.

## Language Defaults

Use `tools/pipeline/src/shadowing_pipeline/language_config.py` as the source of truth:

- Human label: Norwegian
- Written standard: Bokmål
- Metadata language: `nb`
- ASR language: `no`
- spaCy model: `nb_core_news_sm`
- Raw suffix: `.no.txt`

