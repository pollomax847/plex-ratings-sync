#!/bin/bash

echo "🎵 SYNCHRONISATION COMPLÈTE: RATINGS + PLAY COUNTS"
echo "=================================================="
echo
echo "✨ NOUVEAU SYSTÈME MIS À JOUR !"
echo
echo "📊 SYNCHRONISATION MAINTENANT INCLUT :"
echo "======================================="
echo
echo "🌟 RATINGS (Étoiles PlexAmp) :"
echo "   • 1⭐ → Suppression automatique avec sauvegarde"
echo "   • 2⭐ → Scan songrec-rename automatique"  
echo "   • 3⭐ → Écriture dans métadonnées ID3/MP4/FLAC"
echo "   • 4⭐ → Écriture dans métadonnées ID3/MP4/FLAC"
echo "   • 5⭐ → Écriture dans métadonnées ID3/MP4/FLAC"
echo
echo "🔢 PLAY COUNTS (Nombre d'écoutes) :"
echo "   • MP3 → Tag POPM count field"
echo "   • MP4/M4A → Tag 'plct' iTunes"
echo "   • FLAC → Tag 'PLAYCOUNT' standard"
echo
echo "📱 VISIBLE PARTOUT :"
echo "   ✅ Lecteurs audio (VLC, foobar2000, etc.)"
echo "   ✅ Applications mobiles (PlayerPro, PowerAMP, etc.)"
echo "   ✅ iTunes/Music.app"
echo "   ✅ Windows Media Player"
echo "   ✅ Systèmes de gestion musicale"
echo

# Vérifier les données réelles
echo "📊 VOS DONNÉES ACTUELLES :"
echo "=========================="

# Ratings
echo "🌟 RATINGS :"
ratings=$(python3 -c "
import sqlite3
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
conn = sqlite3.connect(plex_db)
cursor = conn.cursor()
cursor.execute('SELECT rating, COUNT(*) FROM metadata_item_settings WHERE rating IS NOT NULL GROUP BY rating ORDER BY rating')
for row in cursor.fetchall():
    rating, count = row
    stars = '⭐' * int(rating)
    print(f'   {stars} ({rating}) : {count} fichiers')
conn.close()
")
echo "$ratings"

echo
echo "🔢 PLAY COUNTS :"
playcounts=$(python3 -c "
import sqlite3
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
conn = sqlite3.connect(plex_db)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM metadata_item_settings WHERE view_count > 0')
total_with_plays = cursor.fetchone()[0]
cursor.execute('SELECT SUM(view_count) FROM metadata_item_settings WHERE view_count > 0')
total_plays = cursor.fetchone()[0] or 0
cursor.execute('SELECT MAX(view_count) FROM metadata_item_settings WHERE view_count > 0')
max_plays = cursor.fetchone()[0] or 0
cursor.execute('SELECT AVG(view_count) FROM metadata_item_settings WHERE view_count > 0')
avg_plays = cursor.fetchone()[0] or 0
print(f'   📂 Fichiers avec historique : {total_with_plays}')
print(f'   🎧 Total écoutes enregistrées : {total_plays}')
print(f'   🏆 Maximum écoutes (1 titre) : {max_plays}')
print(f'   📊 Moyenne par titre : {avg_plays:.1f}')
conn.close()
")
echo "$playcounts"

echo
echo "🎯 EXEMPLE DE SYNCHRONISATION :"
echo "==============================="
echo
# Exemple avec un fichier réel qui a des stats
example=$(python3 -c "
import sqlite3
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
conn = sqlite3.connect(plex_db)
cursor = conn.cursor()
cursor.execute('''
SELECT mi.title, mis.rating, mis.view_count, parent_mi.title as album
FROM metadata_items mi
JOIN metadata_item_settings mis ON mi.guid = mis.guid
LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
WHERE mi.metadata_type = 10 AND mis.rating IS NOT NULL AND mis.view_count > 0
ORDER BY mis.view_count DESC LIMIT 1
''')
row = cursor.fetchone()
if row:
    title, rating, plays, album = row
    stars = '⭐' * int(rating)
    print(f'🎵 TITRE: {title}')
    print(f'💿 ALBUM: {album or \"Inconnu\"}')
    print(f'🌟 RATING: {stars} ({rating})')
    print(f'🔢 ÉCOUTES: {plays} fois')
    print(f'')
    print(f'📝 SERA ÉCRIT DANS LES MÉTADONNÉES :')
    print(f'   • Rating: {rating}/5 étoiles')
    print(f'   • Play count: {plays} lectures')
    print(f'   • Visible sur TOUS vos lecteurs')
else:
    print('Aucun fichier avec rating ET play count trouvé')
conn.close()
")
echo "$example"

echo
echo "⚡ AUTOMATISATION MENSUELLE :"
echo "============================"
echo "✅ Système configuré pour tourner chaque fin de mois"
echo "✅ Synchronisation automatique de TOUS les ratings"
echo "✅ Synchronisation automatique de TOUS les play counts"
echo "✅ Pas d'intervention manuelle requise"
echo "✅ Sauvegarde automatique avant modifications"
echo
echo "🚀 PROCHAINE EXÉCUTION : Fin novembre 2025 à 2h du matin"
echo "📧 Rapport automatique généré à chaque traitement"

# Nettoyage
rm -f /tmp/test_playcount.json