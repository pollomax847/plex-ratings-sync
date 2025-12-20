# Utiliser watch (outil système existant)
# Vérifier toutes les 5 minutes
watch -n 300 "freyr 'https://www.deezer.com/fr/playlist/1995808222' --dry-run | grep -c 'Title:' && echo -e '\nTitres récents:' && freyr 'https://www.deezer.com/fr/playlist/1995808222' --dry-run | grep 'Title:' | tail -5"
