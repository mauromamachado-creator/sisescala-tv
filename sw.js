// SisGOPA Service Worker
const CACHE_NAME = 'sisgopa-v1';
const STATIC_ASSETS = [
  '/sisescala-tv/',
  '/sisescala-tv/index.html',
  '/sisescala-tv/manifest.json',
  '/sisescala-tv/icon-192.png',
  '/sisescala-tv/icon-512.png',
  '/sisescala-tv/apple-touch-icon.png'
];

// Instala e faz cache dos assets estáticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Ativa e limpa caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Estratégia: Network first, fallback para cache
self.addEventListener('fetch', event => {
  // Ignora requisições externas (planilhas, Telegram, etc.)
  if (!event.request.url.includes('mauromamachado-creator.github.io')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
