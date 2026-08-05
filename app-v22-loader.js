(async()=>{
  try{
    const encoded=await fetch('./app-v22.payload?v=2.4',{cache:'no-store'}).then(r=>r.text());
    const bytes=Uint8Array.from(atob(encoded.trim()),c=>c.charCodeAt(0));
    const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    let source=await new Response(stream).text();
    const logo='./logo-v27.jpg?v=2.7';
    source=source.replaceAll('./logo-officiel.webp',logo);
    source=source.replaceAll('./logo-officiel.png?v=2.3',logo);
    source=source.replaceAll('./logo-mariage-v24.svg?v=2.4',logo);
    source=source.replaceAll('./logo-al.svg',logo);
    source=source.replaceAll('./logo.svg',logo);
    (0,eval)(source);
  }catch(error){
    console.error(error);
    document.querySelector('#app').innerHTML='<main style="padding:32px;font-family:sans-serif"><h1>Application indisponible</h1><p>Rechargez la page dans quelques instants.</p></main>';
  }
})();
