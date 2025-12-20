#!/bin/bash
# Script d'organisation musicale avec interface graphique YAD

# Fonction pour nettoyer les dossiers corrompus
clean_corrupted_dirs() {
    local src="$1"
    local trash_dir="$HOME/.local/share/Trash/files"
    mkdir -p "$trash_dir"
    echo "Déplacement des dossiers corrompus vers la corbeille ($trash_dir)..."
    
    find "$src" -type d -exec sh -c '
        if ! ls "$1" >/dev/null 2>&1; then
            trash_name="$(basename "$1")_$(date +%s)"
            echo "Dossier corrompu déplacé à la corbeille: $1 -> '"$2"'/$trash_name"
            mv "$1" "$2/$trash_name" 2>/dev/null || rm -rf "$1"
        fi
    ' _ {} "$trash_dir" \; 2>/dev/null
    
    echo "Nettoyage des dossiers terminé."
}

# Fonction pour nettoyer les fichiers audio corrompus ou trop courts
clean_audio_files() {
    local src="$1"
    echo "Nettoyage des fichiers audio corrompus ou < 1 minute dans $src..."
    
    find "$src" -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.opus" -o -iname "*.m4b" -o -iname "*.aac" \) 2>/dev/null | while read -r file; do
        # Vérifier si le fichier est lisible et obtenir la durée
        duration=$(ffprobe -v quiet -print_format json -show_format "$file" | jq -r '.format.duration // empty')
        
        if [ -z "$duration" ]; then
            echo "Fichier corrompu supprimé: $file"
            rm "$file"
        elif (( $(echo "$duration < 60" | bc -l) )); then
            echo "Fichier trop court ($duration s) supprimé: $file"
            rm "$file"
        fi
    done
    
    echo "Nettoyage des fichiers terminé."
}

# Fonction pour supprimer les dossiers vides
clean_empty_dirs() {
    local dir="$1"
    echo "Suppression des dossiers vides dans $dir..."
    find "$dir" -type d -empty -delete
    echo "Suppression des dossiers vides terminée."
}

# Fonction pour organiser avec Kid3
organize_music_kid3() {
    local src="$1"
    local dest="$2"
    local format="$3"
    local correct_tags="$4"
    
    # Nettoyer les dossiers corrompus d'abord
    clean_corrupted_dirs "$src"
    
    # Nettoyer les fichiers avant déplacement
    clean_audio_files "$src"
    
    echo "Déplacement des fichiers vers $dest..."
    mkdir -p "$dest"
    
    # Déplacer tous les fichiers audio
    find "$src" -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.wav" -o -iname "*.opus" -o -iname "*.m4b" -o -iname "*.aac" \) -exec mv {} "$dest" \; 2>/dev/null
    
    cd "$dest"
    
    if [ "$correct_tags" = "true" ]; then
        echo "Correction des tags avec MusicBrainz..."
        kid3-cli -c "musicbrainz" *.mp3 *.m4a *.flac *.ogg *.wav *.opus *.m4b *.aac 2>/dev/null
        echo "Correction terminée."
    fi
    
    echo "Organisation avec Kid3..."
    # Appliquer le format avec kid3-cli
    kid3-cli -c "fromtag '$format'" *.mp3 *.m4a *.flac *.ogg *.wav *.opus *.m4b *.aac 2>/dev/null
    
    # Supprimer les dossiers vides après organisation
    clean_empty_dirs "$dest"
    
    echo "Organisation terminée!"
}

# Mode test sans GUI
if [ "$1" = "--test" ]; then
    src="${2:-/media/paulceline/MUSIC}"
    dest="${3:-/tmp/test_organize}"
    format='%{albumartist}/%{album}/%{tracknumber}. %{title}'
    correct_tags="true"
    echo "Mode test: $src -> $dest avec format Picard_Simple, correction tags, nettoyage fichiers/dossiers et déplacement"
    organize_music_kid3 "$src" "$dest" "$format" "$correct_tags"
    echo "Test terminé. Vérifie $dest"
    exit 0
fi

# Interface YAD
result=$(yad --form \
    --title="Organisateur Musical avec Kid3" \
    --text="Choisissez les options d'organisation

Formats :
• Classique : Gestion avancée multi-disques/artistes
• Lidarr : AlbumArtist/Album/01. Titre  
• iTunes : Artist/Album/01 Titre" \
    --field="Dossier source:DIR" "" \
    --field="Dossier destination:DIR" "" \
    --field="Format d'organisation:CB" "Classique!Lidarr!iTunes" \
    --field="Corriger les tags avec MusicBrainz:CHK" \
    --button="Organiser:0" --button="Annuler:1")

if [ $? -eq 0 ]; then
    src=$(echo "$result" | cut -d'|' -f1)
    dest=$(echo "$result" | cut -d'|' -f2)
    format_choice=$(echo "$result" | cut -d'|' -f3)
    correct_tags=$(echo "$result" | cut -d'|' -f4)
    
    # Définir le format Kid3 selon le choix
    case "$format_choice" in
        "Classique")
            format='%{albumartist|artist}/%{albumartist?%{album}/}%{totaldiscs>1?%{totaldiscs>9?%{discnumber:02}:%{discnumber}}-}%{albumartist&tracknumber?%{tracknumber:02} }%{multiartist?%{artist} - }%{title}'
            ;;
        "Lidarr")
            format='%{albumartist}/%{album}/%{tracknumber}. %{title}'
            ;;
        "iTunes")
            format='%{artist}/%{album}/%{tracknumber:02} %{title}'
            ;;
        *)
            format='%{artist}/%{album}/%{tracknumber} %{title}'
            ;;
    esac
    
    if [ -d "$src" ] && [ -n "$dest" ]; then
        organize_music_kid3 "$src" "$dest" "$format" "$correct_tags"
        yad --info --text="Organisation terminée!\nFichiers organisés dans: $dest"
    else
        yad --error --text="Dossier source invalide ou destination vide"
    fi
fi