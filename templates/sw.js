const CACHE_NAME = 'wheels-cache-v4';
const ASSETS = [
  // Главная страница и точки входа
  '/',
  '/index.html',
  
  // Основные HTML-страницы (проверьте точные имена!)
  '/index_pwa.html',
  '/glav3.html',
  '/glaw_pwa.html',
  '/glaw_pwa_copy.html',
  '/glav_pwa_copy_2.html',
  '/glav_pwa_copy_3.html',
  '/glav_pwa_copy_4.html',
  '/glav_pwa_copy_5.html',
  '/tormoz.html',
  '/shiny.html',
  '/salon.html',
  '/podveska.html',
  '/fary.html',
  '/end.html',
  '/electric.html',
  '/diagnostik.html',

  
  // Иконки PWA
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  
  // Внешние ресурсы
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Кэшируем основные ресурсы');
        return cache.addAll(ASSETS)
          .catch(err => console.error('[SW] Ошибка кэширования:', err));
      })
  );
});

self.addEventListener('fetch', event => {
  // Игнорируем POST-запросы и другие не-GET
  if (event.request.method !== 'GET') return;
  
  // Стратегия: Cache First, с обновлением кэша
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // 1. Возвращаем кэш если есть
        if (cachedResponse) {
          // Обновляем кэш в фоне
          fetchAndCache(event.request);
          return cachedResponse;
        }
        
        // 2. Иначе загружаем из сети
        return fetchAndCache(event.request);
      })
      .catch(() => {
        // Fallback для ошибок
        if (event.request.mode === 'navigate') {
          return caches.match('/index.html');
        }
      })
  );
});

function fetchAndCache(request) {
  return fetch(request).then(response => {
    // Клонируем ответ для кэширования
    const responseToCache = response.clone();
    
    // Кэшируем только GET-запросы и локальные ресурсы
    if (response.ok && request.url.startsWith(location.origin)) {
      caches.open(CACHE_NAME)
        .then(cache => cache.put(request, responseToCache))
        .catch(err => console.warn('[SW] Не удалось закэшировать:', request.url, err));
    }
    
    return response;
  });
}

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('[Service Worker] Удаляем старый кэш:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});