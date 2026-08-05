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

## Version 2.5 — quiz DJ

- 15 questions « Elle ou Lui » configurables en Vue Super Admin ;
- lancement, clôture et révélation question par question depuis le compte DJ ;
- une réponse commune par table, modifiable tant que la question est ouverte ;
- scores automatiques lors de la révélation ;
- classement en direct et corrections manuelles Super Admin ;
- remise à zéro complète avant le mariage.

## Version 2.6 — déroulement automatique

- jeux des binômes disponibles à partir de 15h00 ;
- équipes de quatre disponibles à partir de 15h45 ;
- jeux des quatre tables et QR codes bloqués jusqu’à 18h00 ;
- création manuelle et nommage des binômes en Super Admin ;
- association manuelle de deux binômes dans chaque équipe ;
- sélection multiple des participants avec menus de prénoms ;
- compte à rebours et étapes de la journée entièrement automatiques ;
- mini-film souvenir personnel disponible le dimanche ;
- correction des icônes de la barre de navigation.

### Correctif passerelle 2.6.1

La passerelle utilise l'heure officielle du PC Windows sans dépendre de la base
Python `tzdata`, absente de certains exécutables autonomes.

## Version 2.7 — consoles DJ et Super Admin

- le DJ accède uniquement à la page Animation Elle ou Lui ;
- lancement du jeu et des questions, clôture des votes et correction de la réponse ;
- scores des quatre tables suivis en direct ;
- console Super Admin distincte pour écrire les 15 questions et leurs réponses ;
- création manuelle des binômes nommés et des équipes de deux binômes corrigée.

### Version 2.7.1

- quatre jeux toujours déverrouillés pour Alexandra et Lucas en vue Super Admin ;
- QR codes agrandissables et imprimables individuellement depuis la configuration.
