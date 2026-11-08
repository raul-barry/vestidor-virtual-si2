const CACHE = 'fashion-store-shell-v2';

async function cacheApplicationShell() {
  const cache = await caches.open(CACHE);
  const response = await fetch('/index.html', { cache: 'no-cache' });
  if (!response.ok) throw new Error('FashionStore shell unavailable');
  await cache.put('/index.html', response.clone());
  await cache.put('/', response.clone());
  const html = await response.text();
  const queue = [];
  for (const match of html.matchAll(/(?:src|href)=["']([^"']+\.(?:js|css))["']/g)) queue.push(new URL(match[1], self.location.origin).href);
  queue.push(new URL('/manifest.webmanifest', self.location.origin).href);

  const visited = new Set();
  while (queue.length) {
    const asset = queue.shift();
    if (visited.has(asset) || new URL(asset).origin !== self.location.origin) continue;
    visited.add(asset);
    const assetResponse = await fetch(asset, { cache: 'no-cache' });
    if (!assetResponse.ok) continue;
    await cache.put(asset, assetResponse.clone());
    if (!asset.endsWith('.js')) continue;
    const source = await assetResponse.text();
    for (const match of source.matchAll(/(?:import\(\s*|from\s*)["']([^"']+\.(?:js|css))["']/g)) {
      queue.push(new URL(match[1], asset).href);
    }
  }
}

self.addEventListener('install', event => {
  event.waitUntil(cacheApplicationShell());
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith('fashion-store-shell-') && key !== CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  if (request.destination === 'image') {
    event.respondWith(caches.open(CACHE).then(async cache => {
      const cached = await cache.match(request);
      const update = fetch(request).then(response => {
        if (response.ok || response.type === 'opaque') void cache.put(request, response.clone());
        return response;
      });
      if (cached) {
        void update.catch(() => undefined);
        return cached;
      }
      return update;
    }));
    return;
  }

  event.respondWith(fetch(request).then(response => {
    if (response.ok) void caches.open(CACHE).then(cache => cache.put(request, response.clone()));
    return response;
  }).catch(async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    if (request.mode === 'navigate') return (await caches.open(CACHE)).match('/index.html');
    return new Response('', { status: 503, statusText: 'Offline resource unavailable' });
  }));
});
