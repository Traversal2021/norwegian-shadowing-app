import { appPath, lessonAssetPath } from './paths'

export async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return
  try {
    await navigator.serviceWorker.register(appPath('sw.js'), { scope: appPath('') })
  } catch {
    // PWA support is optional; the app remains usable without service workers.
  }
}

export async function cacheLessonForOffline(lessonId: string, audioFile = 'audio.mp3') {
  if (!('serviceWorker' in navigator)) return
  const registration = await navigator.serviceWorker.ready
  registration.active?.postMessage({
    type: 'CACHE_LESSON_ASSETS',
    urls: [
      lessonAssetPath(lessonId, 'lesson.json'),
      lessonAssetPath(lessonId, 'captions.vtt'),
      lessonAssetPath(lessonId, audioFile),
    ],
  })
}

export async function isLessonCached(lessonId: string, audioFile = 'audio.mp3'): Promise<boolean> {
  if (!('caches' in window)) return false
  const keys = await caches.keys()
  const targets = [
    lessonAssetPath(lessonId, 'lesson.json'),
    lessonAssetPath(lessonId, 'captions.vtt'),
    lessonAssetPath(lessonId, audioFile),
  ]
  for (const target of targets) {
    let found = false
    for (const key of keys) {
      const cache = await caches.open(key)
      if (await cache.match(target)) {
        found = true
        break
      }
    }
    if (!found) return false
  }
  return true
}

export async function clearOfflineCache() {
  if (!('serviceWorker' in navigator)) return
  const registration = await navigator.serviceWorker.ready
  registration.active?.postMessage({ type: 'CLEAR_OFFLINE_CACHE' })
}

export async function removeLessonFromOfflineCache(lessonId: string, audioFile = 'audio.mp3') {
  if (!('caches' in window)) return
  const keys = await caches.keys()
  const targets = [
    lessonAssetPath(lessonId, 'lesson.json'),
    lessonAssetPath(lessonId, 'captions.vtt'),
    lessonAssetPath(lessonId, audioFile),
  ]
  await Promise.all(
    keys.map(async (key) => {
      const cache = await caches.open(key)
      await Promise.all(targets.map((target) => cache.delete(target)))
    }),
  )
}

export async function clearLessonAssetCache() {
  if (!('caches' in window)) return
  const keys = await caches.keys()
  await Promise.all(
    keys.filter((key) => key.startsWith('norwegian-shadowing-lessons-')).map((key) => caches.delete(key)),
  )
}
