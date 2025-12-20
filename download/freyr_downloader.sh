#!/bin/bash

# Script Freyr-JS Facile avec interface graphique
# Par Paul Celine - 2024

# Vérification des dépendances
check_deps() {
    if ! command -v yad &> /dev/null; then
        if ! command -v zenity &> /dev/null; then
            echo "Erreur : Installez YAD ou Zenity d'abord"
            echo "sudo apt install yad zenity"
            exit 1
        fi
        GUI="zenity"
    else
        GUI="yad"
    fi

    if ! command -v piactl &> /dev/null; then
        echo "Erreur : Private Internet Access (piactl) non installé"
        exit 1
    fi

    if ! command -v freyr &> /dev/null; then
        echo "Erreur : Freyr-JS non installé"
        exit 1
    fi
}

# Interface pour obtenir l'URL
get_url() {
    if [ "$GUI" = "yad" ]; then
        URL=$(yad --title="Freyr Downloader" --width=500 --center --entry \
            --text="Collez le lien Deezer/Spotify :" \
            --button="Annuler:1" --button="Télécharger:0")
        
        if [ $? -ne 0 ]; then
            exit 0
        fi
    else
        URL=$(zenity --entry --title="Freyr Downloader" \
            --text="Collez le lien Deezer/Spotify :" \
            --width=500 2>/dev/null)
        
        if [ $? -ne 0 ] || [ -z "$URL" ]; then
            exit 0
        fi
    fi
    echo "$URL"
}

# Téléchargement principal
download() {
    local url="$1"
    
    # Désactiver PIA
    piactl disconnect
    
    # Créer un dossier temporaire
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR" || exit 1
    
    # Lancer le téléchargement
    if [ "$GUI" = "yad" ]; then
        freyr "$url" -o "$TEMP_DIR" 2>&1 | yad --progress --title="Téléchargement" \
            --text="Téléchargement en cours..." --pulsate --auto-close
    else
        freyr "$url" -o "$TEMP_DIR" 2>&1 | zenity --progress --title="Téléchargement" \
            --text="Téléchargement en cours..." --pulsate --auto-close
    fi
    
    # Réactiver PIA
    piactl connect
    
    # Déplacer les fichiers
    mkdir -p "$HOME/Musiques"
    mv "$TEMP_DIR"/* "$HOME/Musiques/" 2>/dev/null
    rm -rf "$TEMP_DIR"
    
    # Message de fin
    if [ "$GUI" = "yad" ]; then
        yad --info --title="Terminé" --text="Téléchargement complet!\nLes fichiers sont dans ~/Musiques" --button=OK:0
    else
        zenity --info --title="Terminé" --text="Téléchargement complet!\nLes fichiers sont dans ~/Musiques"
    fi
}

# Main
check_deps
URL=$(get_url)
download "$URL"
