(() => {
  const previousShell=shell,legacyRefresh=refresh,rawApi=api;
  const resources=new Map();
  let qrHandled=false;
  const freshFor=8000;

  function invalidate(){resources.clear()}
  api=async function(path,options={}){
    const method=String(options.method||'GET').toUpperCase();
    if(method!=='GET')invalidate();
    return rawApi(path,options);
  };

  async function resource(key,loader,force=false,ttl=freshFor){
    const current=resources.get(key),time=Date.now();
    if(!force&&current?.promise)return current.promise;
    if(!force&&current&&time-current.at<ttl)return;
    const promise=Promise.resolve().then(loader).finally(()=>{const saved=resources.get(key);if(saved?.promise===promise)resources.set(key,{at:Date.now()})});
    resources.set(key,{at:current?.at||0,promise});
    return promise;
  }
  const loadV24=force=>resource('v24',async()=>{state.v24=await api('/api/v24/state')},force);
  const loadQuiz=force=>resource('quiz',async()=>{state.quiz=await api('/api/v25/quiz')},force,2500);
  const loadEvents=force=>resource('events',async()=>{const value=await api('/api/v26/events');window.MARIAGE_EVENTS_V26?.apply?.(value)},force,5000);
  const loadStories=force=>resource('stories',async()=>{state.stories=await api('/api/stories')},force);
  const loadPhotos=force=>{const scope=state.user?.role==='superadmin'&&state.adminView?'all':'mine';return resource(`photos:${scope}`,async()=>{state.photos=await api(`/api/photos?scope=${scope}`)},force)};

  refresh=async function(force=false){
    if(!state.user)return;
    if(!qrHandled&&new URLSearchParams(location.search).has('unlock')){qrHandled=true;invalidate();return legacyRefresh()}
    if(state.user.role==='dj')return Promise.allSettled([loadQuiz(force)]);
    const jobs={
      home:[loadV24,loadEvents],
      photos:[loadPhotos],
      live:[loadStories],
      game:[loadV24,loadQuiz,loadEvents],
      profile:[loadPhotos,loadV24,loadQuiz,loadEvents],
      table:[loadEvents]
    }[state.tab]||[loadV24,loadEvents];
    return Promise.allSettled(jobs.map(job=>job(force)));
  };

  async function navigate(tab){
    if(state.tab===tab)return;
    state.tab=tab;render();document.body.classList.add('background-sync');
    try{if(tab==='table')await loadTable();else await refresh()}finally{if(state.tab===tab&&tab!=='table')render();document.body.classList.remove('background-sync')}
  }
  shell=function(){
    previousShell();
    app.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>navigate(button.dataset.tab));
  };
  window.MARIAGE_PERFORMANCE={invalidate,refresh};
  if(state.user){document.body.classList.add('background-sync');refresh(true).finally(()=>{render();document.body.classList.remove('background-sync')})}
})();
