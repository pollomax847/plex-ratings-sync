#!/usr/bin/env python3
"""
Script de synchronisation des évaluations Plex avec la bibliothèque audio
Supprime automatiquement les fichiers avec 1 étoile dans Plex/PlexAmp

Fonctionnalités:
- Connexion à la base de données Plex SQLite
- Extraction des ratings des fichiers audio
- Suppression sécurisée des fichiers avec 1 étoile
- Mode simulation/dry-run par défaut
- Sauvegarde optionnelle avant suppression
- Logs détaillés de toutes les opérations

Usage:
    python3 plex_ratings_sync.py --plex-db /path/to/plex/database
    python3 plex_ratings_sync.py --plex-db /path/to/plex/database --delete
    python3 plex_ratings_sync.py --plex-db /path/to/plex/database --delete --backup
"""

import os
import sys
import sqlite3
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json

class PlexRatingsSync:
    def __init__(self, plex_db_path: str, config: Optional[Dict] = None):
        self.plex_db_path = Path(plex_db_path)
        self.deleted_files = []
        self.processed_files = 0
        self.errors = []
        self.skipped_files = []
        
        # Configuration par défaut
        default_config = {
            'target_rating': 1,  # Étoiles à supprimer (1-5)
            'backup_dir': None,  # Répertoire de sauvegarde
            'audio_extensions': ('.mp3', '.flac', '.m4a', '.ogg', '.wma', '.aac', '.wav'),
            'log_level': 'INFO',
            'verify_file_exists': True,
            'dry_run': True
        }
        
        self.config = {**default_config, **(config or {})}
        self.setup_logging()
        
    def setup_logging(self):
        """Configure le système de logs"""
        log_level = getattr(logging, self.config['log_level'])
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Log vers fichier et console
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(f'plex_ratings_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def verify_plex_database(self) -> bool:
        """Vérifie que la base de données Plex est accessible"""
        if not self.plex_db_path.exists():
            self.logger.error(f"Base de données Plex introuvable: {self.plex_db_path}")
            return False
            
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                # Vérifier les tables nécessaires
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('metadata_items', 'media_items', 'media_parts')")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['metadata_items', 'media_items', 'media_parts']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    self.logger.error(f"Tables manquantes dans la DB Plex: {missing_tables}")
                    return False
                    
                self.logger.info(f"✅ Base de données Plex vérifiée: {self.plex_db_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de la DB Plex: {e}")
            return False
    
    def get_rated_audio_files(self) -> List[Dict]:
        """Extrait les fichiers audio avec leur rating depuis la base Plex"""
        rated_files = []
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                # Requête pour obtenir les fichiers audio avec ratings utilisateur et play counts
                query = """
                SELECT 
                    mi.title as track_title,
                    mis.rating as user_rating,
                    mis.view_count as play_count,
                    mp.file as file_path,
                    mi.duration,
                    mi.year,
                    parent_mi.title as album_title,
                    grandparent_mi.title as artist_name
                FROM metadata_items mi
                LEFT JOIN media_items media ON mi.id = media.metadata_item_id
                LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
                LEFT JOIN metadata_items grandparent_mi ON parent_mi.parent_id = grandparent_mi.id
                LEFT JOIN metadata_item_settings mis ON mi.guid = mis.guid
                WHERE mi.metadata_type = 10  -- Type 10 = Track/Audio
                AND mp.file IS NOT NULL
                AND mis.rating IS NOT NULL
                ORDER BY mis.rating, grandparent_mi.title, parent_mi.title, mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    track_title, user_rating, play_count, file_path, duration, year, album_title, artist_name = row
                    
                    # Convertir le rating (Plex stocke parfois sur 10, parfois sur 5)
                    final_rating = user_rating
                    if final_rating:
                        # Normaliser sur une échelle de 1-5 étoiles
                        if final_rating > 5:
                            final_rating = final_rating / 2  # Conversion 10 -> 5
                        
                        rated_files.append({
                            'file_path': file_path,
                            'rating': final_rating,
                            'play_count': play_count or 0,
                            'track_title': track_title or 'Unknown',
                            'album_title': album_title or 'Unknown Album',
                            'artist_name': artist_name or 'Unknown Artist',
                            'duration': duration,
                            'year': year
                        })
                
                self.logger.info(f"📊 Trouvé {len(rated_files)} fichiers avec ratings dans Plex")
                return rated_files
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture des ratings Plex: {e}")
            return []
    
    def get_rated_albums(self) -> List[Dict]:
        """Extrait les albums avec leur rating depuis la base Plex"""
        rated_albums = []
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                # Requête pour obtenir les albums avec ratings utilisateur
                query = """
                SELECT 
                    mi.title as album_title,
                    mis.rating as user_rating,
                    parent_mi.title as artist_name,
                    mi.id as album_id
                FROM metadata_items mi
                LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
                LEFT JOIN metadata_item_settings mis ON mi.guid = mis.guid
                WHERE mi.metadata_type = 2  -- Type 2 = Album
                AND mis.rating IS NOT NULL
                ORDER BY mis.rating, parent_mi.title, mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    album_title, user_rating, artist_name, album_id = row
                    
                    # Convertir le rating
                    final_rating = user_rating
                    if final_rating:
                        if final_rating > 5:
                            final_rating = final_rating / 2
                        
                        rated_albums.append({
                            'album_title': album_title or 'Unknown Album',
                            'artist_name': artist_name or 'Unknown Artist',
                            'rating': final_rating,
                            'album_id': album_id
                        })
                
                self.logger.info(f"💿 Trouvé {len(rated_albums)} albums avec ratings dans Plex")
                return rated_albums
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture des ratings albums Plex: {e}")
            return []
    
    def get_rated_artists(self) -> List[Dict]:
        """Extrait les artistes avec leur rating depuis la base Plex"""
        rated_artists = []
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                # Requête pour obtenir les artistes avec ratings utilisateur
                query = """
                SELECT 
                    mi.title as artist_name,
                    mis.rating as user_rating,
                    mi.id as artist_id
                FROM metadata_items mi
                LEFT JOIN metadata_item_settings mis ON mi.guid = mis.guid
                WHERE mi.metadata_type = 3  -- Type 3 = Artist
                AND mis.rating IS NOT NULL
                ORDER BY mis.rating, mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    artist_name, user_rating, artist_id = row
                    
                    # Convertir le rating
                    final_rating = user_rating
                    if final_rating:
                        if final_rating > 5:
                            final_rating = final_rating / 2
                        
                        rated_artists.append({
                            'artist_name': artist_name or 'Unknown Artist',
                            'rating': final_rating,
                            'artist_id': artist_id
                        })
                
                self.logger.info(f"🎤 Trouvé {len(rated_artists)} artistes avec ratings dans Plex")
                return rated_artists
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture des ratings artistes Plex: {e}")
            return []
    
    def get_album_files(self, album_id: int) -> List[Dict]:
        """Récupère tous les fichiers d'un album"""
        files = []
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    mi.title as track_title,
                    mp.file as file_path,
                    parent_mi.title as album_title,
                    grandparent_mi.title as artist_name
                FROM metadata_items mi
                LEFT JOIN media_items media ON mi.id = media.metadata_item_id
                LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
                LEFT JOIN metadata_items grandparent_mi ON parent_mi.parent_id = grandparent_mi.id
                WHERE mi.metadata_type = 10  -- Tracks
                AND parent_mi.id = ?
                AND mp.file IS NOT NULL
                ORDER BY mi.index
                """
                
                cursor.execute(query, (album_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    track_title, file_path, album_title, artist_name = row
                    files.append({
                        'file_path': file_path,
                        'track_title': track_title or 'Unknown',
                        'album_title': album_title or 'Unknown Album',
                        'artist_name': artist_name or 'Unknown Artist',
                        'rating': 1.0  # Pour cohérence avec les autres
                    })
                
                return files
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des fichiers de l'album {album_id}: {e}")
            return []
    
    def get_artist_files(self, artist_id: int) -> List[Dict]:
        """Récupère tous les fichiers d'un artiste"""
        files = []
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    mi.title as track_title,
                    mp.file as file_path,
                    parent_mi.title as album_title,
                    grandparent_mi.title as artist_name
                FROM metadata_items mi
                LEFT JOIN media_items media ON mi.id = media.metadata_item_id
                LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
                LEFT JOIN metadata_items grandparent_mi ON parent_mi.parent_id = grandparent_mi.id
                WHERE mi.metadata_type = 10  -- Tracks
                AND grandparent_mi.id = ?
                AND mp.file IS NOT NULL
                ORDER BY parent_mi.title, mi.index
                """
                
                cursor.execute(query, (artist_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    track_title, file_path, album_title, artist_name = row
                    files.append({
                        'file_path': file_path,
                        'track_title': track_title or 'Unknown',
                        'album_title': album_title or 'Unknown Album',
                        'artist_name': artist_name or 'Unknown Artist',
                        'rating': 1.0
                    })
                
                return files
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des fichiers de l'artiste {artist_id}: {e}")
            return []
    
    def filter_files_by_rating(self, rated_files: List[Dict], target_rating: float) -> List[Dict]:
        """Filtre les fichiers selon le rating cible"""
        filtered = [f for f in rated_files if f['rating'] == target_rating]
        self.logger.info(f"🎯 Trouvé {len(filtered)} fichiers avec {target_rating} étoile(s)")
        return filtered
    
    def filter_albums_by_rating(self, rated_albums: List[Dict], target_rating: float) -> List[Dict]:
        """Filtre les albums selon le rating cible"""
        filtered = [a for a in rated_albums if a['rating'] == target_rating]
        self.logger.info(f"💿 Trouvé {len(filtered)} albums avec {target_rating} étoile(s)")
        return filtered
    
    def filter_artists_by_rating(self, rated_artists: List[Dict], target_rating: float) -> List[Dict]:
        """Filtre les artistes selon le rating cible"""
        filtered = [a for a in rated_artists if a['rating'] == target_rating]
        self.logger.info(f"🎤 Trouvé {len(filtered)} artistes avec {target_rating} étoile(s)")
        return filtered
    
    def verify_file_exists(self, file_path: str) -> bool:
        """Vérifie que le fichier existe sur le système"""
        path = Path(file_path)
        exists = path.exists()
        
        if not exists:
            self.logger.warning(f"❌ Fichier introuvable: {file_path}")
            self.skipped_files.append({
                'file_path': file_path,
                'reason': 'Fichier introuvable sur le système'
            })
        
        return exists
    
    def backup_file(self, file_path: Path, backup_dir: Path) -> bool:
        """Sauvegarde un fichier avant suppression"""
        try:
            # Créer la structure de répertoire dans le backup
            relative_path = file_path.relative_to(file_path.anchor)
            backup_path = backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"💾 Sauvegardé: {file_path} -> {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde {file_path}: {e}")
            return False
    
    def delete_file_safely(self, file_info: Dict, dry_run: bool = True, backup_dir: Optional[Path] = None) -> bool:
        """Supprime un fichier de manière sécurisée"""
        file_path = Path(file_info['file_path'])
        
        if not file_path.exists():
            self.logger.warning(f"❌ Fichier déjà supprimé ou introuvable: {file_path}")
            return False
        
        if dry_run:
            self.logger.info(f"🎭 [DRY-RUN] Suppression simulée: {file_path}")
            self.logger.info(f"    📝 {file_info['artist_name']} - {file_info['track_title']}")
            self.logger.info(f"    💿 Album: {file_info['album_title']}")
            self.logger.info(f"    ⭐ Rating: {file_info['rating']} étoile(s)")
            return True
        
        try:
            # Sauvegarde optionnelle
            if backup_dir:
                if not self.backup_file(file_path, backup_dir):
                    self.logger.warning(f"⚠️ Sauvegarde échouée pour {file_path}, suppression annulée")
                    return False
            
            # Suppression définitive
            file_path.unlink()
            self.logger.info(f"🗑️ Supprimé: {file_path}")
            self.logger.info(f"    📝 {file_info['artist_name']} - {file_info['track_title']}")
            
            self.deleted_files.append({
                'file_path': str(file_path),
                'artist': file_info['artist_name'],
                'title': file_info['track_title'],
                'album': file_info['album_title'],
                'rating': file_info['rating'],
                'deleted_at': datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur suppression {file_path}: {e}")
            self.errors.append(f"Suppression échouée: {file_path} - {e}")
            return False
    
    def process_two_star_files(self, two_star_files: List[Dict]) -> Dict:
        """Traite les fichiers 2 étoiles avec songrec pour identification"""
        if not two_star_files:
            return {'processed': 0, 'identified': 0, 'errors': 0}
        
        processed = 0
        identified = 0
        errors = 0
        
        self.logger.info(f"🎵 Traitement de {len(two_star_files)} fichiers 2⭐ avec songrec...")
        
        for file_info in two_star_files:
            file_path = Path(file_info['file_path'])
            processed += 1
            
            if not file_path.exists():
                self.logger.warning(f"❌ Fichier introuvable: {file_path}")
                errors += 1
                continue
            
            try:
                self.logger.info(f"🎧 Identification avec songrec: {file_path.name}")
                
                # Utiliser songrec pour identifier le fichier
                result = subprocess.run(
                    ['songrec', 'audio-file-to-recognized-song', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30  # Timeout de 30 secondes par fichier
                )
                
                if result.returncode == 0:
                    # Parser le résultat JSON
                    try:
                        song_data = json.loads(result.stdout)
                        if 'track' in song_data:
                            track = song_data['track']
                            title = track.get('title', 'Unknown')
                            artist = track.get('subtitle', 'Unknown Artist')
                            
                            self.logger.info(f"✅ Identifié: {artist} - {title}")
                            identified += 1
                            
                            # Ici on pourrait ajouter une logique pour renommer ou marquer le fichier
                            # Pour l'instant, on se contente de l'identifier
                        else:
                            self.logger.warning(f"⚠️ Pas de résultat pour: {file_path.name}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"⚠️ Erreur parsing JSON pour: {file_path.name}")
                        errors += 1
                else:
                    self.logger.warning(f"❌ Échec songrec pour: {file_path.name} - {result.stderr.strip()}")
                    errors += 1
                    
            except subprocess.TimeoutExpired:
                self.logger.warning(f"⏰ Timeout songrec pour: {file_path.name}")
                errors += 1
            except Exception as e:
                self.logger.error(f"❌ Erreur inattendue avec songrec: {e}")
                errors += 1
        
        return {
            'processed': processed,
            'identified': identified,
            'errors': errors
        }
    
    def sync_ratings(self, dry_run: bool = True, backup_dir: Optional[str] = None, delete_albums: bool = False, delete_artists: bool = False) -> Dict:
        """Synchronise les ratings Plex avec le système de fichiers
        
        Logique:
        - 1 étoile: suppression du fichier
        - 2 étoiles: identification avec songrec (conservation du fichier)
        - 3-5 étoiles: conservation
        """
        self.logger.info("🎵 Début de la synchronisation des ratings Plex")
        
        # Vérifier la base Plex
        if not self.verify_plex_database():
            return {'success': False, 'error': 'Base de données Plex inaccessible'}
        
        # Extraire les fichiers avec ratings
        all_rated_files = self.get_rated_audio_files()
        if not all_rated_files:
            self.logger.warning("Aucun fichier avec rating trouvé dans Plex")
            return {'success': True, 'deleted_files': 0, 'message': 'Aucun fichier à traiter'}
        
        # Séparer les fichiers par rating
        one_star_files = self.filter_files_by_rating(all_rated_files, 1.0)
        two_star_files = self.filter_files_by_rating(all_rated_files, 2.0)
        
        self.logger.info(f"🎯 Trouvé {len(one_star_files)} fichiers 1⭐ à supprimer")
        self.logger.info(f"🎧 Trouvé {len(two_star_files)} fichiers 2⭐ à identifier avec songrec")
        
        # Traiter les fichiers 2 étoiles avec songrec (toujours, pas de suppression)
        songrec_results = {'processed': 0, 'identified': 0, 'errors': 0}
        if two_star_files:
            songrec_results = self.process_two_star_files(two_star_files)
            
            # Envoyer une notification pour le traitement songrec
            if songrec_results['processed'] > 0:
                try:
                    script_dir = Path(__file__).parent
                    notifications_script = script_dir / 'plex_notifications.sh'
                    
                    if notifications_script.exists():
                        # Calculer le nombre d'albums traités (approximation)
                        album_count = len(set(f['album_title'] for f in two_star_files))
                        
                        subprocess.run([
                            str(notifications_script), 
                            'songrec_completed',
                            str(songrec_results['processed']),
                            str(songrec_results['errors']),
                            str(album_count),
                            str(songrec_results['processed'])  # track_count ≈ processed pour l'instant
                        ], capture_output=True, text=True, timeout=10)
                        
                        self.logger.info(f"🔔 Notification songrec envoyée: {songrec_results['processed']} traités, {songrec_results['errors']} erreurs")
                    else:
                        self.logger.warning(f"Script de notifications introuvable: {notifications_script}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur lors de l'envoi de la notification songrec: {e}")
        
        # Traiter les fichiers 1 étoile (suppression)
        deleted_count = 0
        backup_path = None
        if backup_dir and not dry_run:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"💾 Répertoire de sauvegarde: {backup_path}")
        
        if one_star_files:
            # Supprimer les fichiers 1 étoile
            for file_info in one_star_files:
                self.processed_files += 1
                
                # Vérifier l'existence si configuré
                if self.config['verify_file_exists']:
                    if not self.verify_file_exists(file_info['file_path']):
                        continue
                
                # Supprimer le fichier
                if self.delete_file_safely(file_info, dry_run, backup_path):
                    deleted_count += 1
        
        # Traiter les albums 1 étoile si demandé
        deleted_albums = 0
        if delete_albums:
            all_rated_albums = self.get_rated_albums()
            target_albums = self.filter_albums_by_rating(all_rated_albums, self.config['target_rating'])
            
            self.logger.info(f"💿 Trouvé {len(target_albums)} albums {self.config['target_rating']}⭐ à supprimer")
            
            for album_info in target_albums:
                album_files = self.get_album_files(album_info['album_id'])
                self.logger.info(f"💿 Suppression de l'album '{album_info['album_title']}' - {len(album_files)} fichiers")
                
                for file_info in album_files:
                    self.processed_files += 1
                    
                    if self.config['verify_file_exists']:
                        if not self.verify_file_exists(file_info['file_path']):
                            continue
                    
                    if self.delete_file_safely(file_info, dry_run, backup_path):
                        deleted_count += 1
                
                deleted_albums += 1
        
        # Traiter les artistes 1 étoile si demandé
        deleted_artists = 0
        if delete_artists:
            all_rated_artists = self.get_rated_artists()
            target_artists = self.filter_artists_by_rating(all_rated_artists, self.config['target_rating'])
            
            self.logger.info(f"🎤 Trouvé {len(target_artists)} artistes {self.config['target_rating']}⭐ à supprimer")
            
            for artist_info in target_artists:
                artist_files = self.get_artist_files(artist_info['artist_id'])
                self.logger.info(f"🎤 Suppression de l'artiste '{artist_info['artist_name']}' - {len(artist_files)} fichiers")
                
                for file_info in artist_files:
                    self.processed_files += 1
                    
                    if self.config['verify_file_exists']:
                        if not self.verify_file_exists(file_info['file_path']):
                            continue
                    
                    if self.delete_file_safely(file_info, dry_run, backup_path):
                        deleted_count += 1
                
                deleted_artists += 1
        
        # Envoyer une notification pour les fichiers supprimés
        if not dry_run and (deleted_count > 0 or deleted_albums > 0 or deleted_artists > 0):
            try:
                script_dir = Path(__file__).parent
                notifications_script = script_dir / 'plex_notifications.sh'
                
                if notifications_script.exists():
                    # Créer un résumé des suppressions
                    details = f"{deleted_count} fichier(s) 1⭐ supprimé(s)"
                    if deleted_albums > 0:
                        details += f", {deleted_albums} album(s)"
                    if deleted_artists > 0:
                        details += f", {deleted_artists} artiste(s)"
                    
                    subprocess.run([
                        str(notifications_script), 
                        'files_deleted',
                        str(deleted_count + deleted_albums + deleted_artists),  # Total des éléments supprimés
                        details
                    ], capture_output=True, text=True, timeout=10)
                    
                    self.logger.info(f"🔔 Notification suppression envoyée: {deleted_count + deleted_albums + deleted_artists} élément(s) supprimé(s)")
                else:
                    self.logger.warning(f"Script de notifications introuvable: {notifications_script}")
                    
            except Exception as e:
                self.logger.warning(f"Erreur lors de l'envoi de la notification suppression: {e}")
        
        # Nettoyer la base de données Plex
        cleaned_plex_entries = 0
        if not dry_run and deleted_count > 0:
            self.logger.info("🗃️ Nettoyage de la base de données Plex...")
            cleaned_plex_entries = self.cleanup_plex_database(self.deleted_files)
            self.cleaned_plex_entries = cleaned_plex_entries  # Stocker pour le rapport
        
        # Résumé
        result = {
            'success': True,
            'processed_files': self.processed_files,
            'deleted_files': deleted_count,
            'deleted_albums': deleted_albums,
            'deleted_artists': deleted_artists,
            'songrec_processed': songrec_results['processed'],
            'songrec_identified': songrec_results['identified'],
            'songrec_errors': songrec_results['errors'],
            'cleaned_dirs': 0,
            'cleaned_plex_entries': cleaned_plex_entries,
            'skipped_files': len(self.skipped_files),
            'errors': len(self.errors),
            'dry_run': dry_run
        }
        
        self.logger.info(f"✅ Synchronisation terminée:")
        self.logger.info(f"    📊 Fichiers traités: {self.processed_files}")
        self.logger.info(f"    🗑️ Fichiers 1⭐ supprimés: {deleted_count}")
        if deleted_albums > 0:
            self.logger.info(f"    💿 Albums 1⭐ supprimés: {deleted_albums}")
        if deleted_artists > 0:
            self.logger.info(f"    🎤 Artistes 1⭐ supprimés: {deleted_artists}")
        self.logger.info(f"    🎧 Fichiers 2⭐ traités: {songrec_results['processed']}")
        self.logger.info(f"    ✅ Fichiers 2⭐ identifiés: {songrec_results['identified']}")
        if songrec_results['errors'] > 0:
            self.logger.info(f"    ❌ Erreurs songrec: {songrec_results['errors']}")
        if cleaned_plex_entries > 0:
            self.logger.info(f"    🗃️ Entrées Plex nettoyées: {cleaned_plex_entries}")
        self.logger.info(f"    ⏭️ Fichiers ignorés: {len(self.skipped_files)}")
        self.logger.info(f"    ❌ Erreurs: {len(self.errors)}")
        
        return result
    
    def show_rating_statistics(self):
        """Affiche les statistiques des ratings dans Plex"""
        self.logger.info("📊 Analyse des ratings dans Plex...")
        
        # Statistiques des pistes
        rated_files = self.get_rated_audio_files()
        rating_counts = {}
        if rated_files:
            # Compter par rating pour les pistes
            for file_info in rated_files:
                rating = file_info['rating']
                rating_counts[rating] = rating_counts.get(rating, 0) + 1
        
        # Statistiques des albums
        rated_albums = self.get_rated_albums()
        album_rating_counts = {}
        if rated_albums:
            for album_info in rated_albums:
                rating = album_info['rating']
                album_rating_counts[rating] = album_rating_counts.get(rating, 0) + 1
        
        # Statistiques des artistes
        rated_artists = self.get_rated_artists()
        artist_rating_counts = {}
        if rated_artists:
            for artist_info in rated_artists:
                rating = artist_info['rating']
                artist_rating_counts[rating] = artist_rating_counts.get(rating, 0) + 1
        
        print("\n📊 STATISTIQUES DES RATINGS:")
        print("=" * 50)
        
        # Afficher les pistes
        if rated_files:
            print("🎵 PISTES:")
            for rating in sorted(rating_counts.keys()):
                stars = "⭐" * int(rating)
                print(f"  {stars} ({rating}) : {rating_counts[rating]} fichiers")
        
        # Afficher les albums
        if rated_albums:
            print("\n💿 ALBUMS:")
            for rating in sorted(album_rating_counts.keys()):
                stars = "⭐" * int(rating)
                print(f"  {stars} ({rating}) : {album_rating_counts[rating]} albums")
        else:
            print("\n💿 ALBUMS: Aucun album avec rating")
        
        # Afficher les artistes
        if rated_artists:
            print("\n🎤 ARTISTES:")
            for rating in sorted(artist_rating_counts.keys()):
                stars = "⭐" * int(rating)
                print(f"  {stars} ({rating}) : {artist_rating_counts[rating]} artistes")
        else:
            print("\n🎤 ARTISTES: Aucun artiste avec rating")
        
        total_items = len(rated_files) + len(rated_albums) + len(rated_artists)
        print(f"\nTotal: {total_items} éléments avec ratings ({len(rated_files)} pistes, {len(rated_albums)} albums, {len(rated_artists)} artistes)")
    
    def save_deletion_report(self):
        """Sauvegarde un rapport des suppressions"""
        if not self.deleted_files:
            return
        
        report_path = f"plex_deletions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'deletion_date': datetime.now().isoformat(),
            'total_deleted': len(self.deleted_files),
            'cleaned_dirs': 0,
            'cleaned_plex_entries': getattr(self, 'cleaned_plex_entries', 0),
            'deleted_files': self.deleted_files,
            'config': self.config
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📋 Rapport sauvegardé: {report_path}")
    
    def cleanup_plex_database(self, deleted_files: List[Dict]) -> int:
        """Nettoie la base de données Plex des fichiers supprimés"""
        if not deleted_files:
            return 0
        
        cleaned_entries = 0
        
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                for file_info in deleted_files:
                    file_path = file_info['file_path']
                    
                    # Supprimer l'entrée media_parts (fichier physique)
                    cursor.execute("""
                        DELETE FROM media_parts 
                        WHERE file = ?
                    """, (file_path,))
                    
                    # Si media_parts supprimé, vérifier si media_item est orphelin
                    # et supprimer metadata_item si nécessaire
                    cursor.execute("""
                        SELECT mi.id, mi.title
                        FROM metadata_items mi
                        LEFT JOIN media_items media ON mi.id = media.metadata_item_id
                        LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                        WHERE mi.metadata_type = 10
                        AND mp.file IS NULL
                        AND mi.id = (
                            SELECT mi2.id FROM metadata_items mi2
                            JOIN media_items media2 ON mi2.id = media2.metadata_item_id
                            JOIN media_parts mp2 ON media2.id = mp2.media_item_id
                            WHERE mp2.file = ?
                        )
                    """, (file_path,))
                    
                    orphaned_items = cursor.fetchall()
                    
                    for item_id, title in orphaned_items:
                        # Supprimer les settings utilisateur
                        cursor.execute("DELETE FROM metadata_item_settings WHERE guid IN (SELECT guid FROM metadata_items WHERE id = ?)", (item_id,))
                        
                        # Supprimer media_items
                        cursor.execute("DELETE FROM media_items WHERE metadata_item_id = ?", (item_id,))
                        
                        # Supprimer metadata_item
                        cursor.execute("DELETE FROM metadata_items WHERE id = ?", (item_id,))
                        
                        cleaned_entries += 1
                        self.logger.info(f"🗃️ Entrée Plex nettoyée: {title}")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage de la base Plex: {e}")
            return 0
        
        return cleaned_entries

    def cleanup_old_logs(self, days_to_keep: int) -> Dict:
        """Nettoie les logs plus anciens que X jours"""
        import glob
        from pathlib import Path
        
        cleaned_logs = {'plex_ratings': 0, 'plex_daily': 0, 'plex_monthly': 0, 'reports': 0, 'total': 0}
        
        if days_to_keep < 0:
            return cleaned_logs
        
        # Répertoires de logs à nettoyer
        log_dirs = [
            Path.home() / 'logs' / 'plex_ratings',
            Path.home() / 'logs' / 'plex_daily', 
            Path.home() / 'logs' / 'plex_monthly'
        ]
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
                
            # Trouver tous les fichiers .log dans ce répertoire
            log_files = list(log_dir.glob('*.log'))
            
            dir_name = log_dir.name
            for log_file in log_files:
                try:
                    # Vérifier la date de modification du fichier
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        log_file.unlink()
                        cleaned_logs[dir_name] += 1
                        cleaned_logs['total'] += 1
                        self.logger.info(f"🗑️ Log supprimé: {log_file}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la suppression de {log_file}: {e}")
        
        # Nettoyer aussi les logs dans le répertoire courant
        current_dir = Path('.')
        current_log_files = list(current_dir.glob('plex_ratings_sync_*.log'))
        
        for log_file in current_log_files:
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    cleaned_logs['plex_ratings'] += 1
                    cleaned_logs['total'] += 1
                    self.logger.info(f"🗑️ Log supprimé: {log_file}")
            except Exception as e:
                self.logger.warning(f"Erreur lors de la suppression de {log_file}: {e}")
        
        # Nettoyer aussi les rapports de suppressions
        reports_dir = Path('.')
        report_files = list(reports_dir.glob('plex_deletions_*.json'))
        
        for report_file in report_files:
            try:
                file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    report_file.unlink()
                    cleaned_logs['reports'] += 1
                    cleaned_logs['total'] += 1
                    self.logger.info(f"🗑️ Rapport supprimé: {report_file}")
            except Exception as e:
                self.logger.warning(f"Erreur lors de la suppression de {report_file}: {e}")
        
        return cleaned_logs

def find_plex_database():
    """Trouve automatiquement la base de données Plex"""
    possible_paths = [
        # Snap installation (plus courant maintenant)
        Path("/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"),
        # Linux standard
        Path.home() / ".config/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
        Path("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"),
        # macOS
        Path.home() / "Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
        # Windows
        Path.home() / "AppData/Local/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    return None

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(
        description='Synchronise les évaluations Plex avec la bibliothèque audio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    # Simulation (par défaut) - supprime 1⭐, scanne 2⭐
    python3 plex_ratings_sync.py --auto-find-db

    # Suppression réelle des fichiers avec 1 étoile + scan 2 étoiles
    python3 plex_ratings_sync.py --auto-find-db --delete

    # Avec sauvegarde avant suppression
    python3 plex_ratings_sync.py --auto-find-db --delete --backup ./backup

    # Supprimer également les albums avec 1 étoile
    python3 plex_ratings_sync.py --auto-find-db --delete --delete-albums

    # Supprimer également les artistes avec 1 étoile
    python3 plex_ratings_sync.py --auto-find-db --delete --delete-artists

    # Supprimer les albums avec 2 étoiles
    python3 plex_ratings_sync.py --auto-find-db --delete --delete-albums --rating 2

    # Voir les statistiques des ratings
    python3 plex_ratings_sync.py --auto-find-db --stats
        """
    )
    
    parser.add_argument(
        '--plex-db', '--plex-database',
        type=str,
        help='Chemin vers la base de données Plex (com.plexapp.plugins.library.db)'
    )
    
    parser.add_argument(
        '--delete', '--real',
        action='store_true',
        help='Effectue la suppression réelle (défaut: simulation)'
    )
    
    parser.add_argument(
        '--rating', '--target-rating',
        type=float,
        default=1.0,
        help='Rating cible pour albums/artistes (1-5 étoiles, défaut: 1). Les pistes 1⭐ sont toujours supprimées, 2⭐ toujours scannées.'
    )
    
    parser.add_argument(
        '--backup', '--backup-dir',
        type=str,
        help='Répertoire de sauvegarde avant suppression'
    )
    
    parser.add_argument(
        '--stats', '--statistics',
        action='store_true',
        help='Affiche les statistiques des ratings et quitte'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mode verbeux'
    )
    
    parser.add_argument(
        '--auto-find-db',
        action='store_true',
        help='Recherche automatiquement la base Plex'
    )
    
    parser.add_argument(
        '--delete-albums',
        action='store_true',
        help='Supprime également les albums avec le rating cible'
    )
    
    parser.add_argument(
        '--delete-artists',
        action='store_true',
        help='Supprime également les artistes avec le rating cible'
    )
    
    parser.add_argument(
        '--cleanup-logs',
        type=int,
        metavar='DAYS',
        help='Supprime les logs plus anciens que X jours (0 = tous les logs)'
    )
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    args = parse_arguments()
    
    # Déterminer le chemin de la base Plex
    plex_db_path = args.plex_db
    
    if args.auto_find_db or not plex_db_path:
        auto_path = find_plex_database()
        if auto_path:
            plex_db_path = auto_path
            print(f"🔍 Base Plex trouvée automatiquement: {plex_db_path}")
        elif not plex_db_path:
            print("❌ Base de données Plex introuvable automatiquement.")
            print("Utilisez --plex-db pour spécifier le chemin manuellement.")
            sys.exit(1)
    
    # Configuration
    config = {
        'target_rating': args.rating,
        'backup_dir': args.backup,
        'log_level': 'DEBUG' if args.verbose else 'INFO',
        'dry_run': not args.delete
    }
    
    # Initialiser le synchroniseur
    try:
        syncer = PlexRatingsSync(plex_db_path, config)
        
        # Mode statistiques
        if args.stats:
            syncer.show_rating_statistics()
            return
        
        # Mode nettoyage des logs
        if args.cleanup_logs is not None:
            print(f"🧹 Nettoyage des logs plus anciens que {args.cleanup_logs} jour(s)...")
            cleaned_logs = syncer.cleanup_old_logs(args.cleanup_logs)
            print(f"✅ Nettoyage terminé:")
            print(f"    📝 Logs plex_ratings supprimés: {cleaned_logs['plex_ratings']}")
            print(f"    📅 Logs plex_daily supprimés: {cleaned_logs['plex_daily']}")
            print(f"    📊 Logs plex_monthly supprimés: {cleaned_logs['plex_monthly']}")
            print(f"    📋 Rapports supprimés: {cleaned_logs.get('reports', 0)}")
            print(f"    🗑️ Total supprimé: {cleaned_logs['total']}")
            return
        
        # Avertissements de sécurité
        if args.delete:
            print(f"⚠️  ATTENTION: Mode suppression réelle activé!")
            print(f"⭐ Les fichiers avec 1 étoile seront DÉFINITIVEMENT supprimés")
            print(f"🎧 Les fichiers avec 2 étoiles seront identifiés avec songrec (conservés)")
            if args.delete_albums:
                print(f"💿 Les albums avec {args.rating} étoile(s) seront également supprimés")
            if args.delete_artists:
                print(f"🎤 Les artistes avec {args.rating} étoile(s) seront également supprimés")
            if args.backup:
                print(f"💾 Sauvegarde activée: {args.backup}")
            else:
                print("❌ AUCUNE sauvegarde configurée!")
            
            confirm = input("\nÊtes-vous sûr de continuer ? (tapez 'OUI', 'O', 'YES' ou 'Y'): ")
            valid_responses = ['OUI', 'O', 'YES', 'Y', 'oui', 'o', 'yes', 'y']
            if confirm.upper() not in [resp.upper() for resp in valid_responses]:
                print("Opération annulée.")
                return
        
        # Lancer la synchronisation
        result = syncer.sync_ratings(
            dry_run=not args.delete,
            backup_dir=args.backup,
            delete_albums=args.delete_albums,
            delete_artists=args.delete_artists
        )
        
        # Sauvegarder le rapport si des suppressions ont eu lieu
        if args.delete and syncer.deleted_files:
            syncer.save_deletion_report()
        
        if not result['success']:
            print(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n⏹️ Opération interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()