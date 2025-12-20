#!/usr/bin/env python3
"""
Script pour corriger les métadonnées des fichiers audio avec les bonnes informations de Plex
Remplace les tags incorrects (format "Artiste - Titre") par les vrais tags
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import logging

try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
except ImportError:
    print("❌ Erreur: Module 'mutagen' requis. Installez avec: pip3 install mutagen")
    sys.exit(1)

class MetadataFixer:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.setup_logging()
        self.processed_files = []
        self.failed_files = []
        self.skipped_files = []

    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def fix_mp3_metadata(self, file_path: Path, metadata: Dict) -> bool:
        """Corrige les métadonnées d'un fichier MP3"""
        try:
            audio = MP3(file_path, ID3=ID3)

            # Supprimer les anciens tags
            audio.delete()

            # Ajouter les nouveaux tags corrects
            audio.tags.add(TIT2(encoding=3, text=metadata['title']))
            audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
            audio.tags.add(TALB(encoding=3, text=metadata['album']))

            if metadata.get('track_number'):
                audio.tags.add(TRCK(encoding=3, text=str(metadata['track_number'])))

            audio.save()

            self.logger.info(f"✅ MP3 corrigé: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur MP3 {file_path.name}: {e}")
            return False

    def fix_mp4_metadata(self, file_path: Path, metadata: Dict) -> bool:
        """Corrige les métadonnées d'un fichier MP4/M4A"""
        try:
            audio = MP4(file_path)

            # Corriger les tags
            audio.tags['\xa9nam'] = metadata['title']  # Title
            audio.tags['\xa9ART'] = metadata['artist']  # Artist
            audio.tags['\xa9alb'] = metadata['album']  # Album

            if metadata.get('track_number'):
                audio.tags['trkn'] = [(metadata['track_number'], 0)]  # Track number

            audio.save()

            self.logger.info(f"✅ MP4 corrigé: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur MP4 {file_path.name}: {e}")
            return False

    def fix_flac_metadata(self, file_path: Path, metadata: Dict) -> bool:
        """Corrige les métadonnées d'un fichier FLAC"""
        try:
            audio = FLAC(file_path)

            # Corriger les tags
            audio.tags['TITLE'] = metadata['title']
            audio.tags['ARTIST'] = metadata['artist']
            audio.tags['ALBUM'] = metadata['album']

            if metadata.get('track_number'):
                audio.tags['TRACKNUMBER'] = str(metadata['track_number'])

            audio.save()

            self.logger.info(f"✅ FLAC corrigé: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur FLAC {file_path.name}: {e}")
            return False

    def fix_file_metadata(self, metadata: Dict) -> bool:
        """Corrige les métadonnées d'un fichier"""
        file_path = Path(metadata['file_path'])

        if not file_path.exists():
            self.logger.warning(f"❌ Fichier introuvable: {file_path}")
            self.skipped_files.append(metadata)
            return False

        # Déterminer le type de fichier
        suffix = file_path.suffix.lower()

        success = False
        if suffix in ['.mp3']:
            success = self.fix_mp3_metadata(file_path, metadata)
        elif suffix in ['.mp4', '.m4a', '.aac']:
            success = self.fix_mp4_metadata(file_path, metadata)
        elif suffix in ['.flac']:
            success = self.fix_flac_metadata(file_path, metadata)
        else:
            self.logger.warning(f"⚠️ Format non supporté: {suffix} - {file_path.name}")
            self.skipped_files.append(metadata)
            return False

        if success:
            self.processed_files.append(metadata)
        else:
            self.failed_files.append(metadata)

        return success

    def fix_all_metadata(self, json_file: Path) -> Dict:
        """Corrige les métadonnées de tous les fichiers depuis un fichier JSON"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                files_data = json.load(f)

            self.logger.info(f"🎵 Correction métadonnées pour {len(files_data)} fichiers...")

            for file_info in files_data:
                self.fix_file_metadata(file_info)

            # Statistiques
            stats = {
                'total_files': len(files_data),
                'processed': len(self.processed_files),
                'failed': len(self.failed_files),
                'skipped': len(self.skipped_files)
            }

            self.logger.info("✅ Correction terminée:")
            self.logger.info(f"   • {stats['processed']} fichiers corrigés")
            self.logger.info(f"   • {stats['failed']} erreurs")
            self.logger.info(f"   • {stats['skipped']} fichiers ignorés")

            return stats

        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement du fichier JSON: {e}")
            return {'error': str(e)}

def main():
    parser = argparse.ArgumentParser(description='Corrige les métadonnées des fichiers audio avec les bonnes informations de Plex')
    parser.add_argument('json_file', help='Fichier JSON contenant les métadonnées exportées de Plex')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbose')

    args = parser.parse_args()

    fixer = MetadataFixer(verbose=args.verbose)
    stats = fixer.fix_all_metadata(Path(args.json_file))

    if 'error' in stats:
        sys.exit(1)

    # Exit code basé sur les erreurs
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()