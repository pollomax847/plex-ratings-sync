#!/bin/bash
# Script de démonstration pour la suppression d'albums et artistes avec ratings

echo "🎵 Démonstration de la suppression d'albums et artistes avec ratings"
echo "=================================================================="

# Vérifier que le script existe
if [ ! -f "plex_ratings_sync.py" ]; then
    echo "❌ plex_ratings_sync.py non trouvé dans le répertoire actuel"
    exit 1
fi

echo ""
echo "📊 Statistiques actuelles des ratings :"
python3 plex_ratings_sync.py --auto-find-db --stats

echo ""
echo "🎭 Simulation de suppression des albums avec 1 étoile :"
python3 plex_ratings_sync.py --auto-find-db --delete-albums

echo ""
echo "🎭 Simulation de suppression des artistes avec 1 étoile :"
python3 plex_ratings_sync.py --auto-find-db --delete-artists

echo ""
echo "💡 Pour supprimer réellement, utilisez :"
echo "   python3 plex_ratings_sync.py --auto-find-db --delete --delete-albums --delete-artists --backup ./backup"
echo ""
echo "⚠️ ATTENTION : Cela supprimera TOUS les fichiers des albums/artistes avec 1 étoile !"