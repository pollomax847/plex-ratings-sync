# Script qui lit la liste des playlists depuis un fichier
#!/bin/bash

PLAYLIST_FILE="${1:-$HOME/mes_playlists_deezer.txt}"

if [ ! -f "$PLAYLIST_FILE" ]; then
    echo "❌ Fichier de playlists non trouvé: $PLAYLIST_FILE"
    echo "Crée le fichier avec: touch ~/mes_playlists_deezer.txt"
    exit 1
fi

# Lire les playlists (ignorer les lignes vides et commentaires)
PLAYLISTS=($(grep -v "^#" "$PLAYLIST_FILE" | grep -v "^$" | tr -d r))

if [ ${#PLAYLISTS[@]} -eq 0 ]; then
    echo "❌ Aucune playlist trouvée dans $PLAYLIST_FILE"
    echo "Ajoute des URLs de playlists (une par ligne)"
    exit 1
fi

echo "🔍 Vérification de ${#PLAYLISTS[@]} playlists depuis $PLAYLIST_FILE..."
echo

for playlist_url in "${PLAYLISTS[@]}"; do
    # Utiliser le script existant pour chaque playlist
    ~/api_deezer_check.sh "$playlist_url"
    echo "---"
done

echo "✨ Toutes les playlists vérifiées à $(date)"
