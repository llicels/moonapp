const CACHE_NAME = 'moon-study-v4';
const ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/timer.js',
    '/static/moon/new.jpg',
    '/static/moon/crescent.jpg',
    '/static/moon/half.jpg',
    '/static/moon/gibbous.jpg',
    '/static/moon/full.jpg'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip non-GET and dynamic API calls
    if (event.request.method !== 'GET' || 
        url.pathname.startsWith('/stats') || 
        url.pathname.startsWith('/weekly-stats') ||
        url.pathname.startsWith('/save')) {
        return;
    }

    // Network-first for the index page to ensure updates
    if (url.pathname === '/') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }
    
    // Cache-first for other assets
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request).then((fetchResponse) => {
                if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
                    return fetchResponse;
                }
                const responseToCache = fetchResponse.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseToCache);
                });
                return fetchResponse;
            });
        })
    );
});