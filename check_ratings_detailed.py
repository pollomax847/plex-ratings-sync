#!/usr/bin/env python3
import sqlite3
import subprocess
import tempfile
import shutil
import os

# Nouvelle bibliothèque audio
AUDIO_LIBRARY = "/media/paulceline/5E0C011B0C00EFB72/itunes/Music"

# Arrêter Plex temporairement
print("Arrêt de Plex...")
subprocess.run(["sudo", "snap", "stop", "plexmediaserver"], check=True)

# Copier la DB pour éviter les problèmes de permissions
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
temp_db = tempfile.mktemp(suffix='.db')
shutil.copy2(plex_db, temp_db)

print(f"Base copiée vers: {temp_db}")

try:
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Vérifier les fichiers avec rating 1 étoile qui peuvent être supprimés
    cursor.execute("""
        SELECT mi.title, mp.file, mi.metadata_type, mi.id as item_id
        FROM metadata_item_settings mis
        JOIN metadata_items mi ON mis.guid = mi.guid
        LEFT JOIN media_items media ON mi.id = media.metadata_item_id
        LEFT JOIN media_parts mp ON media.id = mp.media_item_id
        WHERE mis.rating = 1.0 AND mis.account_id = 1
        ORDER BY mi.title
    """)
    
    files_to_delete = cursor.fetchall()
    print(f"\n=== FICHIERS AVEC 1 ÉTOILE ({len(files_to_delete)} trouvés) ===")
    
    can_delete = []
    cannot_delete = []
    
    for title, file_path, metadata_type, item_id in files_to_delete:
        if file_path:
            # Vérifier si le fichier existe dans la nouvelle bibliothèque
            if file_path.startswith(AUDIO_LIBRARY):
                if os.path.exists(file_path):
                    can_delete.append((title, file_path, metadata_type))
                    print(f"✅ PEUT ÊTRE SUPPRIMÉ: {title} ({metadata_type})")
                    print(f"   Fichier: {file_path}")
                else:
                    cannot_delete.append((title, file_path, metadata_type, "fichier introuvable"))
                    print(f"❌ NE PEUT PAS ÊTRE SUPPRIMÉ: {title} ({metadata_type}) - fichier introuvable")
                    print(f"   Fichier: {file_path}")
            else:
                cannot_delete.append((title, file_path, metadata_type, "pas dans la bibliothèque"))
                print(f"⚠️ HORS BIBLIOTHÈQUE: {title} ({metadata_type})")
                print(f"   Fichier: {file_path}")
        else:
            cannot_delete.append((title, None, metadata_type, "pas de fichier associé"))
            print(f"❌ SANS FICHIER: {title} ({metadata_type})")
    
    print(f"\n=== RÉSUMÉ ===")
    print(f"📁 Bibliothèque vérifiée: {AUDIO_LIBRARY}")
    print(f"🗑️ Fichiers pouvant être supprimés: {len(can_delete)}")
    print(f"⚠️ Fichiers ne pouvant pas être supprimés: {len(cannot_delete)}")
    
    if can_delete:
        print(f"\nDétails des fichiers à supprimer:")
        for title, path, mtype in can_delete:
            print(f"  - {title} ({mtype}): {os.path.basename(path)}")
    
    if cannot_delete:
        print(f"\nDétails des fichiers non supprimables:")
        for title, path, mtype, reason in cannot_delete:
            print(f"  - {title} ({mtype}): {reason}")
    
    # Voir tous les ratings avec plus de détails
    cursor.execute("""
        SELECT mis.rating, mis.account_id, mi.title, mi.year, mi."index" as track_index, mi.metadata_type
        FROM metadata_item_settings mis
        JOIN metadata_items mi ON mis.guid = mi.guid
        WHERE mis.rating IS NOT NULL 
        ORDER BY mis.rating DESC, mi.title
        LIMIT 20
    """)
    
    print("\n=== DÉTAILS DES RATINGS (top 20) ===")
    for rating, account_id, title, year, track_index, metadata_type in cursor.fetchall():
        print(f"Rating {rating}, Account {account_id}: {title} ({year}) [track {track_index}] Type: {metadata_type}")
    
    # Vérifier si c'est peut-être une échelle différente (0-100 ou autre)
    cursor.execute("SELECT MIN(rating), MAX(rating), AVG(rating) FROM metadata_item_settings WHERE rating IS NOT NULL")
    min_r, max_r, avg_r = cursor.fetchone()
    print(f"\n=== STATISTIQUES ===")
    print(f"Min rating: {min_r}")
    print(f"Max rating: {max_r}")
    print(f"Avg rating: {avg_r:.2f}")
    
    # Vérifier la table metadata_item_settings
    cursor.execute("PRAGMA table_info(metadata_item_settings)")
    print(f"\n=== STRUCTURE TABLE metadata_item_settings ===")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]}) - {col[5] if len(col) > 5 else ''}")
    
    # Chercher spécifiquement "Under Grass and Clover" by "Children of Bodom"
    cursor.execute("""
        SELECT mi.title, mis.rating, mi.metadata_type, mp.file
        FROM metadata_item_settings mis
        JOIN metadata_items mi ON mis.guid = mi.guid
        LEFT JOIN media_items media ON mi.id = media.metadata_item_id
        LEFT JOIN media_parts mp ON media.id = mp.media_item_id
        WHERE mi.title LIKE ? AND mis.account_id = 1
    """, ('%Under Grass and Clover%',))
    
    specific_songs = cursor.fetchall()
    print(f"\n=== RECHERCHE 'Under Grass and Clover' ===")
    if specific_songs:
        for title, rating, metadata_type, file_path in specific_songs:
            print(f"Trouvé: {title} - Rating: {rating} - Type: {metadata_type}")
            if file_path:
                print(f"  Fichier: {file_path}")
            else:
                print("  Pas de fichier trouvé")
    else:
        print("Aucun résultat trouvé pour 'Under Grass and Clover'")
    
    conn.close()
    
except Exception as e:
    print(f"Erreur: {e}")
finally:
    # Nettoyer le fichier temporaire
    if os.path.exists(temp_db):
        os.remove(temp_db)
        print(f"Fichier temporaire supprimé: {temp_db}")
    
    # Redémarrer Plex
    print("Redémarrage de Plex...")
    subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True)
