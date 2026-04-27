const VERSION = 'phase-5-v1'
const APP_CACHE = `norwegian-shadowing-app-${VERSION}`
const LESSON_CACHE = `norwegian-shadowing-lessons-${VERSION}`

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_CACHE).then((cache) =>
      cache.addAll([
        self.registration.scope,
        `${self.registration.scope}manifest.webmanifest`,
        `${self.registration.scope}pwa-icon.svg`,
      ]),
    ),
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith('norwegian-shadowing-') && ![APP_CACHE, LESSON_CACHE].includes(key))
            .map((key) => caches.delete(key)),
        ),
      ),
  )
  self.clients.claim()
})

self.addEventListener('message', (event) => {
  const data = event.data || {}
  if (data.type === 'CACHE_LESSON_ASSETS' && Array.isArray(data.urls)) {
    event.waitUntil(cacheLessonAssets(data.urls))
  }
  if (data.type === 'CLEAR_OFFLINE_CACHE') {
    event.waitUntil(
      Promise.all([caches.delete(APP_CACHE), caches.delete(LESSON_CACHE)]).then(() => self.skipWaiting()),
    )
  }
  if (data.type === 'CLEAR_LESSON_CACHE') {
    event.waitUntil(caches.delete(LESSON_CACHE))
  }
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, APP_CACHE, self.registration.scope))
    return
  }

  if (url.pathname.includes('/lessons/')) {
    event.respondWith(cacheFirst(request, LESSON_CACHE))
    return
  }

  event.respondWith(staleWhileRevalidate(request, APP_CACHE))
})

async function cacheLessonAssets(urls) {
  const cache = await caches.open(LESSON_CACHE)
  await Promise.all(
    urls.map(async (url) => {
      try {
        const response = await fetch(url, { cache: 'no-cache' })
        if (response.ok) await cache.put(url, response)
      } catch {
        // Offline or missing optional asset; keep existing cached copy if present.
      }
    }),
  )
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName)
  try {
    const response = await fetch(request)
    if (response.ok) cache.put(request, response.clone())
    return response
  } catch {
    return (await cache.match(request)) || (await cache.match(fallbackUrl)) || Response.error()
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  const network = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone())
      return response
    })
    .catch(() => cached)
  return cached || network
}
