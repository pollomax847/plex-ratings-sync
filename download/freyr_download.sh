#!/bin/sh
echo "Collez l'URL de la playlist, album ou track Spotify (ou appuyez Ctrl+C pour annuler):"
read -r url
if [ -n "$url" ]; then
    freyr "$url"
else
    echo "Aucune URL fournie."
fi