#!/bin/bash
# Script de surveillance avec deemix pour /mnt/mybook/itunes/Music

PLAYLIST_FILE="$HOME/bin/audio/automate_freyr/mes_playlists_deezer.txt"
DEEMIX_CMD="/home/paulceline/.local/bin/deemix"
DEST_DIR="/mnt/mybook/itunes/Music"

if [ ! -f "$PLAYLIST_FILE" ]; then
    echo "❌ Fichier de playlists non trouvé"
    exit 1
fi

# Traiter toutes les URLs Deezer
PLAYLISTS=($(grep -v "^#" "$PLAYLIST_FILE" | grep "deezer.com" | grep -v "^$" | tr -d '\r'))

echo "🔍 Vérification de ${#PLAYLISTS[@]} playlists Deezer avec deemix..."
echo "📁 Destination: $DEST_DIR"
echo

DOWNLOADS=0

for playlist_url in "${PLAYLISTS[@]}"; do
    echo "🔍 Traitement: $playlist_url"
    
    playlist_id=$(echo "$playlist_url" | grep -o "[0-9]*$")
    cache_file="$HOME/.deemix_cache_$playlist_id"
    
    echo "🎵 Vérification playlist $playlist_id..."
    
    new_titles=$(curl -s "https://api.deezer.com/playlist/$playlist_id" | jq -r ".tracks.data[].title" 2>/dev/null | sort)
    
    if [ -z "$new_titles" ]; then
        echo "❌ Impossible de récupérer les données"
        continue
    fi
    
    if [ ! -f "$cache_file" ]; then
        echo "$new_titles" > "$cache_file"
        echo "📝 Cache créé - Téléchargement initial"
        download_needed=true
    else
        old_titles=$(cat "$cache_file")
        
        if [ "$new_titles" != "$old_titles" ]; then
            echo "🎵 NOUVEAUX TITRES détectés !"
            download_needed=true
            echo "$new_titles" > "$cache_file"
        else
            echo "✅ Aucun changement"
            download_needed=false
        fi
    fi
    
    # Téléchargement si nécessaire
    if [ "$download_needed" = true ]; then
        mkdir -p "$DEST_DIR"
        echo "📥 Téléchargement en cours vers $DEST_DIR..."
        if $DEEMIX_CMD -p "$DEST_DIR" "$playlist_url"; then
            echo "✅ Téléchargement réussi !"
            DOWNLOADS=$((DOWNLOADS + 1))
            
            # Sync vers USB si connectée
            if [ -d /media/paulceline/MUSIC ]; then
                echo "🔄 Synchronisation vers USB /media/paulceline/MUSIC..."
                rsync -av "$DEST_DIR/" /media/paulceline/MUSIC/
                echo "✅ Sync USB terminée"
            else
                echo "⚠️ USB non connectée, fichiers gardés localement"
            fi
        else
            echo "❌ Erreur de téléchargement"
        fi
    fi
    
    echo
done

if [ $DOWNLOADS -gt 0 ]; then
    echo "🎉 $DOWNLOADS playlist(s) téléchargée(s) dans $DEST_DIR !"
else
    echo "✨ Rien de nouveau"
fi
