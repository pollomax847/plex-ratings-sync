#!/bin/bash
# Script de démonstration pour synchroniser les ratings Plex vers les métadonnées audio

echo "🎵 SYNCHRONISATION DES RATINGS PLEX VERS LES FICHIERS AUDIO"
echo "=========================================================="
echo ""

echo "📊 Étape 1: Vérification des ratings dans Plex..."
python3 plex_rating_sync_complete.py --auto-find-db --stats

echo ""
echo "🔍 Étape 2: Simulation de la synchronisation (recommandé d'abord)..."
python3 plex_rating_sync_complete.py --auto-find-db --dry-run

echo ""
echo "⚠️  ATTENTION: La synchronisation réelle va modifier les métadonnées des fichiers!"
echo "   Assurez-vous d'avoir une sauvegarde de vos fichiers audio."
echo ""
read -p "Voulez-vous procéder à la synchronisation réelle ? (o/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "🎵 Synchronisation en cours..."
    python3 plex_rating_sync_complete.py --auto-find-db

    echo ""
    echo "✅ Synchronisation terminée!"
    echo "   Les étoiles que vous avez mises dans Plex sont maintenant"
    echo "   visibles dans les métadonnées de vos fichiers audio."
    echo "   Vous pouvez les voir dans vos lecteurs musicaux !"
else
    echo "⏹️ Synchronisation annulée."
fi