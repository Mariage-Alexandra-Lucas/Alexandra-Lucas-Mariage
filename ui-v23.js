(() => {
  const guests = [
    'Alexandra','Alexandre','Boris','Chloé','Clémence','DJ','Éliane','Florian','Gérard','Joseph','Kevin','Khoil','Loris','Louise','Lucas','Lucas B','Marc','Marie-Jo','Marine','Maxime B','Maxime G','Maxime P','Méline','Michel A','Michel D','Michel T','Morgane','Nathalie','Nina','Nino','Quentin','Roman','Sarah','Sophie D','Sophie T','Sylvie'
  ].sort((a,b)=>a.localeCompare(b,'fr',{sensitivity:'base'}));

  const protectedUsers = new Set(['alexandra','lucas','dj']);
  const icons = {
    home: '⌂',
    table: '♢',
    photos: '▣',
    live: '◎',
    game: '🎲',
    profile: '◯'
  };

  loginView = function () {
    const options = guests.map(name => `<option value="${esc(name)}">${esc(name)}</option>`).join('');

    app.innerHTML = `<main class="shell login-shell">
      <section class="hero">
        <img class="hero-logo" src="${LOGO}" alt="Logo Alexandra et Lucas">
        <div class="date">29 août 2026</div>
        <h1>Mariage d’Alexandra & Lucas</h1>
      </section>
      <section class="card login-card refined-login">
        <form id="login">
          <label for="guest-select">Sélectionnez votre prénom</label>
          <div class="select-wrap">
            <select class="field guest-select" id="guest-select" name="name" required>
              <option value="" selected disabled>Choisir dans la liste</option>
              ${options}
            </select>
          </div>
          <div id="password-wrap"></div>
          <p id="error" class="error"></p>
          <button class="btn login-submit" disabled>Entrer</button>
        </form>
      </section>
    </main>`;

    const select = app.querySelector('#guest-select');
    const passwordWrap = app.querySelector('#password-wrap');
    const submit = app.querySelector('.login-submit');
    select.onchange = () => {
      const needsPassword = protectedUsers.has(norm(select.value));
      passwordWrap.innerHTML = needsPassword
        ? '<label for="guest-password">Mot de passe</label><input class="field" id="guest-password" type="password" name="password" autocomplete="current-password" required>'
        : '';
      submit.disabled = !select.value;
      if (needsPassword) setTimeout(() => app.querySelector('#guest-password')?.focus(), 50);
    };
    app.querySelector('#login').onsubmit = login;
  };

  shell = function () {
    const content = {home:homeView(),table:tableView(),photos:photosView(),live:storiesView(),game:gameView(),profile:profileView()}[state.tab];
    const navItems = [
      ['home','Accueil'],['table','Table'],['photos','Photos'],['live','Stories'],['game','Jeu'],['profile','Profil']
    ];
    app.innerHTML = `<main class="shell">
      <header class="topbar"><div><span>Bienvenue</span><strong>${esc(state.user.name)}</strong></div>${state.user.role==='superadmin'?`<button class="mode-toggle" id="mode">${state.adminView?'Vue invité':'Vue Super Admin'}</button>`:''}</header>
      ${content}
    </main>
    <nav class="nav refined-nav" aria-label="Navigation principale">
      ${navItems.map(([id,label]) => `<button data-tab="${id}" class="${state.tab===id?'active':''}" aria-label="${label}" ${state.tab===id?'aria-current="page"':''}><span class="nav-icon" aria-hidden="true">${icons[id]}</span><span class="nav-label">${label}</span></button>`).join('')}
    </nav>`;

    app.querySelectorAll('[data-tab]').forEach(b=>b.onclick=async()=>{state.tab=b.dataset.tab;if(state.tab==='table')await loadTable();else{await refresh();render()}});
    app.querySelector('#mode')?.addEventListener('click',toggleAdmin);
    app.querySelector('#logout')?.addEventListener('click',logout);
    app.querySelector('#photo-picker')?.addEventListener('change',e=>preload(e.target.files));
    app.querySelector('#deposit-photos')?.addEventListener('click',deposit);
    app.querySelector('#new-story')?.addEventListener('click',openStoryEditor);
    app.querySelectorAll('.media-card').forEach(c=>c.onclick=e=>{if(e.target.tagName==='BUTTON')return;openViewer(c.dataset.src,c.dataset.type,c.dataset.owner,c.dataset.comment)});
    app.querySelectorAll('.delete-story').forEach(b=>b.onclick=e=>{e.stopPropagation();deleteItem('stories',b.dataset.id)});
    app.querySelectorAll('.delete-photo').forEach(b=>b.onclick=e=>{e.stopPropagation();deleteItem('photos',b.dataset.id)});
  };

  render();
})();