# shadowing-pipeline

Python package for turning raw Norwegian lesson folders into web-ready static lesson files.

Raw input:

```text
content/raw/<lesson-id>/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json
```

Build:

```bash
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli build --lesson <lesson-id> --aligner fallback --force
```

Refresh and sync to the web app:

```bash
npm run lesson:ingest -- --lesson <lesson-id> --aligner auto --force
```

Norwegian defaults are centralized in `src/shadowing_pipeline/language_config.py`:

- Metadata language: `nb`
- ASR language: `no`
- spaCy model: `nb_core_news_sm`
- Raw text suffix: `.no.txt`

