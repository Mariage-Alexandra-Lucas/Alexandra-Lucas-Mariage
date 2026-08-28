// Programme du mariage — ajout du rendez-vous photo de groupe.
if (typeof schedule !== 'undefined' && !schedule.some(item => item.time === '17h40' && item.title === 'Photo de groupe')) {
  schedule.splice(3, 0, {
    time: '17h40',
    title: 'Photo de groupe',
    address: 'Parc de la mairie de Bresson, 38320 Bresson',
    maps: 'https://www.google.com/maps/search/?api=1&query=Parc+de+la+mairie+de+Bresson+38320+Bresson'
  });
  if (typeof render === 'function' && typeof state !== 'undefined' && state.user) render();
}
