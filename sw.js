const CACHE='alexandra-lucas-logo-v2-1-restored';
const ASSETS=[
  './?v=2.1-restore','./index.html','./styles.css?v=2.1-restore','./v22.css?v=2.1-restore',
  './app-v22-loader.js?v=2.1-restore','./app-v22.payload?v=2.4',
  './config.js?v=2.1-restore','./manifest.webmanifest?v=2.1-restore',
  './logo.svg?v=2.1-restore','./icon.svg?v=2.1-restore'
];
self.addEventListener('install',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.map(key=>caches.delete(key))))
    .then(()=>caches.open(CACHE)).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key))))
    .then(()=>self.clients.claim())
));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{
    const copy=response.clone();
    caches.open(CACHE).then(cache=>cache.put(event.request,copy));
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('./?v=2.1-restore'))));
});
