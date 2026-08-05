const CACHE='alexandra-lucas-v2-3-4-org-migration';
const ASSETS=[
  './','./index.html',
  './styles.css?v=2.3.4-org','./v22.css?v=2.3.4-org','./nav-v232.css?v=2.3.4-org',
  './config.js?v=2.3.4-org','./app.js?v=2.3.4-org','./ui-v23.js?v=2.3.4-org','./logo-fix.js?v=2.3.4-org',
  './manifest.webmanifest?v=2.3.4-org','./logo.svg?v=2.3.4-org','./icon.svg?v=2.3.4-org',
  './icon-192.png','./icon-512.png','./apple-touch-icon.png'
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
