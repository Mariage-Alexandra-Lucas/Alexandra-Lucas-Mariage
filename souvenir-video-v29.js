(() => {
  const previousProfileView = profileView;

  profileView = function () {
    let html = previousProfileView();
    const isCouple = state.user?.role === 'superadmin' && ['Alexandra', 'Lucas'].includes(state.user?.name);
    const label = isCouple
      ? "Télécharger le livre d’or vidéo (.mp4)"
      : "Télécharger ma vidéo souvenir (.mp4)";
    const href = `${API}/api/v29/souvenir.mp4?token=${encodeURIComponent(state.token)}`;
    const replacement = `<a class="album-download" href="${href}" download>${label}</a><p class="video-memory-note">Sélection automatique des meilleures photos, sans séries trop similaires.</p>`;
    html = html.replace(
      /<a class="album-download" href="[^"]*\/api\/v24\/souvenirs\.zip\?token=[^"]*" download>Télécharger l’album ZIP<\/a>/,
      replacement
    );
    return html;
  };
})();
