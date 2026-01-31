#!/usr/bin/env python3
"""
Script pour retrouver les audios avec 1 étoile dans Plex
"""
import sqlite3
import subprocess
import tempfile
import shutil
import os

def find_1_star_audios():
    """Trouve tous les fichiers audio avec rating 1 étoile"""
    # Arrêter Plex temporairement
    print("Arrêt de Plex...")
    subprocess.run(["sudo", "snap", "stop", "plexmediaserver"], check=True)

    try:
        # Copier la DB pour éviter les problèmes de permissions
        plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
        temp_db = tempfile.mktemp(suffix='.db')
        shutil.copy2(plex_db, temp_db)

        print(f"Base de données copiée vers: {temp_db}")

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Rechercher tous les fichiers avec rating 2.0 (1 étoile affichée)
        cursor.execute("""
            SELECT mi.title, mi.year, mi.metadata_type, mp.file, mi.id as item_id
            FROM metadata_item_settings mis
            JOIN metadata_items mi ON mis.guid = mi.guid
            LEFT JOIN media_items media ON mi.id = media.metadata_item_id
            LEFT JOIN media_parts mp ON media.id = mp.media_item_id
            WHERE mis.rating = 2.0 AND mis.account_id = 1
            ORDER BY mi.title
        """)

        results = cursor.fetchall()
        conn.close()

        print(f"\n=== AUDIOS AVEC 1 ÉTOILE ({len(results)} trouvés) ===")

        if results:
            for title, year, metadata_type, file_path, item_id in results:
                print(f"\n📀 {title} ({year or 'N/A'})")
                print(f"   Type: {metadata_type} (10=track, 9=album, 8=artist)")
                print(f"   ID Plex: {item_id}")
                if file_path:
                    if os.path.exists(file_path):
                        print(f"   ✅ Fichier existe: {file_path}")
                    else:
                        print(f"   ❌ Fichier introuvable: {file_path}")
                else:
                    print("   ⚠️ Pas de fichier associé dans la base")
        else:
            print("Aucun audio avec 1 étoile trouvé.")
            print("\nNote: Les ratings peuvent être sur une échelle différente (ex: 0-10 au lieu de 0-5)")
            print("Vérifiez les statistiques des ratings avec check_ratings_detailed.py")

        # Nettoyer
        if os.path.exists(temp_db):
            os.remove(temp_db)
            print(f"\nFichier temporaire nettoyé: {temp_db}")

    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        # Redémarrer Plex
        print("Redémarrage de Plex...")
        subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True)

if __name__ == "__main__":
    find_1_star_audios()