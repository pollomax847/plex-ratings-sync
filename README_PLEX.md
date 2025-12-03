# Plex Ratings Sync

Script Python pour synchroniser les évaluations Plex avec le système de fichiers audio.

## Fonctionnalités

- **Suppression automatique** : Supprime les fichiers notés 1⭐ dans Plex
- **Identification audio** : Utilise songrec pour identifier les fichiers 2⭐
- **Support albums/artistes** : Peut supprimer des albums ou artistes entiers selon leur rating
- **Sauvegarde** : Option de sauvegarde avant suppression
- **Nettoyage automatique** : Supprime les anciens logs
- **Notifications** : Envoie des notifications desktop/email
- **Mode simulation** : Teste sans supprimer réellement

## Installation

1. **Prérequis** :

   ```bash
   # Installer Python 3.8+
   sudo apt install python3 python3-pip

   # Installer songrec (pour l'identification audio)
   pip install songrec

   # Installer les dépendances
   pip install -r requirements.txt
   ```

2. **Configuration** :
   - Le script trouve automatiquement la base Plex
   - Ou spécifiez manuellement : `--plex-db /chemin/vers/com.plexapp.plugins.library.db`

## Utilisation

### Mode simulation (recommandé d'abord)

```bash
python3 plex_ratings_sync.py --auto-find-db
```

### Suppression réelle

```bash
# Supprimer les fichiers 1⭐
python3 plex_ratings_sync.py --auto-find-db --delete

# Avec sauvegarde
python3 plex_ratings_sync.py --auto-find-db --delete --backup ./backup

# Supprimer aussi les albums 1⭐
python3 plex_ratings_sync.py --auto-find-db --delete --delete-albums

# Supprimer aussi les artistes 1⭐
python3 plex_ratings_sync.py --auto-find-db --delete --delete-artists
```

### Autres options

```bash
# Voir les statistiques des ratings
python3 plex_ratings_sync.py --auto-find-db --stats

# Nettoyer les logs de plus de 30 jours
python3 plex_ratings_sync.py --auto-find-db --cleanup-logs 30

# Mode verbeux
python3 plex_ratings_sync.py --auto-find-db --verbose
```

## Logique de traitement

- **1⭐** : Suppression du fichier
- **2⭐** : Identification avec songrec (conservation)
- **3-5⭐** : Conservation

## Sécurité

- **Toujours tester en simulation d'abord** (`--delete` pour la suppression réelle)
- **Utilisez `--backup`** pour sauvegarder avant suppression
- **Vérifiez les logs** après chaque exécution

## Notifications

Le script envoie automatiquement des notifications pour :

- Fichiers identifiés avec songrec
- Fichiers supprimés

## Structure des fichiers

```text
plex_ratings_sync.py          # Script principal
plex_notifications.sh         # Script de notifications
requirements.txt              # Dépendances Python
README_PLEX.md                # Cette documentation
```

## Dépannage

### Base Plex introuvable

```bash
# Chercher manuellement
find / -name "com.plexapp.plugins.library.db" 2>/dev/null

# Puis spécifier le chemin
python3 plex_ratings_sync.py --plex-db /chemin/trouvé/com.plexapp.plugins.library.db
```

### Erreur de permissions

```bash
# Donner les droits sur la base Plex
sudo chmod 644 /chemin/vers/com.plexapp.plugins.library.db
```

### Songrec ne fonctionne pas

```bash
# Vérifier l'installation
songrec --version

# Tester manuellement
songrec audio-file-to-recognized-song "fichier_audio.mp3"
```

## Licence

Ce projet est fourni tel quel, sans garantie. Utilisez à vos risques et périls.
