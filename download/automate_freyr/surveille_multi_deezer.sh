# Script pour surveiller plusieurs playlists Deezer
#!/bin/bash

# Liste des playlists à surveiller (ajoute les tiennes ici)
PLAYLISTS=(
    "https://www.deezer.com/fr/playlist/1995808222"
    # "https://www.deezer.com/fr/playlist/XXXXXXX"
    # "https://www.deezer.com/fr/playlist/YYYYYYY"
)

# Fonction pour vérifier une playlist
check_playlist() {
    local url="$1"
    local playlist_id=$(echo "$url" | grep -o "[0-9]*$")
    local cache_file="$HOME/.deezer_multi_cache_$playlist_id"
    
    # Récupérer les titres via API
    local new_titles=$(curl -s "https://api.deezer.com/playlist/$playlist_id" | jq -r ".tracks.data[].title" 2>/dev/null | sort)
    
    if [ ! -f "$cache_file" ]; then
        echo "$new_titles" > "$cache_file"
        echo "📝 Cache créé pour playlist $playlist_id"
        return
    fi
    
    local old_titles=$(cat "$cache_file")
    
    if [ "$new_titles" != "$old_titles" ]; then
        local old_count=$(echo "$old_titles" | wc -l)
        local new_count=$(echo "$new_titles" | wc -l)
        
        echo "🎵 PLAYLIST $playlist_id MISE À JOUR !"
        echo "  Avant: $old_count titres"
        echo "  Après: $new_count titres"
        
        # Afficher les nouveaux titres
        echo "  Nouveaux titres:"
        comm -13 "$cache_file" <(echo "$new_titles") | sed "s/^/    ➤ /"
        
        # Mettre à jour le cache
        echo "$new_titles" > "$cache_file"
    else
        echo "✅ Playlist $playlist_id: Aucun changement ($(echo "$new_titles" | wc -l) titres)"
    fi
}

echo "🔍 Vérification de ${#PLAYLISTS[@]} playlists..."
echo

for playlist in "${PLAYLISTS[@]}"; do
    check_playlist "$playlist"
    echo
done

echo "✨ Vérification terminée à $(date)"
