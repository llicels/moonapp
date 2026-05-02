const CACHE_NAME = 'moon-study-v2';
const ASSETS = [
    '/',
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

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    if (event.request.method !== 'GET' || url.pathname.startsWith('/stats') || url.pathname.startsWith('/weekly')) {
        event.respondWith(fetch(event.request));
        return;
    }
    
    event.respondWith(
        caches.match(event.request).then((response) => {
            if (response) {
                return response;
            }
            return fetch(event.request).then((response) => {
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                const responseToCache = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseToCache);
                });
                return response;
            });
        })
    );
});