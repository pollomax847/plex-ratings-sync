# Plex Ratings Sync

Script Python pour synchroniser les évaluations Plex avec le système de fichiers audio.

## 🚀 Installation Rapide

### Option 1: Installation automatique (recommandée)

```bash
# Téléchargez le repo
git clone https://github.com/pollomax847/plex-ratings-sync.git
cd plex-ratings-sync

# Lancez l'installation automatique
./install.sh
```

### Option 2: Installation manuelle

```bash
# 1. Prérequis système
sudo apt update && sudo apt install python3 python3-pip  # Ubuntu/Debian
# ou
brew install python3  # macOS

# 2. Installation des dépendances
pip3 install songrec
pip3 install -r requirements.txt

# 3. Rendre les scripts exécutables
chmod +x plex_notifications.sh
```

## ✅ Vérification de l'installation

```bash
# Test rapide
python3 plex_ratings_sync.py --help

# Vérification des dépendances
songrec --version
python3 -c "import sqlite3, pathlib, subprocess; print('✅ Toutes les dépendances OK')"
```

## Fonctionnalités

- **Suppression automatique** : Supprime les fichiers notés 1⭐ dans Plex
- **Identification audio** : Utilise songrec pour identifier les fichiers 2⭐
- **Support albums/artistes** : Peut supprimer des albums ou artistes entiers selon leur rating
- **Sauvegarde** : Option de sauvegarde avant suppression
- **Nettoyage automatique** : Supprime les anciens logs
- **Notifications** : Envoie des notifications desktop/email
- **Mode simulation** : Teste sans supprimer réellement

## 🎯 Premiers Pas

### 1. Test de fonctionnement

```bash
# Mode simulation (recommandé pour commencer)
python3 plex_ratings_sync.py --auto-find-db
```

### 2. Voir les statistiques

```bash
# Afficher la répartition des ratings dans Plex
python3 plex_ratings_sync.py --auto-find-db --stats
```

### 3. Suppression réelle (avec précaution)

```bash
# Supprimer les fichiers 1⭐ avec sauvegarde
python3 plex_ratings_sync.py --auto-find-db --delete --backup ./sauvegarde_securisee
```

## Utilisation Avancée

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
