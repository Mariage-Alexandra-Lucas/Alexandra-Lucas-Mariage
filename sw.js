const CACHE='alexandra-lucas-v2-8-0-performance';
const ASSETS=[
  './','./index.html',
  './styles.css?v=2.4.0','./v22.css?v=2.4.0','./nav-v232.css?v=2.4.0','./features-v24.css?v=2.6.0','./quiz-v25.css?v=2.7.0','./events-v26.css?v=2.7.0','./console-v27.css?v=2.7.0','./qr-print-v271.css?v=2.7.1','./games-v272.css?v=2.7.2','./performance-v28.css?v=2.8.0',
  './config.js?v=2.4.0','./app.js?v=2.8.0','./ui-v23.js?v=2.4.0','./logo-fix.js?v=2.4.0','./features-v24.js?v=2.8.0','./quiz-v25.js?v=2.8.0','./events-v26.js?v=2.8.0','./performance-v28.js?v=2.8.0',
  './manifest.webmanifest?v=2.4.0','./logo.svg','./icon.svg','./icon-192.png','./icon-512.png','./apple-touch-icon.png',
  './qr-guadeloupe.svg','./qr-ile-maurice.svg','./qr-maldives.svg','./qr-mexique.svg'
];
self.addEventListener('install',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('alexandra-lucas-')).map(key=>caches.delete(key))))
    .then(()=>caches.open(CACHE)).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('alexandra-lucas-')&&key!==CACHE).map(key=>caches.delete(key))))
    .then(()=>self.clients.claim())
));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);if(url.origin!==self.location.origin)return;
  if(event.request.mode==='navigate'){
    event.respondWith(fetch(event.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put('./index.html',copy));return response}).catch(()=>caches.match('./index.html')));return;
  }
  event.respondWith(caches.match(event.request).then(cached=>{
    const update=fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy))}return response}).catch(()=>cached);
    return cached||update;
  }));
});
