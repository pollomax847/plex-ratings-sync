#!/bin/bash

# Script de maintenance mensuelle pour beets
# Exécuté automatiquement la nuit le 1er de chaque mois

LOG_FILE="/home/paulceline/beets_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== Début maintenance beets - $DATE ===" >> "$LOG_FILE"

# 1. Import des nouveaux fichiers
echo "Import automatique des nouveaux fichiers..." >> "$LOG_FILE"
/home/paulceline/.local/bin/beet import -A -q /home/paulceline/Musiques >> "$LOG_FILE" 2>&1

# 2. Import depuis mybook si disponible
if [ -d "/mnt/mybook/Musiques" ]; then
    echo "Import depuis mybook..." >> "$LOG_FILE"
    /home/paulceline/.local/bin/beet import -A -q /mnt/mybook/Musiques >> "$LOG_FILE" 2>&1
fi

# 3. Nettoyage des fichiers corrompus
echo "Vérification des fichiers corrompus..." >> "$LOG_FILE"
/home/paulceline/.local/bin/beet bad >> "$LOG_FILE" 2>&1

# 4. Mise à jour des métadonnées
echo "Mise à jour des métadonnées..." >> "$LOG_FILE"
/home/paulceline/.local/bin/beet update >> "$LOG_FILE" 2>&1

# 5. Nettoyage des références cassées (fichiers supprimés/corrompus)
echo "Nettoyage des références cassées..." >> "$LOG_FILE"
/home/paulceline/.local/bin/beet update -p >> "$LOG_FILE" 2>&1

# 5b. Recherche et gestion des doublons (entre home et mybook)
echo "Recherche des doublons entre tous les dossiers..." >> "$LOG_FILE"
/home/paulceline/.local/bin/beet duplicates >> "$LOG_FILE" 2>&1

# 5c. Affichage des doublons pour information (seulement les valides)
echo "Liste des doublons détectés (fichiers valides):" >> "$LOG_FILE"
/home/paulceline/.local/bin/beet duplicates -f '$artist - $title [$length]' 2>/dev/null | grep -v "could not get filesize" >> "$LOG_FILE"

# 5d. Recherche des compilations audio
echo "Recherche des compilations audio dans la bibliothèque:" >> "$LOG_FILE"
/home/paulceline/.local/bin/beet ls comp:1 -f '$albumartist - $album' >> "$LOG_FILE" 2>&1

# 6. Statistiques finales
echo "Statistiques après maintenance:" >> "$LOG_FILE"
/home/paulceline/.local/bin/beet stats >> "$LOG_FILE" 2>&1

echo "=== Fin maintenance beets - $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
