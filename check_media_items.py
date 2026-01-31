#!/usr/bin/env python3
import sqlite3
import subprocess
import tempfile
import shutil

subprocess.run(["sudo", "snap", "stop", "plexmediaserver"], check=True, capture_output=True)

plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
temp_db = tempfile.mktemp(suffix='.db')
shutil.copy2(plex_db, temp_db)

conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

print("=== COLONNES media_items ===")
cursor.execute("PRAGMA table_info(media_items)")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col[1]} ({col[2]})")

print("\n=== TEST REQUÊTE PISTES ===")
try:
    cursor.execute("""
        SELECT mp.file, mdi.guid, mis.rating FROM media_parts mp
        JOIN media_items mi ON mp.media_item_id = mi.id
        JOIN metadata_items mdi ON mi.metadata_item_id = mdi.id
        JOIN metadata_item_settings mis ON mis.guid = mdi.guid
        WHERE mis.rating IS NOT NULL AND mis.rating BETWEEN 1 AND 5 AND mis.account_id = 1
        LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        print(f"✅ Requête fonctionne: file={result[0][:50]}..., guid={result[1]}, rating={result[2]}")
    else:
        print("✅ Requête fonctionne mais aucun résultat")
except Exception as e:
    print(f"❌ Erreur: {e}")

conn.close()
subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True, capture_output=True)
