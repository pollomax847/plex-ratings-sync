#!/usr/bin/env python3
import sqlite3
import subprocess
import tempfile
import shutil
import os

subprocess.run(["sudo", "snap", "stop", "plexmediaserver"], check=True, capture_output=True)

plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'

temp_db = tempfile.mktemp(suffix='.db')
shutil.copy2(plex_db, temp_db)

conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

print("=== COLONNES DISPONIBLES DANS metadata_item_settings ===")
cursor.execute("PRAGMA table_info(metadata_item_settings)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

print("\n=== RATINGS UTILISATEUR (1-5 ÉTOILES) ===")
cursor.execute("""
    SELECT mi.title, mis.rating, mi.metadata_type
    FROM metadata_items mi
    JOIN metadata_item_settings mis ON mis.guid = mi.guid
    WHERE mis.rating BETWEEN 1 AND 5
    ORDER BY mis.rating DESC
    LIMIT 10
""")

for title, rating, meta_type in cursor.fetchall():
    type_name = "Album" if meta_type == 9 else "Artiste" if meta_type == 8 else "Piste" if meta_type == 10 else f"Type {meta_type}"
    print(f"{rating}⭐ {type_name}: {title[:50]}")

print("\n=== COMPTAGE PAR TYPE ===")
cursor.execute("""
    SELECT mi.metadata_type, COUNT(*) as count
    FROM metadata_items mi
    JOIN metadata_item_settings mis ON mis.guid = mi.guid
    WHERE mis.rating BETWEEN 1 AND 5
    GROUP BY mi.metadata_type
    ORDER BY mi.metadata_type
""")

for meta_type, count in cursor.fetchall():
    type_name = "Album" if meta_type == 9 else "Artiste" if meta_type == 8 else "Piste" if meta_type == 10 else f"Type {meta_type}"
    print(f"{type_name}: {count} ratings")

print("\n=== VÉRIFICATION DES AUTRES COLONNES DE RATING ===")
cursor.execute("""
    SELECT mi.title, mis.rating, mi.metadata_type
    FROM metadata_items mi
    JOIN metadata_item_settings mis ON mis.guid = mi.guid
    WHERE mis.rating IS NOT NULL
    LIMIT 10
""")

for title, rating, meta_type in cursor.fetchall():
    type_name = "Album" if meta_type == 9 else "Artiste" if meta_type == 8 else "Piste" if meta_type == 10 else f"Type {meta_type}"
    print(f"{type_name}: {title[:30]} - rating: {rating}")

conn.close()
os.remove(temp_db)
subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True, capture_output=True)
subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True, capture_output=True)
