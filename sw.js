const CACHE='alexandra-lucas-v2-1-network-fix';
const ASSETS=[
  './?v=2.1-network-fix','./index.html',
  './styles.css?v=2.1-network-fix','./v22.css?v=2.1-network-fix',
  './config.js?v=2.1-network-fix','./app-v22-loader.js?v=2.1-network-fix','./app.js?v=2.1-network-fix',
  './manifest.webmanifest?v=2.1-network-fix','./logo.svg?v=2.1-network-fix','./icon.svg?v=2.1-network-fix'
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
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('./?v=2.1-network-fix'))));
});
