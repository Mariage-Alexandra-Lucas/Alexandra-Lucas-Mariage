const app=document.querySelector('#app');
const ADMIN_PASSWORD='AL-290826';
const UNLOCK_AT=new Date('2026-08-29T18:00:00+02:00').getTime();
const tables={
  'Guadeloupe':['Kevin','Marie-Jo','Marc','Sylvie','Louise','Joseph','Boris','Méline','Morgane'],
  'Île Maurice':['Sophie D','Michel D','Éliane','Gérard','Michel T','Sophie T','Nino','Nathalie'],
  'Maldives':['Alexandra','Lucas','Maxime B','Roman','Marine','Clémence','Alexandre','Khoil','Michel A'],
  'Mexique':['Quentin','Maxime P','Lucas B','Chloé','Loris','Nina','Maxime G','Florian','Sarah']
};
const guests=Object.entries(tables).flatMap(([table,names])=>names.map(name=>({name,table,role:['Alexandra','Lucas'].includes(name)?'superadmin':'guest'}))).concat([{name:'DJ',table:null,role:'dj'}]);
const schedule=[
  ['13:30','Accueil des invités','Mairie de Claix'],
  ['14:00','Cérémonie civile','Mairie de Claix'],
  ['À préciser','Cérémonie religieuse','Église Saint-Étienne'],
  ['18:00','Découverte du plan de table','Lieu de réception'],
  ['Soirée','Dîner, jeu et soirée dansante','Lieu de réception']
];
let state={user:JSON.parse(localStorage.getItem('wedding-user')||'null'),tab:'home',serverNow:Date.now()};
const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
async function syncServerTime(){try{const r=await fetch(location.href,{method:'HEAD',cache:'no-store'});const d=r.headers.get('date');if(d)state.serverNow=new Date(d).getTime()}catch(e){} }
function saveUser(u){state.user=u;localStorage.setItem('wedding-user',JSON.stringify(u));render()}
function login(e){e.preventDefault();const fd=new FormData(e.target),name=String(fd.get('name')||'');const found=guests.find(g=>norm(g.name)===norm(name));const error=document.querySelector('#error');if(!found){error.textContent='Prénom non reconnu. Vérifiez l’orthographe.';return}if(found.role==='superadmin'&&fd.get('password')!==ADMIN_PASSWORD){error.textContent='Mot de passe Super Admin incorrect.';return}saveUser(found)}
function logout(){localStorage.removeItem('wedding-user');state.user=null;state.tab='home';render()}
function loginView(){app.innerHTML=`<main class="shell"><section class="hero"><div class="eyebrow">29 août 2026</div><h1>Alexandra & Lucas</h1><p class="subtitle">Bienvenue dans l’application privée de notre mariage.</p></section><section class="card"><form id="login"><label>Votre prénom</label><input class="field" name="name" autocomplete="given-name" required placeholder="Ex. Kevin"><div id="password-wrap"></div><p id="error" class="error"></p><button class="btn">Entrer</button></form><p class="small">Alexandra et Lucas doivent saisir leur mot de passe administrateur.</p></section></main>`;const input=app.querySelector('[name=name]');input.addEventListener('input',()=>{const admin=['alexandra','lucas'].includes(norm(input.value));document.querySelector('#password-wrap').innerHTML=admin?'<label>Mot de passe Super Admin</label><input class="field" name="password" type="password" required placeholder="Mot de passe">':''});app.querySelector('#login').addEventListener('submit',login)}
function homeView(){return `<section class="card"><div class="eyebrow">Notre journée</div><div class="timeline">${schedule.map(x=>`<div class="event"><div class="time">${x[0]}</div><div><strong>${x[1]}</strong><div class="small">${x[2]}</div></div></div>`).join('')}</div></section>`}
function tableView(){const u=state.user,unlocked=state.serverNow>=UNLOCK_AT||u.role==='superadmin';if(!unlocked)return `<section class="card locked"><div class="eyebrow">Encore un peu de patience</div><h2>Le plan de table sera dévoilé</h2><p class="table-name">29 août · 18h00</p><p class="small">Le déverrouillage dépend de l’heure du serveur, jamais de celle du téléphone.</p></section>`;if(u.role==='dj')return `<section class="card locked"><h2>Compte DJ</h2><p>Le DJ n’est associé à aucune table.</p></section>`;const names=tables[u.table]||[];return `<section class="card"><div class="eyebrow">Votre table</div><div class="table-name">${u.table}</div><div class="people">${names.map(n=>`<span class="person">${n}</span>`).join('')}</div></section>${u.role==='superadmin'?`<section class="card"><h3>Vue Super Admin</h3>${Object.entries(tables).map(([t,ns])=>`<p><strong>${t}</strong> — ${ns.join(', ')}</p>`).join('')}</section>`:''}`}
function placeholder(title,text){return `<section class="card module-placeholder"><div class="eyebrow">V1</div><h2>${title}</h2><p class="subtitle">${text}</p></section>`}
function adminPanel(){if(!['superadmin','dj'].includes(state.user.role))return '';return `<section class="card"><div class="eyebrow">${state.user.role==='dj'?'Interface DJ':'Super administration'}</div><h2>Commandes du jeu</h2><div class="admin-grid"><button class="btn">Lancer le jeu</button><button class="btn secondary">Question suivante</button></div><p class="small">Les commandes temps réel seront activées avec la passerelle sécurisée.</p></section>`}
function shell(){const content={home:homeView(),table:tableView(),photos:placeholder('Mes photos','Retrouvez ici uniquement les photos que vous avez envoyées au NAS.'),live:placeholder('Live','Prenez une photo, ajoutez un commentaire et publiez-la volontairement dans le fil partagé.'),game:adminPanel()+placeholder('Jeu des mariés','Le jeu s’ouvrira automatiquement quand le DJ le lancera.')}[state.tab];app.innerHTML=`<main class="shell"><header class="topbar"><div><div class="small">Bienvenue</div><div class="welcome">${state.user.name}</div></div><div><span class="pill">${state.user.role==='superadmin'?'Super Admin':state.user.role==='dj'?'DJ':state.user.table}</span></div></header>${content}<button class="btn secondary" id="logout">Se déconnecter</button></main><nav class="nav">${[['home','Accueil'],['table','Table'],['photos','Photos'],['live','Live'],['game','Jeu']].map(([id,label])=>`<button data-tab="${id}" class="${state.tab===id?'active':''}">${label}</button>`).join('')}</nav>`;app.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;render()});app.querySelector('#logout').onclick=logout}
function render(){state.user? shell():loginView()}
if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js');
syncServerTime().finally(render);
