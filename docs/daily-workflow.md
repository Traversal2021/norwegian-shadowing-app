# Daily Workflow

## 1. Create A Lesson Folder

```text
content/raw/my-norwegian-lesson/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json
```

`original.no.txt` is clean Norwegian. `annotated.no.txt` is the same visible text with optional English glosses.

## 2. Set Up Once

```bash
npm install
npm run env:setup
```

This installs the main pipeline environment, `nb_core_news_sm`, ffmpeg checks, and the optional faster-whisper conda environment.

## 3. Validate

```bash
npm run pipeline:validate -- --lesson my-norwegian-lesson
```

## 4. Build And Sync

Use fallback while editing:

```bash
npm run lesson:ingest -- --lesson my-norwegian-lesson --aligner fallback --force
```

Use auto when the lesson is ready for better timing:

```bash
npm run lesson:ingest -- --lesson my-norwegian-lesson --aligner auto --force
```

## 5. Run The Web App

```bash
npm run web:dev
```

Open the Vite URL and choose the lesson from the library.

## 6. Inspect Problems

```bash
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli inspect --lesson my-norwegian-lesson --stage report
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli inspect --lesson my-norwegian-lesson --stage segmentation
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli inspect --lesson my-norwegian-lesson --stage alignment
```

If annotated text drifted from the original, preview a repair:

```bash
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli repair-annotated --lesson my-norwegian-lesson --report --force
```

Review `annotated.regenerated.no.txt` before overwriting anything.

## 7. Deploy

```bash
VITE_BASE_PATH=/norwegian-shadowing-app/ npm run web:build
```

Update the base path if your GitHub repository has a different name.

