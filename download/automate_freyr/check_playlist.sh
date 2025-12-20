#!/bin/bash
# Script de surveillance de playlist Deezer
PLAYLIST_URL="$1"
LAST_CHECK_FILE="/tmp/deezer_playlist_$(basename "$PLAYLIST_URL" | sed s/[^a-zA-Z0-9]/_/g).last"

# Récupérer le contenu actuel de la playlist
CURRENT_CONTENT=$(freyr "$PLAYLIST_URL" --dry-run 2>/dev/null | grep -E "(Title|Album|Artist)" | sort)

if [ -f "$LAST_CHECK_FILE" ]; then
    LAST_CONTENT=$(cat "$LAST_CHECK_FILE")
    if [ "$CURRENT_CONTENT" != "$LAST_CONTENT" ]; then
        echo "🎵 Nouveaux titres détectés dans la playlist !"
        echo "$CURRENT_CONTENT" > "$LAST_CHECK_FILE"
        # Ici tu peux ajouter la commande de téléchargement
        # freyr-music "$PLAYLIST_URL"
    else
        echo "✅ Aucune modification détectée"
    fi
else
    echo "$CURRENT_CONTENT" > "$LAST_CHECK_FILE"
    echo "📝 Première vérification - baseline créée"
fi
