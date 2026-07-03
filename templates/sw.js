/* Service worker Social Immo — sert a l'installation PWA/app stores.
   Strategie prudente : reseau d'abord pour les pages (jamais de contenu
   perime), cache pour les statiques, page hors-ligne en secours. */
const VERSION = 'si-v1';
const OFFLINE_URL = '/offline/';
const PRECACHE = [OFFLINE_URL, '/static/css/app.css', '/static/icons/icon-192.png'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cles) =>
            Promise.all(cles.filter((c) => c !== VERSION).map((c) => caches.delete(c)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    if (url.origin !== self.location.origin) return;

    // Statiques : cache d'abord (ils sont versionnes par WhiteNoise)
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(req).then((hit) => hit || fetch(req).then((rep) => {
                const copie = rep.clone();
                caches.open(VERSION).then((cache) => cache.put(req, copie));
                return rep;
            }))
        );
        return;
    }

    // Pages : reseau d'abord, page hors-ligne en secours
    if (req.mode === 'navigate') {
        event.respondWith(
            fetch(req).catch(() => caches.match(OFFLINE_URL))
        );
    }
});
