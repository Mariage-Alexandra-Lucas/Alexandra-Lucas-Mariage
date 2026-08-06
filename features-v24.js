(() => {
  const VERSION = '2.4.0';
  const originalRefresh = refresh;
  state.v24 = {announcements:[],guestbook:[],program:{current:0},progress:{unlocked:[],completed:[],challengePoints:0},pair:null,dashboard:null,families:{},pairs:[]};

  const gameInfo = {
    'guadeloupe': {name:'Guadeloupe', icon:'🌺', title:'Qui est qui ?', description:'Retrouvez les invités correspondant aux anecdotes en discutant avec eux.', tasks:['A déjà dormi dans un aéroport','Connaît l’un des mariés depuis plus de 10 ans','A déjà vécu sur une île','A rencontré un marié pendant ses études']},
    'ile-maurice': {name:'Île Maurice', icon:'🐚', title:'Points communs improbables', description:'Découvrez des points communs entre les invités.', tasks:['Deux personnes nées le même mois','Deux personnes ayant visité le même pays','Trois personnes aimant le même plat','Deux personnes connaissant les mariés depuis plus de 10 ans']},
    'maldives': {name:'Maldives', icon:'🏝️', title:'Le puzzle des mariés', description:'Reconstituez ensemble l’histoire d’Alexandra et Lucas.', tasks:['Remettez trois souvenirs dans l’ordre','Associez une photo à son année','Retrouvez le lieu d’une anecdote','Choisissez l’anecdote vraie parmi trois propositions']},
    'mexique': {name:'Mexique', icon:'🌵', title:'La loterie photo', description:'Complétez votre grille de souvenirs photographiques.', tasks:['Photo avec les mariés','Photo avec trois générations','Photo avec une autre table','Photo avec quelqu’un rencontré aujourd’hui','Photo de toute une table','Photo avec le DJ']}
  };
  const practical = [
    ['Mairie de Claix','15h15 — Place Hector Berlioz, 38640 Claix','https://www.google.com/maps/search/?api=1&query=Place+Hector+Berlioz+38640+Claix'],
    ['Église Saint-Étienne','16h30 — 37 avenue du Maquis de l’Oisans, Le Pont-de-Claix','https://www.google.com/maps/search/?api=1&query=Eglise+Saint+Etienne+Le+Pont+de+Claix'],
    ['Dîner et soirée','18h00 — 2 rue Émile Chavant, 38320 Bresson','https://www.google.com/maps/search/?api=1&query=2+Rue+Emile+Chavant+38320+Bresson']
  ];
  const photoChallenges = ['Trois générations réunies','Une rencontre entre les deux familles','La plus belle photo de danse','Une photo avec les mariés','Le meilleur selfie de groupe'];
  const stages = ['Accueil et mairie','Cérémonie religieuse','Vin d’honneur et dîner','Soirée dansante'];

  const v24Media = path => path ? `${API}${path}${path.includes('?')?'&':'?'}token=${encodeURIComponent(state.token)}` : '';
  const fmt = value => value ? new Date(value).toLocaleString('fr-FR',{dateStyle:'short',timeStyle:'short'}) : '';
  const isAdmin = () => state.user?.role === 'superadmin' && state.adminView;
  const unlocked = id => state.v24.progress?.unlocked?.includes(id);
  const completed = id => state.v24.progress?.completed?.includes(id);
  const mediaTag = item => {
    if(!item.media) return '';
    const url=v24Media(item.media), type=item.mediaType||'';
    if(type.startsWith('video')) return `<video class="memory-media" src="${url}" controls playsinline></video>`;
    if(type.startsWith('audio')) return `<audio class="memory-audio" src="${url}" controls></audio>`;
    return `<img class="memory-media" src="${url}" loading="lazy" alt="Souvenir publié par ${esc(item.author)}">`;
  };

  refresh = async function(){
    await originalRefresh();
    if(!state.user) return;
    state.v24 = await api('/api/v24/state').catch(()=>state.v24);
    await processQrUnlock();
  };

  async function processQrUnlock(){
    if(!state.user) return;
    const params=new URLSearchParams(location.search), game=params.get('unlock'), code=params.get('code');
    if(!game||!code) return;
    try{
      const result=await api('/api/v24/unlock',{method:'POST',body:JSON.stringify({game,code})});
      state.v24.progress=result.progress; state.tab='game';
      history.replaceState({},'',location.pathname); toast(`Jeu ${gameInfo[game]?.name||game} déverrouillé définitivement !`);
    }catch(e){if(e.status===423)history.replaceState({},'',location.pathname);toast(e.message)}
  }

  function toast(text){document.querySelector('.toast')?.remove();document.body.insertAdjacentHTML('beforeend',`<div class="toast">${esc(text)}</div>`);setTimeout(()=>document.querySelector('.toast')?.remove(),3500)}

  homeView = function(){
    const stage=Number(state.v24.program?.current||0), souvenir=new Date()>new Date('2026-08-30T10:00:00+02:00');
    const announcements=(state.v24.announcements||[]).map(a=>`<article class="announcement"><span>En direct</span><p>${esc(a.text)}</p><small>${fmt(a.createdAt)}</small></article>`).join('');
    return `<section class="brand-card"><img class="home-logo official-logo" src="${LOGO}" alt="Logo officiel"><h2>Alexandra & Lucas</h2><p>${souvenir?'Merci d’avoir partagé cette merveilleuse journée avec nous.':'Nous sommes heureux de partager cette journée avec vous.'}</p></section>
    ${announcements?`<section class="card"><div class="section-title">Annonces</div>${announcements}</section>`:''}
    <section class="card"><div class="section-title">En ce moment</div><div class="current-stage"><b>${stage+1}</b><div><strong>${stages[stage]}</strong><p>Étape mise à jour par les mariés ${state.v24.program?.updatedAt?'à '+fmt(state.v24.program.updatedAt):''}.</p></div></div><div class="stage-track">${stages.map((s,i)=>`<span class="${i<=stage?'done':''}" title="${esc(s)}"></span>`).join('')}</div></section>
    <section class="card"><div class="section-title">Informations pratiques</div>${practical.map(([t,d,m])=>`<article class="practical"><div><strong>${t}</strong><p>${d}</p></div><a href="${m}" target="_blank">GPS</a></article>`).join('')}<p class="help-line">En cas de difficulté, rapprochez-vous d’Alexandra, Lucas ou d’un témoin.</p></section>`;
  };

  function gameCard(id){
    const g=gameInfo[id], isUnlocked=unlocked(id), isDone=completed(id);
    return `<article class="game-card ${isUnlocked?'unlocked':'locked-game'}"><div class="game-icon">${g.icon}</div><div class="game-copy"><small>${g.name}</small><h3>${g.title}</h3><p>${isUnlocked?g.description:'Trouvez et scannez le QR code de la table '+g.name+'.'}</p></div><button class="mini-btn ${isDone?'success':''}" ${isUnlocked?'data-open-game="'+id+'"':'disabled'}>${isDone?'Terminé ✓':isUnlocked?'Jouer':'🔒'}</button></article>`;
  }

  gameView = function(){
    const pair=state.v24.pair, partner=pair?.members?.find(n=>n!==state.user.name);
    return `<section class="card"><div class="section-title">Avant la mairie</div><h2>Retrouvez votre binôme</h2>${pair?`<div class="pair-box ${pair.validated?'validated':''}"><span>Votre binôme</span><strong>${esc(partner)}</strong><p>${pair.validated?'Défi validé pour vous deux !':'Retrouvez-vous et publiez une photo ensemble.'}</p>${pair.photo?`<img src="${v24Media(pair.photo)}">`:''}${!pair.validated?`<form id="pair-proof"><label class="upload-button">Prendre votre photo<input name="media" type="file" accept="image/*" capture="environment" required hidden></label><button class="btn">Valider pour le binôme</button></form>`:''}</div>`:`<p class="soft-alert">Les mariés préparent encore votre binôme entre les deux familles.</p>`}</section>
    <section class="card"><div class="section-title">Entre la mairie et l’église</div><h2>Formez votre équipe</h2><p>Réunissez deux binômes, trouvez un point commun ou réalisez une mission créative, puis publiez votre photo.</p><form id="team-proof"><input class="field" name="participants" placeholder="Prénoms séparés par une virgule" required><select class="field" name="text"><option>Trouvez un point commun surprenant</option><option>Formez les lettres A et L</option><option>Reproduisez une pochette d’album</option><option>Inventez un nom et une devise</option></select><label class="upload-button">Photo de l’équipe<input name="media" type="file" accept="image/*" capture="environment" required hidden></label><button class="btn">Valider pour toute l’équipe</button></form></section>
    <section class="card"><div class="section-title">Les jeux des quatre tables</div><p class="intro-copy">Chaque QR code peut être scanné par tous les invités. Une fois découvert, le jeu reste déverrouillé définitivement dans votre compte.</p><div class="games-grid">${Object.keys(gameInfo).map(gameCard).join('')}</div></section>
    <section class="card"><div class="section-title">Défis photos</div><div class="challenge-list">${photoChallenges.map((x,i)=>`<button data-challenge="${i}"><span>📸</span>${x}</button>`).join('')}</div><p class="score-line">${Number(state.v24.progress?.challengePoints||0)} défi(s) validé(s)</p></section>
    <section class="card locked"><h2>Quiz des mariés</h2><p>Le quiz collectif apparaîtra lorsque le DJ lancera l’animation.</p></section>`;
  };

  function guestbook(){
    const items=(state.v24.guestbook||[]).map(x=>`<article class="memory-card">${mediaTag(x)}<div><strong>${esc(x.author)}</strong><small>${fmt(x.createdAt)}</small><p>${esc(x.text)}</p></div></article>`).join('');
    return `<section class="card"><div class="section-title">Livre d’or numérique</div><form id="guestbook-form"><textarea class="field" name="text" rows="3" placeholder="Votre message pour Alexandra et Lucas"></textarea><label class="upload-button">Ajouter une photo, une vidéo ou un message vocal<input name="media" type="file" accept="image/*,video/*,audio/*" hidden></label><button class="btn">Publier dans le livre d’or</button></form></section><section class="card"><div class="section-title">Souvenirs</div><a class="album-download" href="${API}/api/v24/souvenirs.zip?token=${encodeURIComponent(state.token)}" download>Télécharger l’album ZIP</a><div class="memory-grid">${items||'<p class="empty">Le livre d’or vous attend.</p>'}</div></section>`;
  }

  function adminPanel(){
    if(!isAdmin())return '';
    const d=state.v24.dashboard||{}, families=state.v24.families||{};
    const users=['Alexandra','Alexandre','Boris','Chloé','Clémence','Éliane','Florian','Gérard','Joseph','Kevin','Khoil','Loris','Louise','Lucas','Lucas B','Marc','Marie-Jo','Marine','Maxime B','Maxime G','Maxime P','Méline','Michel A','Michel D','Michel T','Morgane','Nathalie','Nina','Nino','Quentin','Roman','Sarah','Sophie D','Sophie T','Sylvie'];
    return `<section class="card admin-v24"><div class="section-title">Tableau de bord</div><div class="admin-stats"><div><b>${d.connectedGuests||0}</b><span>invités actifs</span></div><div><b>${d.unlockedGames||0}</b><span>jeux débloqués</span></div><div><b>${d.guestbookMessages||0}</b><span>souvenirs</span></div><div><b>${d.validatedPairs||0}</b><span>binômes validés</span></div></div><p class="nas-state ${d.nasConnected?'ok':''}">● NAS ${d.nasConnected?'connecté':'indisponible'} — ${Math.round((d.storageBytes||0)/1048576)} Mo utilisés</p></section>
    <section class="card"><div class="section-title">Annonce en direct</div><form id="announcement-form"><textarea class="field" name="text" rows="2" maxlength="280" required placeholder="Votre annonce"></textarea><button class="btn">Publier l’annonce</button></form></section>
    <section class="card"><div class="section-title">Programme dynamique</div><form id="program-form"><select class="field" name="current">${stages.map((x,i)=>`<option value="${i}" ${Number(state.v24.program?.current)===i?'selected':''}>${x}</option>`).join('')}</select><button class="btn">Mettre à jour l’étape</button></form></section>
    <section class="card"><div class="section-title">Préparation des binômes</div><p>Indiquez le côté de chaque invité, puis générez les binômes Alexandra/Lucas.</p><div class="family-grid">${users.map(n=>`<label><span>${esc(n)}</span><select data-family="${esc(n)}"><option value="" ${!families[n]?'selected':''}>À définir</option><option value="alexandra" ${families[n]==='alexandra'?'selected':''}>Famille Alexandra</option><option value="lucas" ${families[n]==='lucas'?'selected':''}>Famille Lucas</option><option value="autre" ${families[n]==='autre'?'selected':''}>Autre</option></select></label>`).join('')}</div><button class="btn" id="generate-pairs">Générer les binômes</button></section>
    <section class="card"><div class="section-title">QR codes des tables</div><p>Cliquez sur un QR code pour l’agrandir et l’imprimer. Ils restent actifs et peuvent être scannés par tous les invités.</p><div class="qr-grid">${Object.keys(gameInfo).map(id=>`<button class="qr-card" type="button" data-open-qr="${id}"><img src="qr-${id}.svg" alt="QR code ${gameInfo[id].name}"><strong>${gameInfo[id].name}</strong><span>Agrandir et imprimer</span></button>`).join('')}</div></section>`;
  }

  profileView = function(){return `<section class="card profile"><img class="profile-logo" src="${LOGO}"><h2>${esc(state.user.name)}</h2><div class="profile-badges"><span>🎮 ${state.v24.progress?.unlocked?.length||0}/4 jeux</span><span>📸 ${state.v24.progress?.challengePoints||0} défis</span></div><button class="btn secondary" id="logout">Se déconnecter</button></section>${adminPanel()}${guestbook()}`}

  function standardGameForm(id,g){const saved=state.v24.progress?.gameAnswers?.[id]||[];return `<div class="task-checks answer-tasks">${g.tasks.map((x,i)=>`<div class="answer-task"><label><input type="checkbox" data-task="${i}" ${saved[i]?'checked':''}><span>${esc(x)}</span></label><div class="task-answer ${saved[i]?'visible':''}"><label>Votre réponse</label><textarea class="field" data-task-answer="${i}" rows="2" maxlength="300" placeholder="Écrivez votre réponse ici">${esc(saved[i]||'')}</textarea></div></div>`).join('')}</div>`}
  function puzzleForm(){return `<div class="wedding-puzzle">
    <section class="puzzle-block"><h3>1. Remettez les souvenirs dans l’ordre</h3><p>Attribuez une position de 1 à 3 à chaque souvenir.</p>${[['plongee','1ère plongée bouteille'],['tortues','1ère nage avec les tortues'],['requins','1ère nage avec les requins']].map(([key,label])=>`<label class="order-line"><span>${label}</span><select class="field" data-puzzle-order="${key}"><option value="">Position</option><option>1</option><option>2</option><option>3</option></select></label>`).join('')}</section>
    <section class="puzzle-block"><h3>2. Retrouvez l’année de chaque photo</h3><div class="puzzle-photos">${[['photo2021','souvenir-2021.jpeg'],['photo2024','souvenir-2024.jpeg'],['photo2015','souvenir-2015.jpeg']].map(([key,src])=>`<label><img src="${src}" alt="Souvenir d’Alexandra et Lucas"><select class="field" data-puzzle-year="${key}"><option value="">Choisir l’année</option><option>2015</option><option>2021</option><option>2024</option></select></label>`).join('')}</div></section>
    <section class="puzzle-block"><h3>3. Retrouvez le lieu</h3><blockquote>« Ça me fait une belle jambe »</blockquote><input class="field" data-puzzle-place maxlength="80" placeholder="Dans quel lieu ?"></section>
    <section class="puzzle-block"><h3>4. Laquelle de ces anecdotes est vraie ?</h3>${[['safari','On a déjà fait un safari'],['corail','On a déjà plongé sur une barrière de corail'],['basket','On a déjà fait un resto basket']].map(([value,label])=>`<label class="anecdote-line"><input type="radio" name="puzzle-anecdote" value="${value}"><span>${label}</span></label>`).join('')}</section>
  </div>`}
  function collectAnswers(modal,id){if(id==='maldives')return {order:['tortues','requins','plongee'].map(key=>modal.querySelector(`[data-puzzle-order="${key}"]`).value),years:Object.fromEntries([...modal.querySelectorAll('[data-puzzle-year]')].map(x=>[x.dataset.puzzleYear,x.value])),place:modal.querySelector('[data-puzzle-place]').value.trim(),anecdote:modal.querySelector('[name="puzzle-anecdote"]:checked')?.value||''};return [...modal.querySelectorAll('[data-task-answer]')].map(x=>x.value.trim())}
  function openGame(id){
    const g=gameInfo[id],done=completed(id);
    document.body.insertAdjacentHTML('beforeend',`<div class="game-modal"><section><button class="modal-close">×</button><div class="game-icon">${g.icon}</div><small>Jeu de la table ${g.name}</small><h2>${g.title}</h2><p>${g.description}</p>${id==='maldives'?puzzleForm():standardGameForm(id,g)}<button class="btn" id="finish-game" ${done?'disabled':''}>${done?'Jeu déjà terminé':'Valider les réponses'}</button></section></div>`);
    const modal=document.querySelector('.game-modal');modal.querySelector('.modal-close').onclick=()=>modal.remove();
    modal.querySelectorAll('[data-task]').forEach(box=>box.onchange=()=>{const answer=modal.querySelector(`[data-task-answer="${box.dataset.task}"]`),wrap=answer.closest('.task-answer');wrap.classList.toggle('visible',box.checked);answer.required=box.checked;if(!box.checked)answer.value=''});
    modal.querySelector('#finish-game').onclick=async()=>{const answers=collectAnswers(modal,id);if(id!=='maldives'&&(![...modal.querySelectorAll('[data-task]')].every(x=>x.checked)||answers.some(x=>!x))){toast('Cochez chaque mission et écrivez une réponse pour chacune.');return}try{const r=await api('/api/v24/game-progress',{method:'POST',body:JSON.stringify({game:id,answers})});state.v24.progress=r.progress;modal.remove();render();toast('Toutes les réponses sont correctes. Jeu terminé !')}catch(e){toast(e.message)}};
  }

  function openQr(id){
    const game=gameInfo[id];if(!game)return;
    document.body.insertAdjacentHTML('beforeend',`<div class="game-modal qr-modal"><section class="qr-print-sheet"><button class="modal-close" aria-label="Fermer">×</button><img src="${LOGO}" class="qr-print-logo" alt="Alexandra et Lucas"><p>Jeu de la table</p><h2>${esc(game.name)}</h2><img class="qr-large" src="qr-${id}.svg" alt="QR code ${esc(game.name)}"><p class="qr-instruction">Scannez ce QR code pour déverrouiller définitivement le jeu.</p><button class="btn" id="print-qr">Imprimer ce QR code</button></section></div>`);
    const modal=document.querySelector('.qr-modal');modal.querySelector('.modal-close').onclick=()=>modal.remove();modal.querySelector('#print-qr').onclick=()=>window.print();
  }

  async function sendMultipart(form,path,participantsTransform=false){
    const fd=new FormData(form);
    if(participantsTransform)fd.set('participants',String(fd.get('participants')||'').split(',').map(x=>x.trim()).filter(Boolean).join('|'));
    const button=form.querySelector('button');button.disabled=true;
    try{await api(path,{method:'POST',body:fd});await refresh();render();toast('Publication enregistrée pour tous les participants.')}catch(e){toast(e.message);button.disabled=false}
  }

  function bindV24(){
    app.querySelector('#pair-proof')?.addEventListener('submit',e=>{e.preventDefault();sendMultipart(e.target,'/api/v24/pair-proof')});
    app.querySelector('#team-proof')?.addEventListener('submit',e=>{e.preventDefault();sendMultipart(e.target,'/api/v24/team-proof',true)});
    app.querySelector('#guestbook-form')?.addEventListener('submit',e=>{e.preventDefault();sendMultipart(e.target,'/api/v24/guestbook')});
    app.querySelectorAll('[data-open-game]').forEach(b=>b.onclick=()=>openGame(b.dataset.openGame));
    app.querySelectorAll('[data-open-qr]').forEach(b=>b.onclick=()=>openQr(b.dataset.openQr));
    app.querySelectorAll('[data-challenge]').forEach(b=>b.onclick=()=>{const title=photoChallenges[Number(b.dataset.challenge)];const wrap=document.createElement('div');wrap.className='game-modal';wrap.innerHTML=`<section><button class="modal-close">×</button><h2>${esc(title)}</h2><form id="challenge-form"><input type="hidden" name="text" value="${esc(title)}"><input class="field" name="participants" placeholder="Prénoms présents, séparés par une virgule"><label class="upload-button">Prendre la photo<input name="media" type="file" accept="image/*" capture="environment" required hidden></label><button class="btn">Valider le défi</button></form></section>`;document.body.appendChild(wrap);wrap.querySelector('.modal-close').onclick=()=>wrap.remove();wrap.querySelector('form').onsubmit=e=>{e.preventDefault();sendMultipart(e.target,'/api/v24/challenge-proof',true);wrap.remove()}});
    app.querySelector('#announcement-form')?.addEventListener('submit',async e=>{e.preventDefault();await api('/api/v24/announcement',{method:'POST',body:JSON.stringify({text:new FormData(e.target).get('text')})});await refresh();render();toast('Annonce publiée')});
    app.querySelector('#program-form')?.addEventListener('submit',async e=>{e.preventDefault();await api('/api/v24/program',{method:'POST',body:JSON.stringify({current:Number(new FormData(e.target).get('current'))})});await refresh();render();toast('Programme mis à jour')});
    app.querySelectorAll('[data-family]').forEach(s=>s.onchange=async()=>{await api('/api/v24/family',{method:'POST',body:JSON.stringify({name:s.dataset.family,family:s.value})});state.v24.families[s.dataset.family]=s.value});
    app.querySelector('#generate-pairs')?.addEventListener('click',async()=>{await api('/api/v24/generate-pairs',{method:'POST',body:'{}'});await refresh();render();toast('Binômes générés')});
  }

  shell = function(){
    const content={home:homeView(),table:tableView(),photos:photosView(),live:storiesView(),game:gameView(),profile:profileView()}[state.tab];
    const nav=[['home','⌂','Accueil'],['table','♧','Table'],['photos','▣','Photos'],['live','◎','Stories'],['game','✦','Jeux'],['profile','♙','Profil']];
    app.innerHTML=`<main class="shell"><header class="topbar"><div><span>Bienvenue</span><strong>${esc(state.user.name)}</strong></div>${state.user.role==='superadmin'?`<button class="mode-toggle" id="mode">${state.adminView?'Vue invité':'Vue Super Admin'}</button>`:''}</header>${content}</main><nav class="nav refined-nav">${nav.map(([id,icon,label])=>`<button data-tab="${id}" class="${state.tab===id?'active':''}"><span class="nav-icon" aria-hidden="true">${icon}</span><span class="nav-label">${label}</span></button>`).join('')}</nav>`;
    app.querySelectorAll('[data-tab]').forEach(b=>b.onclick=async()=>{state.tab=b.dataset.tab;if(state.tab==='table')await loadTable();else{await refresh();render()}});app.querySelector('#mode')?.addEventListener('click',toggleAdmin);app.querySelector('#logout')?.addEventListener('click',logout);app.querySelector('#photo-picker')?.addEventListener('change',e=>preload(e.target.files));app.querySelector('#deposit-photos')?.addEventListener('click',deposit);app.querySelector('#new-story')?.addEventListener('click',openStoryEditor);app.querySelectorAll('.media-card').forEach(c=>c.onclick=e=>{if(e.target.tagName==='BUTTON')return;openViewer(c.dataset.src,c.dataset.type,c.dataset.owner,c.dataset.comment)});app.querySelectorAll('.delete-story').forEach(b=>b.onclick=e=>{e.stopPropagation();deleteItem('stories',b.dataset.id)});app.querySelectorAll('.delete-photo').forEach(b=>b.onclick=e=>{e.stopPropagation();deleteItem('photos',b.dataset.id)});bindV24();
  };

  if(state.user){refresh().finally(render)}
  window.MARIAGE_V24={version:VERSION,gameInfo};
})();
