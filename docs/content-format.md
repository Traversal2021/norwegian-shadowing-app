# Content Format

Each Norwegian lesson lives in `content/raw/<lesson-id>/`.

```text
content/raw/<lesson-id>/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json        optional
  vocab.json|md    optional
  grammar.json|md  optional
```

Use `.no.txt` for raw text files. `.nb.txt` is accepted for Bokmål compatibility, but `.no.txt` is the documented default.

## Metadata

If `meta.json` is missing or incomplete, the pipeline fills in:

```json
{
  "id": "<folder-name>",
  "title": "<folder-name as title>",
  "source": "Norwegian learning material",
  "language": "nb",
  "tags": ["norwegian", "shadowing"],
  "level": "unknown"
}
```

`language` should be `nb` for Bokmål lesson metadata. ASR tools use `no` internally.

## Original Text

`original.no.txt` is the canonical visible transcript. Keep it clean: Norwegian text only, with normal punctuation and sentence boundaries.

```text
Hei, og velkommen til norsk skyggetrening.
Jeg leser en kort tekst.
```

## Annotated Text

`annotated.no.txt` must preserve the same visible text as `original.no.txt`. Add optional English glosses in parentheses after the word or phrase they explain:

```text
Hei(hello), og velkommen(welcome) til norsk skyggetrening(shadowing practice).
Jeg leser(read) en kort(short) tekst.
```

After glosses are removed, the annotated text must match the original text. The repair command can regenerate a canonical annotated file from the original text plus old gloss placements:

```bash
PYTHONPATH=tools/pipeline/src .venv/bin/python -m shadowing_pipeline.cli repair-annotated --lesson <lesson-id> --report
```

By default this writes `annotated.regenerated.no.txt`. Add `--write --backup --force` only after reviewing the output.

## Audio

`audio.wav` must be a real recording of the text. The pipeline normalizes it and exports `audio.mp3` for the web app.

## Processed Outputs

The build writes inspectable artifacts under `content/processed/<lesson-id>/`, including:

```text
lesson.json
captions.vtt
alignment.json
build-report.json
annotated.canonical.no.txt
clean.no.txt
sentence-segments.json
audio.mp3
```

Only `lesson.json`, `captions.vtt`, and `audio.mp3` are synced to the web app.

