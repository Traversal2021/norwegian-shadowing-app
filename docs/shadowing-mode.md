# Shadowing Mode

Phase 3 adds a shadowing-oriented lesson detail experience while keeping the
static lesson architecture.

## Controls

- `Space`: play or pause.
- `J`: previous segment.
- `K`: next segment.
- `R`: replay current segment.
- `F`: toggle focus mode.

Touch users can use the visible Previous, Replay, Next, Repeat, Gap,
Auto-advance, Auto-follow, and Focus controls.

## Repeat And Gap

Repeat options:

- `1x`
- `2x`
- `3x`
- `5x`
- infinite

Gap options:

- `0s`
- `0.5s`
- `1s`
- `2s`

When auto-advance is on, the player completes the current segment, applies the
repeat rule, waits for the configured gap, then moves to the next segment.

## Focus Mode

Focus mode hides non-essential UI, enlarges transcript text, and keeps the
bottom playback controls available. It is intended for commute-style listening
and repeating.

## Transcript States

The transcript distinguishes:

- active segment
- completed segments
- upcoming segments
- difficult segments marked locally

If token timings are present in `lesson.json`, the active token is highlighted
progressively. If token timings are absent, the app falls back to segment-level
highlighting.

## Local State

The app stores per-lesson state in `localStorage` only:

- last playback position
- playback speed
- repeat mode
- gap mode
- auto-advance
- focus mode
- auto-follow
- difficult segment ids

There is no user account, cloud sync, analytics, or backend persistence in this
phase.

## Alignment Metadata

New Phase 3 lessons may include optional `alignmentMeta` and optional token
timing fields:

```json
{
  "alignmentMeta": {
    "alignerRequested": "auto",
    "alignerUsed": "real-cli",
    "fallbackOccurred": false,
    "hasTokenTimings": true
  },
  "segments": [
    {
      "tokens": [
        { "text": "Hej", "start": 0.1, "end": 0.4 }
      ]
    }
  ]
}
```

Older Phase 2 lessons without these fields still load normally.
