// Programme du mariage — ajout du rendez-vous photo de groupe et affichage complet.
if (typeof schedule !== 'undefined' && !schedule.some(item => item.time === '17h40' && item.title === 'Photo de groupe')) {
  schedule.splice(3, 0, {
    time: '17h40',
    title: 'Photo de groupe',
    address: 'Parc de la mairie de Bresson, 38320 Bresson',
    maps: 'https://www.google.com/maps/search/?api=1&query=Parc+de+la+mairie+de+Bresson+38320+Bresson'
  });
}

if (typeof homeView === 'function' && typeof schedule !== 'undefined') {
  const homeViewWithLimitedSchedule = homeView;
  homeView = function () {
    let html = homeViewWithLimitedSchedule();
    const extraItems = schedule.slice(4);
    if (!extraItems.length) return html;
    const extraHtml = extraItems.map(item => `<article class="practical"><div><strong>${esc(item.title)}</strong><p>${esc(item.time)} — ${esc(item.address)}</p></div><a href="${item.maps}" target="_blank">GPS</a></article>`).join('');
    return html.replace(/<\/section>\s*$/, `${extraHtml}</section>`);
  };
}

if (typeof render === 'function' && typeof state !== 'undefined' && state.user) render();
