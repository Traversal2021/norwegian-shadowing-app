# Review Workflow

Phase 5 adds local-only review tools on top of the lesson player.

## Library Dashboard

The library supports:

- Search by title, source, and tags.
- Filters for started, completed, offline cached, and lessons with difficult segments.
- Sort by title, last opened, recently added, and difficult segment count.

All metadata is stored locally in `localStorage`.

## Difficult-Segment Drill

Open a lesson and choose `Drill difficult`. The drill view:

- Plays only segments marked difficult in that lesson.
- Reuses repeat and gap controls.
- Supports previous/next and replay controls.
- Falls back cleanly to sentence-level timing when token timings are absent.

If there are no difficult segments, the lesson shows a friendly empty state.

## Review Queue

The library `Review queue` button builds a deterministic local queue from:

- Lessons with difficult segments.
- Started but incomplete lessons.
- Recently opened incomplete lessons.

This is not a full spaced-repetition system. It is a lightweight retrieval prompt
to help decide what to study next.

## Deferred

There is no backend sync, account system, spaced-repetition scheduling, Anki
sync, analytics, or AI-generated review material in Phase 5.
