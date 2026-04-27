# scripts/

Helper scripts for local development.

## Sync Processed Lessons To Web

```bash
npm run lessons:sync
```

This runs `scripts/sync_lessons_to_web.sh`, which copies only `audio.mp3`,
`lesson.json`, and `captions.vtt` from each processed lesson into
`apps/web/public/lessons/<lesson-id>/` and regenerates
`apps/web/public/lessons/index.json`.

The script is safe to rerun. Existing copied lesson folders are replaced from
the current processed output.
