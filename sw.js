const CACHE='alexandra-lucas-v2-6-logo-original';
const ASSETS=[
  './?v=2.6','./index.html','./styles.css?v=2.6','./v22.css?v=2.6',
  './app-v22-loader.js?v=2.6','./app-v22.payload?v=2.4',
  './config.js?v=2.6','./manifest.webmanifest?v=2.6','./logo-v26.b64?v=2.6'
];
async function logoResponse(){
  const encoded=await fetch('./logo-v26.b64?v=2.6',{cache:'no-store'}).then(r=>r.text());
  const bytes=Uint8Array.from(atob(encoded.trim()),c=>c.charCodeAt(0));
  return new Response(bytes,{headers:{'Content-Type':'image/png','Cache-Control':'no-store'}});
}
self.addEventListener('install',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.map(k=>caches.delete(k))))
    .then(()=>caches.open(CACHE)).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())
));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.pathname.endsWith('/icon-v26.png')){event.respondWith(logoResponse());return;}
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{
    const copy=response.clone();
    caches.open(CACHE).then(cache=>cache.put(event.request,copy));
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('./?v=2.6'))));
});
