# Automatisation réelle (Docker + systemd)

Ce fichier est la source de vérité pour l'automatisation actuelle du repo.

## Ce qui tourne vraiment

Deux modes existent, mais il faut en utiliser un seul à la fois:

- mode Docker cron: [docker/crontab](docker/crontab)
- mode systemd: [systemd/plex-auto-playlists.timer](systemd/plex-auto-playlists.timer)

## Horaires actuels harmonisés

Playlists auto Plexamp:

- Docker cron: 1x/heure en journee (08h-22h, minute 30)
- systemd: tous les jours a 23:00

Autres jobs Docker (si service `cron` actif):

- sync ratings: 1x/heure en journee (minute 00)
- workflow quotidien 1 etoile / 2 etoiles: 1x/heure en journee (minute 15)
- export playlists M3U: 1x/heure en journee (minute 45)

## Mode auto journee (Docker)

Le cron Docker est configure en mode "1x par heure en journee" pour toutes les commandes.

Plage: 08:00 a 22:59.

- `00` de chaque heure: sync ratings
- `15` de chaque heure: workflow 1 etoile / 2 etoiles
- `30` de chaque heure: regeneration playlists
- `45` de chaque heure: export playlists M3U

Note: ce mode est plus intensif que le mode quotidien. Sur une grosse bibliotheque, surveille les logs et la charge.

## Pourquoi il y avait dimanche en Docker et 23h en systemd

Ce n'etait pas une limite technique. C'etait juste un ancien choix de planning different selon le mode d'execution.

Le comportement est maintenant aligne pour eviter la confusion.

## Une musique mise a jour en journee: quand apparait-elle en playlist auto

Par defaut:

- en Docker cron: au prochain passage horaire (minute 30, entre 08h et 22h)
- en systemd: au prochain run planifie de 23:00

Il n'y a pas de mode evenementiel natif (pas de watcher filesystem/webhook dans cette stack actuelle).

## Oui, Docker peut le faire immediatement

Tu peux lancer une regeneration instantanee a la demande.

Depuis la racine du projet:

```bash
docker compose run --rm scripts run ./playlists/generate_plexamp_playlists.sh --refresh
```

Ou, sans Docker:

```bash
./playlists/generate_plexamp_playlists.sh --refresh
```

## Regler une frequence plus agressive (optionnel)

Si tu veux quasi temps reel, tu peux augmenter la frequence cron (par exemple toutes les 15 min), mais attention a la charge Plex/DB:

```cron
*/15 * * * * cd /app && ./playlists/generate_plexamp_playlists.sh --refresh >> /data/logs/playlists.log 2>&1
```

## Bonnes pratiques

- Ne pas activer Docker cron et systemd en meme temps (sinon doublons d'execution).
- Utiliser `--refresh` pour nettoyer/regenerer completement.
- Consulter les logs:
   - Docker: `docker logs -f plex-scripts-cron`
   - systemd: `journalctl -u plex-auto-playlists.service -f`