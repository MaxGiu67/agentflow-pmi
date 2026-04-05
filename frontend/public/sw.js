/**
 * AgentFlow PMI — Service Worker (manual, no Workbox)
 *
 * Strategies:
 * - HTML pages: network first (always get fresh after deploy)
 * - Hashed assets (/assets/*): cache first (immutable, hash in filename)
 * - API calls: network first, fallback to cache
 * - Static files: stale-while-revalidate
 */

const CACHE_NAME = 'agentflow-v2'
const APP_SHELL = [
  '/manifest.json',
  '/favicon.svg',
  '/icon-192.svg',
  '/icon-512.svg',
]

// Install: precache static shell (NOT index.html — that must be network-first)
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  )
  self.skipWaiting()
})

// Activate: cleanup old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  )
  self.clients.claim()
})

// Fetch handler
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') return

  // Skip cross-origin requests (API on different domain)
  if (url.origin !== self.location.origin) return

  // API calls: network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request))
    return
  }

  // HTML navigation: ALWAYS network first (critical for deploy freshness)
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(networkFirst(request))
    return
  }

  // Hashed assets (/assets/*.js, /assets/*.css): cache first (immutable)
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(request))
    return
  }

  // Everything else: stale-while-revalidate
  event.respondWith(staleWhileRevalidate(request))
})

// ── Strategies ──

async function networkFirst(request) {
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    return cached || new Response('Offline', { status: 503 })
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request)
  if (cached) return cached
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return new Response('', { status: 503 })
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request)
  const fetchPromise = fetch(request).then((response) => {
    if (response.ok) {
      caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()))
    }
    return response
  }).catch(() => cached)

  return cached || fetchPromise
}
