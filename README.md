# Norwegian Shadowing App

A local web app for Norwegian shadowing practice. You give it Norwegian text, optional inline English glosses, and a real `audio.wav`; it builds a static lesson with audio playback, synced transcript highlighting, click-to-seek, repeat-current-segment controls, and optional gloss display.

The app is Norwegian-first:

- Human label: Norwegian
- Written standard: Bokmål
- Lesson metadata language: `nb`
- ASR language for faster-whisper/Whisper-style tools: `no`
- spaCy sentence model: `nb_core_news_sm`
- Raw text filenames: `original.no.txt` and `annotated.no.txt`

## Input Folder Format

Create one folder per lesson under `content/raw/`:

```text
content/raw/<lesson-id>/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json        optional
```

`original.no.txt` is the clean Norwegian transcript. `annotated.no.txt` contains the same visible text, with optional glosses after words or phrases:

```text
Jeg liker(like) norsk veldig(very) godt.
```

The pipeline also accepts `original.nb.txt` / `annotated.nb.txt` for Bokmål. `original.no.txt` is the documented default because it is friendlier to type.

## Example Lesson

```text
content/raw/test-norwegian/
  original.no.txt
  annotated.no.txt
  audio.wav
  meta.json
```

Minimal `meta.json`:

```json
{
  "id": "test-norwegian",
  "title": "Test Norwegian",
  "source": "Norwegian learning material",
  "language": "nb",
  "tags": ["norwegian", "shadowing"],
  "level": "unknown"
}
```

If `meta.json` is missing, those values are generated from the folder name.

There is a text-only example in `content/raw/sample-norwegian/`. It intentionally has no audio. Add a real `audio.wav` before ingesting it.

## Set Up

Run this once:

```bash
npm install
npm run env:setup
```

`env:setup` creates the main `.venv`, installs the pipeline, installs spaCy with `nb_core_news_sm`, checks `ffmpeg`, and sets up the separate faster-whisper conda environment when conda is available. Heavy ASR packages are not installed into the main `.venv`.

## Ingest A Lesson

For a reliable first run, use fallback alignment:

```bash
npm run lesson:ingest -- --lesson test-norwegian --aligner fallback --force
```

For automatic alignment, which tries external alignment/faster-whisper before falling back:

```bash
npm run lesson:ingest -- --lesson test-norwegian --aligner auto --force
```

The command builds `content/processed/<lesson-id>/`, syncs the web files, and refreshes the lesson manifest.

## Run The Web App

```bash
npm run web:dev
```

Open the local URL printed by Vite, usually `http://localhost:5173/`.

## How Alignment Works

The pipeline first segments `original.no.txt` into sentences. It then assigns timestamps to each sentence using the requested aligner:

- `fallback`: spreads sentence timings across the audio duration. It is deterministic and always local, but approximate.
- `auto`: checks for `alignment.external.json`, then tries faster-whisper if configured, then WhisperX if configured, then fallback.
- `fastwhisper`: requires the separate conda ASR environment and uses ASR language `no`.
- `external`: uses a prebuilt `alignment.external.json`.

The web app uses the final segment timings to highlight the current sentence, scroll the transcript, seek when a segment is clicked, and repeat the current segment.

## Fallback vs Faster-Whisper

Fallback alignment is good for checking the lesson quickly. It does not listen to the audio; it estimates timings from sentence count and audio length.

Faster-whisper alignment runs speech recognition in the separate ASR environment, maps recognized speech back to your sentence list, and usually produces better sentence timing. It may need model downloads and can be slower on CPU.

## Synced Web Files

Only these files are copied to `apps/web/public/lessons/<lesson-id>/`:

```text
audio.mp3
lesson.json
captions.vtt
```

Intermediate files like `alignment.json`, `build-report.json`, normalized WAVs, and regenerated annotation files stay in `content/processed/<lesson-id>/`.

## Deploy To GitHub Pages

Build the static web app with the repo base path:

```bash
VITE_BASE_PATH=/norwegian-shadowing-app/ npm run web:build
```

The included GitHub Pages workflow uses that base path. If your repository has a different name, update `VITE_BASE_PATH` in `.github/workflows/deploy.yml`.

## Troubleshooting

- `.venv is missing`: run `npm run env:setup`.
- `audio.wav` missing: add a real WAV file to the raw lesson folder.
- spaCy model unavailable: run `npm run env:setup` again; ingestion will fall back to deterministic sentence splitting with a warning.
- faster-whisper unavailable: use `--aligner fallback`, or install conda and rerun `npm run env:setup`.
- Lesson does not appear in the web app: rerun `npm run lesson:ingest -- --lesson <lesson-id> --aligner fallback --force`.
- Transcript text mismatch: make sure `annotated.no.txt` has the same visible text as `original.no.txt` after glosses are removed.
- GitHub Pages blank paths: check that `VITE_BASE_PATH` matches your repository name.

