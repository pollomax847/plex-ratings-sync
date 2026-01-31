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

print("=== RATINGS DANS metadata_item_settings (rating column) ===")
cursor.execute("""
    SELECT mi.title, mis.rating, mi.metadata_type, mis.account_id
    FROM metadata_items mi
    JOIN metadata_item_settings mis ON mis.guid = mi.guid
    WHERE mis.rating IS NOT NULL AND mis.rating > 0
    ORDER BY mis.rating DESC
    LIMIT 15
""")

for title, rating, meta_type, account_id in cursor.fetchall():
    type_name = "Album" if meta_type == 9 else "Artiste" if meta_type == 8 else "Piste" if meta_type == 10 else f"Type {meta_type}"
    print(f"{rating}⭐ {type_name}: {title[:40]} (account: {account_id})")

print("\n=== COMPTES DISPONIBLES ===")
cursor.execute("SELECT id, name FROM accounts")
for account_id, name in cursor.fetchall():
    print(f"Account {account_id}: {name}")

print("\n=== RATINGS PAR COMPTE ===")
cursor.execute("""
    SELECT mis.account_id, COUNT(*) as count, MIN(mis.rating) as min_rating, MAX(mis.rating) as max_rating
    FROM metadata_item_settings mis
    WHERE mis.rating IS NOT NULL AND mis.rating > 0
    GROUP BY mis.account_id
    ORDER BY mis.account_id
""")

for account_id, count, min_rating, max_rating in cursor.fetchall():
    print(f"Account {account_id}: {count} ratings (min: {min_rating}, max: {max_rating})")

print("\n=== VÉRIFICATION SI LES RATINGS 1-5 SONT LES UTILISATEUR ===")
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

conn.close()
os.remove(temp_db)
subprocess.run(["sudo", "snap", "start", "plexmediaserver"], check=True, capture_output=True)
