#!/usr/bin/env python3
import sqlite3
import subprocess
import tempfile
import shutil
import os

subprocess.run(["sudo", "snap", "stop", "plexmediaserver"], check=True, capture_output=True)

plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'
temp_db = tempfile.mktemp(suffix='.db')

print("Copie de la base de données...")
shutil.copy2(plex_db, temp_db)

conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

print("=== COLONNES DISPONIBLES DANS metadata_items ===")
cursor.execute("PRAGMA table_info(metadata_items)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

print("\n=== COLONNES DISPONIBLES DANS metadata_item_settings ===")
cursor.execute("PRAGMA table_info(metadata_item_settings)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

print("\n=== RELATION ENTRE LES TABLES ===")
cursor.execute("""
    SELECT mi.id, mi.guid, mis.id, mis.guid, mis.account_id, mis.rating
    FROM metadata_items mi
    LEFT JOIN metadata_item_settings mis ON mis.guid = mi.guid
    WHERE mis.rating IS NOT NULL AND mis.rating BETWEEN 1 AND 5
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"mi.id={row[0]}, mi.guid={row[1]}, mis.id={row[2]}, mis.guid={row[3]}, account={row[4]}, rating={row[5]}")

conn.close()
os.remove(temp_db)
subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True, capture_output=True)
