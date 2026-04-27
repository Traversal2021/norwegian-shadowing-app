# Offline And PWA

The web app is installable as a PWA and includes a small custom service worker.

## What Is Cached

The service worker uses two caches:

- App shell cache: the app entry page, web manifest, icon, and runtime app assets as they are requested.
- Lesson cache: lesson JSON, captions, and audio for lessons that are opened or explicitly requested by the app.

The app does not pre-cache the full lesson library. This keeps installs small
and avoids surprising downloads of large audio files.

## When Lesson Assets Are Cached

When a lesson page opens, the app asks the service worker to cache:

- `lesson.json`
- `captions.vtt`
- `audio.mp3`

The library page shows an `offline` badge when all three assets are present in
the browser cache.

## Cache Controls

The lesson page includes controls to cache or remove that lesson's assets. The
library page can clear all lesson assets.

Clearing lesson assets does not remove the app shell cache. The installed app can
still launch, but uncached lesson pages need network access again.

## Offline Behavior

- Reopening a cached lesson offline should work.
- Opening an uncached lesson offline shows the existing lesson load error state.
- If audio is missing or was never cached, the transcript still loads if
  `lesson.json` is cached.

## Development Cache Reset

During development, stale service worker assets can be confusing. Use one of
these options:

```js
navigator.serviceWorker.getRegistrations().then((regs) => regs.forEach((reg) => reg.unregister()))
caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
```

Then hard refresh the page.

In Chrome/Edge DevTools, Application -> Service Workers -> Unregister and
Application -> Storage -> Clear site data does the same thing.

## GitHub Pages

The app uses Vite `BASE_URL` for service worker registration and lesson fetches.
For GitHub Pages, build with the repo base path:

```bash
VITE_BASE_PATH=/norwegian-shadowing-app/ npm run web:build
```

The service worker scope follows that base path.
