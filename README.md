# Mariage d’Alexandra et Lucas

Application web progressive privée pour le mariage du 29 août 2026.

## V1

- Connexion par prénom sur liste d’invités
- Mot de passe obligatoire pour Alexandra et Lucas
- Rôles : invité, DJ, super administrateur
- Programme de la journée
- Plan de table verrouillé jusqu’au 29 août 2026 à 18:00, heure Europe/Paris
- Modules Photos, Live et Jeu préparés
- Application installable sur téléphone

## Test local

```bash
python -m http.server 8080
```

Ouvrir ensuite `http://localhost:8080`.

## Publication

GitHub Pages est publié depuis la branche `main`, dossier racine :

https://mariage-alexandra-lucas.github.io/Alexandra-Lucas-Mariage/

La passerelle NAS autorise cette nouvelle origine GitHub Pages.

## Version 2.4 — animations du mariage

- annonces et programme dynamique en direct ;
- informations pratiques avec itinéraires GPS ;
- livre d’or texte, photo, audio et vidéo avec album ZIP ;
- binômes entre les deux familles et équipes de quatre ;
- défis photos partagés entre tous les participants identifiés ;
- quatre mini-jeux déverrouillés définitivement par les QR codes des tables ;
- mode souvenirs après le mariage ;
- tableau de bord administrateur avec progression et état du NAS.

Les QR codes Guadeloupe, Île Maurice, Maldives et Mexique peuvent être scannés par tous les invités. Le déverrouillage est personnel, permanent et conservé par la passerelle sur le NAS.
