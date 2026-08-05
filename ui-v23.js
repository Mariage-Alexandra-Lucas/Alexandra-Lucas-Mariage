(() => {
  const groups = [
    ['Table Guadeloupe', ['Kevin','Marie-Jo','Marc','Sylvie','Louise','Joseph','Boris','Méline','Morgane']],
    ['Table Île Maurice', ['Sophie D','Michel D','Éliane','Gérard','Michel T','Sophie T','Nino','Nathalie']],
    ['Table Maldives', ['Alexandra','Lucas','Maxime B','Roman','Marine','Clémence','Alexandre','Khoil','Michel A']],
    ['Table Mexique', ['Quentin','Maxime P','Lucas B','Chloé','Loris','Nina','Maxime G','Florian','Sarah']],
    ['Animation', ['DJ']]
  ];

  const protectedUsers = new Set(['alexandra','lucas','dj']);
  const icons = {
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5v8a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>',
    table: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="10" r="6"/><path d="M7 16.5 5 21m12-4.5 2 4.5M4 10h16"/></svg>',
    photos: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="6" width="18" height="14" rx="2"/><path d="m8 6 1.5-2h5L16 6"/><circle cx="12" cy="13" r="4"/></svg>',
    live: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="4"/><circle cx="12" cy="12" r="4"/><circle cx="17" cy="7" r="1"/></svg>',
    game: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="7" width="18" height="11" rx="4"/><path d="M8 10v5m-2.5-2.5h5M15.5 11h.01M18 14h.01"/></svg>',
    profile: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/></svg>'
  };

  loginView = function () {
    const options = groups.map(([label,names]) =>
      `<optgroup label="${esc(label)}">${names.map(name => `<option value="${esc(name)}">${esc(name)}</option>`).join('')}</optgroup>`
    ).join('');

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
      ${navItems.map(([id,label]) => `<button data-tab="${id}" class="${state.tab===id?'active':''}" aria-label="${label}" ${state.tab===id?'aria-current="page"':''}><span class="nav-icon">${icons[id]}</span><span class="nav-label">${label}</span></button>`).join('')}
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