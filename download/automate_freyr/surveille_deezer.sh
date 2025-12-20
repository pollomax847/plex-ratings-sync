# Script simple de surveillance Deezer
#!/bin/bash
PLAYLIST_URL="$1"
CACHE_FILE="$HOME/.deezer_playlist_cache"

# Fonction pour extraire les titres de la playlist
get_playlist_tracks() {
    freyr "$1" --dry-run 2>/dev/null | grep "Title:" | sed "s/.*Title: //" | sort
}

# Vérifier si le cache existe
if [ -f "$CACHE_FILE" ]; then
    OLD_TRACKS=$(cat "$CACHE_FILE")
else
    echo "📝 Première exécution - création du cache..."
    get_playlist_tracks "$PLAYLIST_URL" > "$CACHE_FILE"
    echo "✅ Cache créé. Relance le script pour détecter les changements."
    exit 0
fi

# Récupérer les nouveaux titres
NEW_TRACKS=$(get_playlist_tracks "$PLAYLIST_URL")

# Comparer
if [ "$NEW_TRACKS" != "$OLD_TRACKS" ]; then
    echo "🎵 NOUVEAUX TITRES DÉTECTÉS !"
    echo "Anciens titres: $(echo "$OLD_TRACKS" | wc -l)"
    echo "Nouveaux titres: $(echo "$NEW_TRACKS" | wc -l)"
    
    # Afficher les différences
    echo "Nouveaux titres ajoutés:"
    comm -13 <(echo "$OLD_TRACKS") <(echo "$NEW_TRACKS") | sed "s/^/  ➤ /"
    
    # Mettre à jour le cache
    echo "$NEW_TRACKS" > "$CACHE_FILE"
    
    # Demander si on télécharge
    read -p "Télécharger les nouveaux titres ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        freyr-music "$PLAYLIST_URL"
    fi
else
    echo "✅ Aucun changement détecté ($(echo "$NEW_TRACKS" | wc -l) titres)"
fi
