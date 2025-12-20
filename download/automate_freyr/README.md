# Automate Freyr - Surveillance automatique des playlists
# ========================================================

Ce répertoire contient les scripts pour la surveillance automatique des playlists musicales.

## Fichiers :
- surveille_auto_deezer.sh    : Script principal de surveillance et téléchargement
- gestion_deezer_monitor.sh   : Gestionnaire de surveillance en arrière-plan (cron)
- mes_playlists_deezer.txt    : Liste des playlists à surveiller

## Utilisation :
- check-download-deezer       : Vérification manuelle
- deezer-start                : Démarrer surveillance auto (toutes les 4 heures)
- deezer-stop                 : Arrêter surveillance auto
- deezer-status               : Statut de la surveillance
- deezer-log                  : Voir les logs
- edit-playlists              : Éditer la liste des playlists
- list-playlists              : Lister les playlists actives

## Destination des téléchargements :
/mnt/mybook/Musiques

## Plateformes supportées :
- Deezer (avec détection de changements)
- Spotify (téléchargement systématique)

