# Data Portability

Phase 5 keeps all study data local and lets you export/import it manually.

## Study Data Export

Use `Export study data` on the library page. The app downloads:

```json
{
  "schemaVersion": 1,
  "exportedAt": "2026-04-23T00:00:00.000Z",
  "lessonMetadata": {
    "lesson-id": {
      "lessonId": "lesson-id",
      "lastOpenedAt": "2026-04-23T00:00:00.000Z",
      "difficultCount": 2,
      "cached": true,
      "started": true,
      "completed": false
    }
  },
  "sessions": {
    "lesson-id": {
      "lastPlaybackPosition": 12.5,
      "playbackSpeed": 1,
      "repeatMode": 3,
      "pauseSec": 1,
      "autoAdvance": true,
      "focusMode": false,
      "autoFollow": true,
      "difficultSegmentIds": ["s2", "s4"]
    }
  }
}
```

## Study Data Import

Use `Import study data` on the library page and choose a previous JSON export.
The app asks whether to overwrite overlapping local records.

- Cancel keeps existing local records and imports only missing ones.
- Confirm overwrites overlapping lesson metadata and sessions.

The import is entirely client-side.

## Vocab Export

Vocab export is available as CSV or JSON from:

- The library page for all available lessons.
- A lesson page for a single lesson.

CSV columns:

```text
lessonId,lessonTitle,word,definition,example
```

JSON shape:

```json
[
  {
    "lessonId": "lesson-id",
    "lessonTitle": "Lesson title",
    "word": "ciffer",
    "definition": "digit",
    "example": "Et ciffer."
  }
]
```

There is no direct Anki sync in Phase 5.
