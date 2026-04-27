# Architecture

Norwegian Shadowing is a static/local app:

- `apps/web/`: React + Vite lesson player.
- `content/raw/`: user-authored Norwegian lesson inputs.
- `content/processed/`: generated lesson artifacts.
- `tools/pipeline/`: Python ingestion pipeline.
- `tools/alignment/`: optional external ASR runners.
- `scripts/`: setup, ingestion, and sync helpers.

## Data Flow

```text
content/raw/<lesson-id>/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json

      ↓ pipeline

content/processed/<lesson-id>/
  lesson.json
  captions.vtt
  audio.mp3
  build-report.json
  alignment.json

      ↓ sync

apps/web/public/lessons/<lesson-id>/
  lesson.json
  captions.vtt
  audio.mp3
```

Only web-serving files are copied into `apps/web/public/lessons`.

## Language Defaults

Language defaults are centralized in `tools/pipeline/src/shadowing_pipeline/language_config.py`.

- Raw suffix: `.no.txt`
- Metadata: `nb`
- ASR: `no`
- spaCy: `nb_core_news_sm`

## GitHub Pages

For this repo name:

```bash
VITE_BASE_PATH=/norwegian-shadowing-app/ npm run web:build
```

