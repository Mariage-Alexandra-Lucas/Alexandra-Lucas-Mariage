(()=>{
  const nativeFetch=window.fetch.bind(window);
  window.fetch=(input,init={})=>{
    let url=typeof input==='string'?input:input.url;
    const options={...init};
    const headers=new Headers(options.headers||{});
    const apiBase=(window.MARIAGE_CONFIG?.apiUrl||'').replace(/\/$/,'');
    if(apiBase && url.startsWith(apiBase)){
      const auth=headers.get('Authorization');
      if(auth && auth.startsWith('Bearer ')){
        const token=auth.slice(7);
        headers.delete('Authorization');
        const target=new URL(url);
        if(!target.searchParams.has('token'))target.searchParams.set('token',token);
        url=target.toString();
      }
      if(options.body && !(options.body instanceof FormData)){
        headers.set('Content-Type','text/plain;charset=UTF-8');
      }
      options.mode='cors';
      options.cache='no-store';
    }
    options.headers=headers;
    return nativeFetch(url,options);
  };
})();
