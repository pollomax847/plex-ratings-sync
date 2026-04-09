#!/usr/bin/env python3
"""
Script temporaire pour renommer les fichiers 1-étoile spécifiques avec songrec
"""
import subprocess
import json
import os
import shutil
from pathlib import Path

def run_songrec(file_path):
    """Exécute songrec sur un fichier et retourne le résultat"""
    try:
        result = subprocess.run(
            ['songrec', 'audio-file-to-recognized-song', str(file_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data
            except json.JSONDecodeError:
                print(f"❌ Erreur JSON pour {file_path.name}")
                return None
        else:
            print(f"❌ Songrec échoué pour {file_path.name}: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout pour {file_path.name}")
        return None
    except Exception as e:
        print(f"❌ Erreur pour {file_path.name}: {e}")
        return None

def generate_new_filename(songrec_data):
    """Génère un nouveau nom de fichier basé sur les données songrec"""
    if not songrec_data:
        return None

    # Extraire les informations (structure Shazam)
    track = songrec_data.get('track', {})
    artist = track.get('subtitle', 'Unknown Artist')  # Artiste dans 'subtitle'
    title = track.get('title', 'Unknown Title')       # Titre dans 'title'
    album = None
    
    # Chercher l'album dans les métadonnées si disponible
    sections = track.get('sections', [])
    for section in sections:
        if section.get('type') == 'SONG':
            metadata = section.get('metadata', [])
            for meta in metadata:
                if meta.get('title') == 'Album':
                    album = meta.get('text')
                    break
            break

    # Nettoyer les noms
    artist = artist.replace('/', '-').replace('\\', '-')
    title = title.replace('/', '-').replace('\\', '-')
    if album:
        album = album.replace('/', '-').replace('\\', '-')

    # Format: Artist - Title.mp3 (ou extension originale)
    if album:
        new_name = f"{artist} - {album} - {title}"
    else:
        new_name = f"{artist} - {title}"

    return new_name

def rename_file_with_songrec(file_path):
    """Renomme un fichier en utilisant songrec"""
    print(f"🎵 Traitement de: {file_path.name}")

    # Exécuter songrec
    data = run_songrec(file_path)

    if data:
        new_name = generate_new_filename(data)
        if new_name:
            # Obtenir l'extension
            ext = file_path.suffix

            # Nouveau chemin complet
            new_path = file_path.parent / f"{new_name}{ext}"

            # Éviter les conflits
            counter = 1
            while new_path.exists():
                new_path = file_path.parent / f"{new_name} ({counter}){ext}"
                counter += 1

            print(f"✅ Identifié: {new_name}")
            print(f"📁 Nouveau nom: {new_path.name}")

            # Renommer avec sudo si nécessaire
            try:
                file_path.rename(new_path)
                print(f"✅ Renommé: {file_path.name} → {new_path.name}")
                return True
            except PermissionError:
                print("🔐 Permission denied, tentative avec sudo...")
                try:
                    subprocess.run(['sudo', 'mv', str(file_path), str(new_path)], check=True)
                    print(f"✅ Renommé avec sudo: {file_path.name} → {new_path.name}")
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"❌ Échec sudo: {e}")
                    return False
            except Exception as e:
                print(f"❌ Erreur renommage: {e}")
                return False
        else:
            print("❌ Impossible de générer un nouveau nom")
            return False
    else:
        print("❌ Échec identification")
        return False

def main():
    # Liste des fichiers à traiter avec leurs vrais noms
    files_to_correct = [
        ("/media/paulceline/5E0C011B0C00EFB71/itunes/Music/Digital Media 02/Unknown Artist - Fière allure.mp3", "Matmatah - Fière allure.mp3"),
        ("/media/paulceline/5E0C011B0C00EFB71/itunes/Music/Michel Jonasz/Unknown Artist - Le mal de toi.mp3", "Michel Jonasz - Le mal de toi.mp3"),
        ("/media/paulceline/5E0C011B0C00EFB71/itunes/Music/1967 - misty/Unknown Artist - The More I See You.mp3", "Richard \"Groove\" Holmes - The More I See You.mp3")
    ]

    print("🔧 Correction des noms de fichiers avec les vrais artistes")
    print("=" * 60)

    success_count = 0

    for old_path_str, new_name in files_to_correct:
        old_path = Path(old_path_str)
        if old_path.exists():
            new_path = old_path.parent / new_name
            try:
                # Utiliser sudo pour renommer
                subprocess.run(['sudo', 'mv', str(old_path), str(new_path)], check=True)
                print(f"✅ Corrigé: {old_path.name} → {new_name}")
                success_count += 1
            except subprocess.CalledProcessError as e:
                print(f"❌ Échec: {old_path.name} - {e}")
        else:
            print(f"❌ Fichier introuvable: {old_path_str}")

    print(f"\n📊 Résumé: {success_count}/{len(files_to_correct)} fichiers corrigés")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()