#!/bin/bash
# Script avec destination personnalisée /mnt/mybook/itunes/Music

PLAYLIST_FILE="$HOME/bin/audio/automate_freyr/mes_playlists_deezer.txt"

if [ ! -f "$PLAYLIST_FILE" ]; then
    echo "❌ Fichier de playlists non trouvé"
    exit 1
fi

# Traiter toutes les URLs (Deezer et Spotify)
PLAYLISTS=($(grep -v "^#" "$PLAYLIST_FILE" | grep -v "^$" | tr -d '\r'))

echo "🔍 Vérification de ${#PLAYLISTS[@]} playlists avec téléchargement automatique..."
echo "📁 Destination: /mnt/mybook/itunes/Music (puis sync vers USB /media/paulceline/MUSIC si connectée)"
echo

DOWNLOADS=0

for playlist_url in "${PLAYLISTS[@]}"; do
    echo "🔍 Traitement: $playlist_url"
    
    if [[ "$playlist_url" == *"deezer.com"* ]]; then
        # === TRAITEMENT DEEZER ===
        platform="Deezer"
        playlist_id=$(echo "$playlist_url" | grep -o "[0-9]*$")
        cache_file="$HOME/.deezer_cache_$playlist_id"
        
        echo "🎵 [$platform] Vérification playlist $playlist_id..."
        
        new_titles=$(curl -s "https://api.deezer.com/playlist/$playlist_id" | jq -r ".tracks.data[].title" 2>/dev/null | sort)
        
        if [ -z "$new_titles" ]; then
            echo "❌ [$platform] Impossible de récupérer les données"
            continue
        fi
        
        if [ ! -f "$cache_file" ]; then
            echo "$new_titles" > "$cache_file"
            echo "📝 [$platform] Cache créé - Téléchargement initial"
            download_needed=true
        else
            old_titles=$(cat "$cache_file")
            
            if [ "$new_titles" != "$old_titles" ]; then
                echo "🎵 [$platform] NOUVEAUX TITRES détectés !"
                download_needed=true
                echo "$new_titles" > "$cache_file"
            else
                echo "✅ [$platform] Aucun changement"
                download_needed=false
            fi
        fi
        
    elif [[ "$playlist_url" == *"spotify.com"* ]]; then
        # === TRAITEMENT SPOTIFY ===
        platform="Spotify"
        playlist_id=$(echo "$playlist_url" | grep -o "[^/?]*$" | sed 's/\?.*//')
        
        echo "🎵 [$platform] Vérification playlist $playlist_id..."
        
        # Pour Spotify, on tente toujours le téléchargement
        # Si ça échoue, c'est que la playlist n'est pas accessible
        echo "📝 [$platform] Téléchargement systématique (test d'accessibilité)"
        download_needed=true
        
    else
        echo "❌ Plateforme non supportée: $playlist_url"
        continue
    fi
    
    # Téléchargement si nécessaire
    if [ "$download_needed" = true ]; then
        mkdir -p /mnt/mybook/itunes/Music
        echo "📥 [$platform] Téléchargement en cours vers /mnt/mybook/itunes/Music..."
        if /usr/local/bin/freyr -d /mnt/mybook/itunes/Music "$playlist_url" 2>/dev/null; then
            echo "✅ [$platform] Téléchargement réussi !"
            DOWNLOADS=$((DOWNLOADS + 1))
            
            # Sync vers USB si connectée
            if [ -d /media/paulceline/MUSIC ]; then
                echo "🔄 [$platform] Synchronisation vers USB /media/paulceline/MUSIC..."
                rsync -av /mnt/mybook/itunes/Music/ /media/paulceline/MUSIC/
                echo "✅ [$platform] Sync USB terminée"
            else
                echo "⚠️ [$platform] USB non connectée, fichiers gardés localement"
            fi
        else
            echo "❌ [$platform] Erreur de téléchargement (playlist inaccessible?)"
        fi
    fi
    
    echo
done

if [ $DOWNLOADS -gt 0 ]; then
    echo "🎉 $DOWNLOADS playlist(s) téléchargée(s) dans /mnt/mybook/itunes/Music et synchronisée(s) vers USB /media/paulceline/MUSIC si connectée !"
else
    echo "✨ Rien de nouveau"
fi
