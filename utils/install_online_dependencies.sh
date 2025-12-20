#!/bin/bash
# Installation des dépendances pour la recherche en ligne

echo "🎵 Installation des dépendances pour recherche en ligne"
echo "======================================================"

echo "📦 Installation pyacoustid (AcoustID)..."
pip3 install pyacoustid

echo "📦 Installation pylast (Last.fm)..."
pip3 install pylast

echo "📦 Installation requests (API web)..."
pip3 install requests

echo ""
echo "✅ Installation terminée!"
echo ""
echo "📋 Dépendances installées:"
echo "  • pyacoustid - Reconnaissance audio (comme SongRec)"
echo "  • pylast - Métadonnées Last.fm"
echo "  • requests - Communication API"
echo ""
echo "🧪 Test des imports:"

python3 -c "
import sys
try:
    import acoustid
    print('✅ pyacoustid OK')
except ImportError:
    print('❌ pyacoustid manquant')

try:
    import pylast
    print('✅ pylast OK')
except ImportError:
    print('❌ pylast manquant')

try:
    import requests
    print('✅ requests OK')
except ImportError:
    print('❌ requests manquant')

print()
print('🎯 Vous pouvez maintenant utiliser les modes en ligne!')
"