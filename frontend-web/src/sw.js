const CACHE = 'fashion-store-shell-v1';
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(['/','/index.html','/manifest.webmanifest'])));
  self.skipWaiting();
});
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (event.request.destination === 'image' && url.pathname.startsWith('/assets/catalog/')) {
    event.respondWith(caches.match(event.request).then(cached => {
      const update = fetch(event.request).then(response => {
        if (response.ok || response.type === 'opaque') caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
        return response;
      });
      return cached || update;
    }));
    return;
  }
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  event.respondWith(fetch(event.request).then(response => {
    if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, copy)); }
    return response;
  }).catch(() => caches.match(event.request).then(cached => cached || caches.match('/index.html'))));
});
