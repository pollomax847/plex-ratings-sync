#!/usr/bin/env python3
import sqlite3
import tempfile
import shutil
import os
import tempfile
import shutil
import os

plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
temp_db = tempfile.mktemp(suffix='.db')
shutil.copy2(plex_db, temp_db)

conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

print("=== TEST JOINTURE POUR PISTES ===")
try:
    cursor.execute("""
        SELECT COUNT(*) FROM media_parts mp
        JOIN media_items mi ON mp.media_item_id = mi.id
        JOIN metadata_items mdi ON mi.metadata_item_id = mdi.id
        JOIN metadata_item_settings mis ON mis.guid = mdi.guid
        WHERE mis.rating IS NOT NULL AND mis.rating BETWEEN 1 AND 5 AND mis.account_id = 1
    """)
    count = cursor.fetchone()[0]
    print(f"✅ Jointure pistes fonctionne: {count} résultats")
except Exception as e:
    print(f"❌ Erreur jointure pistes: {e}")

print("\n=== TEST JOINTURE POUR ARTISTES ===")
try:
    cursor.execute("""
        SELECT COUNT(*) FROM metadata_items mi
        JOIN metadata_item_settings mis ON mis.guid = mi.guid
        WHERE mi.metadata_type = 8 AND mis.rating IS NOT NULL AND mis.rating BETWEEN 1 AND 5 AND mis.account_id = 1
    """)
    count = cursor.fetchone()[0]
    print(f"✅ Jointure artistes fonctionne: {count} résultats")
except Exception as e:
    print(f"❌ Erreur jointure artistes: {e}")

print("\n=== TEST JOINTURE POUR ALBUMS ===")
try:
    cursor.execute("""
        SELECT COUNT(*) FROM metadata_items mi
        JOIN metadata_item_settings mis ON mis.guid = mi.guid
        WHERE mi.metadata_type = 9 AND mis.rating IS NOT NULL AND mis.rating BETWEEN 1 AND 5 AND mis.account_id = 1
    """)
    count = cursor.fetchone()[0]
    print(f"✅ Jointure albums fonctionne: {count} résultats")
except Exception as e:
    print(f"❌ Erreur jointure albums: {e}")

conn.close()
os.remove(temp_db)
