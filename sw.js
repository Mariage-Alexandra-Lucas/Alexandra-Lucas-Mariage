const CACHE='alexandra-lucas-v2-5-0-quiz-dj';
const ASSETS=[
  './','./index.html',
  './styles.css?v=2.4.0','./v22.css?v=2.4.0','./nav-v232.css?v=2.4.0','./features-v24.css?v=2.4.0','./quiz-v25.css?v=2.5.0',
  './config.js?v=2.4.0','./app.js?v=2.4.0','./ui-v23.js?v=2.4.0','./logo-fix.js?v=2.4.0','./features-v24.js?v=2.4.0','./quiz-v25.js?v=2.5.0',
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
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{
    const copy=response.clone();
    caches.open(CACHE).then(cache=>cache.put(event.request,copy));
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('./'))));
});
