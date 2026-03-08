#!/usr/bin/env python3
"""
Script temporaire pour supprimer manuellement les fichiers 1⭐ (rating 2.0)
"""
import sqlite3
import os
import shutil
import tempfile
import subprocess
from pathlib import Path

# Configuration
BACKUP_DIR = "/home/paulceline/backup_1star_manual"
AUDIO_LIBRARY = "/home/paulceline/Musiques"

# Créer le répertoire de sauvegarde
os.makedirs(BACKUP_DIR, exist_ok=True)

# Copier la DB Plex
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
temp_db = tempfile.mktemp(suffix='.db')
shutil.copy2(plex_db, temp_db)

print("🔍 Analyse de la base de données Plex...")

try:
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Trouver tous les fichiers avec rating 2.0 (1⭐)
    cursor.execute("""
        SELECT mi.title, mp.file, mi.metadata_type, mi.id as item_id
        FROM metadata_item_settings mis
        JOIN metadata_items mi ON mis.guid = mi.guid
        LEFT JOIN media_items media ON mi.id = media.metadata_item_id
        LEFT JOIN media_parts mp ON media.id = mp.media_item_id
        WHERE mis.rating = 2.0 AND mis.account_id = 1
        ORDER BY mi.title
    """)

    files_to_delete = cursor.fetchall()
    print(f"📊 Trouvé {len(files_to_delete)} fichiers avec rating 2.0 (1⭐)")

    deleted_count = 0
    for title, file_path, metadata_type, item_id in files_to_delete:
        if file_path and os.path.exists(file_path):
            # Vérifier que c'est dans la bibliothèque audio
            if file_path.startswith(AUDIO_LIBRARY):
                try:
                    # Créer le chemin de sauvegarde relatif
                    rel_path = os.path.relpath(file_path, AUDIO_LIBRARY)
                    backup_path = os.path.join(BACKUP_DIR, rel_path)

                    # Créer les répertoires nécessaires
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)

                    # Copier le fichier en sauvegarde
                    shutil.copy2(file_path, backup_path)
                    print(f"💾 Sauvegardé: {os.path.basename(file_path)}")

                    # Supprimer le fichier original
                    os.remove(file_path)
                    print(f"🗑️ Supprimé: {title}")
                    deleted_count += 1

                except Exception as e:
                    print(f"❌ Erreur suppression {file_path}: {e}")
            else:
                print(f"⚠️ Hors bibliothèque: {file_path}")
        else:
            print(f"⚠️ Fichier introuvable: {title}")

    print(f"\n✅ Suppression terminée: {deleted_count} fichiers supprimés")
    print(f"💾 Sauvegardes: {BACKUP_DIR}")

    # Maintenant supprimer les ratings de la DB
    print("\n🔄 Suppression des ratings de la base de données...")

    # Supprimer les ratings pour les fichiers supprimés
    cursor.execute("""
        UPDATE metadata_item_settings
        SET rating = NULL, updated_at = ?
        WHERE rating = 2.0 AND account_id = 1
    """, (subprocess.run(['date', '+%s'], capture_output=True, text=True).stdout.strip(),))

    print(f"✅ {cursor.rowcount} ratings supprimés de la base de données")

    conn.commit()
    conn.close()

except Exception as e:
    print(f"❌ Erreur: {e}")

finally:
    # Nettoyer
    if os.path.exists(temp_db):
        os.remove(temp_db)