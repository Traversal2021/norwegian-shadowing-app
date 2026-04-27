# content/raw/

Put one raw Norwegian lesson folder here.

```text
content/raw/<lesson-id>/
  original.no.txt      Clean Norwegian text
  annotated.no.txt     Same text with optional inline English glosses
  audio.wav            Real recording
  meta.json            Optional metadata, language defaults to "nb"
```

The documented suffix is `.no.txt`. `.nb.txt` is also accepted.

Text-only examples can live here, but folders without `audio.wav` are skipped by `--all` builds and cannot be ingested directly until a real recording is added.

Build a lesson with:

```bash
npm run lesson:ingest -- --lesson <lesson-id> --aligner fallback --force
```

See [docs/content-format.md](../../docs/content-format.md) for the full content rules.

