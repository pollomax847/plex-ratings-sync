#!/usr/bin/env python3
"""
Script pour identifier et supprimer les fichiers audio par genre
Utilise les métadonnées ID3 pour lire les genres
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List
import logging

try:
    from mutagen.id3 import ID3
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen._file import File
except ImportError:
    print("❌ Erreur: Module 'mutagen' requis. Installez avec: pip3 install mutagen")
    sys.exit(1)

class GenreFilter:
    def __init__(self, unwanted_genres: List[str], excluded_artists: List[str], verbose: bool = False, dry_run: bool = True):
        self.unwanted_genres = [g.lower() for g in unwanted_genres]
        self.excluded_artists = [a.lower() for a in excluded_artists]
        self.verbose = verbose
        self.dry_run = dry_run
        self.setup_logging()
        self.found_files = []
        
    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def get_artist_and_genre_from_file(self, file_path: Path) -> tuple[str, str]:
        """Extrait l'artiste et le genre du fichier audio"""
        artist = ""
        genre = ""
        try:
            if file_path.suffix.lower() == '.mp3':
                audio = MP3(file_path, ID3=ID3)
                if audio.tags:
                    if 'TPE1' in audio.tags:
                        artist = str(audio.tags['TPE1'])
                    if 'TCON' in audio.tags:
                        genre = str(audio.tags['TCON'])
            elif file_path.suffix.lower() == '.flac':
                audio = FLAC(file_path)
                if 'artist' in audio:
                    artist = str(audio['artist'][0])
                if 'genre' in audio:
                    genre = str(audio['genre'][0])
            elif file_path.suffix.lower() in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if '©ART' in audio:
                    artist = str(audio['©ART'][0])
                if '©gen' in audio:
                    genre = str(audio['©gen'][0])
            # Pour autres formats, utiliser mutagen générique
            audio = File(file_path)
            if audio and hasattr(audio, 'tags') and audio.tags:
                if 'artist' in audio.tags:
                    artist = str(audio.tags['artist'])
                if 'genre' in audio.tags:
                    genre = str(audio.tags['genre'])
        except Exception as e:
            self.logger.debug(f"Erreur lecture artiste/genre {file_path}: {e}")
        return artist.lower(), genre.lower()

    def scan_directory(self, directory: Path) -> None:
        """Scanne récursivement le répertoire pour les fichiers audio"""
        audio_extensions = ('.mp3', '.flac', '.m4a', '.ogg', '.wma', '.aac', '.wav', '.mp4')
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                artist, genre = self.get_artist_and_genre_from_file(file_path)
                if genre and any(unwanted in genre for unwanted in self.unwanted_genres):
                    # Vérifier si l'artiste est exclu
                    if artist and any(excluded in artist for excluded in self.excluded_artists):
                        self.logger.debug(f"Artiste exclu: {file_path} (Artiste: {artist})")
                        continue
                    self.found_files.append((file_path, genre, artist))
                    self.logger.info(f"🎸 Trouvé: {file_path} (Genre: {genre}, Artiste: {artist})")

    def delete_files(self) -> None:
        """Supprime les fichiers trouvés"""
        if self.dry_run:
            self.logger.info("🔍 Mode simulation - Aucun fichier supprimé")
            return
            
        for file_path, genre, artist in self.found_files:
            try:
                file_path.unlink()
                self.logger.info(f"🗑️ Supprimé: {file_path}")
            except Exception as e:
                self.logger.error(f"❌ Erreur suppression {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Identifier et supprimer les fichiers audio par genre")
    parser.add_argument("directory", help="Répertoire à scanner")
    parser.add_argument("--genres", nargs='+', default=["hard rock", "metal", "punk", "heavy metal", "thrash metal", "death metal", "black metal"],
                        help="Genres à supprimer (par défaut: hard rock, metal, punk, heavy metal, etc.)")
    parser.add_argument("--exclude-artists", nargs='+', default=["ac/dc"],
                        help="Artistes à exclure de la suppression (par défaut: ac/dc)")
    parser.add_argument("--delete", action="store_true", help="Supprimer réellement les fichiers (sinon mode simulation)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"❌ Répertoire invalide: {directory}")
        sys.exit(1)
    
    filter = GenreFilter(args.genres, args.exclude_artists, args.verbose, not args.delete)
    
    print(f"🔍 Scan du répertoire: {directory}")
    print(f"🎸 Genres à supprimer: {', '.join(args.genres)}")
    print(f"🙅 Artistes exclus: {', '.join(args.exclude_artists)}")
    print(f"🗑️ Mode: {'Suppression' if args.delete else 'Simulation'}")
    
    filter.scan_directory(directory)
    
    print(f"\n📊 {len(filter.found_files)} fichiers trouvés")
    
    if filter.found_files:
        print("\nFichiers à traiter:")
        for file_path, genre, artist in filter.found_files:
            print(f"  {file_path} (Genre: {genre}, Artiste: {artist})")
        
        if not args.delete:
            print("\n💡 Utilisez --delete pour supprimer réellement")
        else:
            filter.delete_files()
    else:
        print("✅ Aucun fichier trouvé avec ces genres")

if __name__ == "__main__":
    main()