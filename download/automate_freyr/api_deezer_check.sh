#!/bin/bash
# Surveillance avec API Deezer (plus rapide)
PLAYLIST_ID=$(echo "$1" | grep -o "[0-9]*$")
API_URL="https://api.deezer.com/playlist/$PLAYLIST_ID"
CACHE_FILE="$HOME/.deezer_api_cache_$PLAYLIST_ID"

# Installer jq si nécessaire
if ! command -v jq &> /dev/null; then
    echo "Installation de jq..."
    sudo apt update && sudo apt install -y jq
fi

# Fonction pour récupérer les titres via API
get_titles_api() {
    curl -s "$API_URL" | jq -r ".tracks.data[].title" 2>/dev/null | sort
}

# Première exécution
if [ ! -f "$CACHE_FILE" ]; then
    echo "📝 Création du cache initial..."
    get_titles_api > "$CACHE_FILE"
    echo "✅ Cache créé ($(wc -l < "$CACHE_FILE") titres)"
    exit 0
fi

# Vérification
OLD_COUNT=$(wc -l < "$CACHE_FILE")
NEW_TITLES=$(get_titles_api)
NEW_COUNT=$(echo "$NEW_TITLES" | wc -l)

if [ "$NEW_TITLES" != "$(cat "$CACHE_FILE")" ]; then
    echo "🎵 PLAYLIST MISE À JOUR !"
    echo "Avant: $OLD_COUNT titres"
    echo "Après: $NEW_COUNT titres"
    
    # Afficher les nouveaux titres
    echo "Nouveaux titres:"
    comm -13 "$CACHE_FILE" <(echo "$NEW_TITLES") | sed "s/^/  ➤ /"
    
    # Mettre à jour le cache
    echo "$NEW_TITLES" > "$CACHE_FILE"
else
    echo "✅ Aucun changement ($NEW_COUNT titres)"
fi
