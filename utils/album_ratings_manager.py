#!/usr/bin/env python3
"""
Script étendu pour gérer les ratings au niveau des albums ET des pistes
Permet de traiter des albums entiers basés sur leur rating
"""

import sqlite3
import json
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

from logging_utils import get_audio_logger, cleanup_all_logs

class PlexAlbumRatingsManager:
    def __init__(self, plex_db_path: str, logger=None):
        self.plex_db_path = plex_db_path
        self.logger = logger or logging.getLogger()
        
    def get_album_ratings(self) -> List[Dict]:
        """Extrait les albums avec leurs ratings"""
        albums_with_ratings = []
        
        try:
            with sqlite3.connect(self.plex_db_path) as conn:
                cursor = conn.cursor()
                
                # Requête pour obtenir les albums avec ratings
                query = """
                SELECT DISTINCT
                    album_mi.id as album_id,
                    album_mi.title as album_title,
                    artist_mi.title as artist_name,
                    album_mis.rating as album_rating,
                    COUNT(track_mi.id) as track_count
                FROM metadata_items album_mi
                LEFT JOIN metadata_items artist_mi ON album_mi.parent_id = artist_mi.id
                LEFT JOIN metadata_item_settings album_mis ON album_mi.guid = album_mis.guid
                LEFT JOIN metadata_items track_mi ON track_mi.parent_id = album_mi.id
                WHERE album_mi.metadata_type = 9  -- Type 9 = Album
                AND album_mis.rating IS NOT NULL
                GROUP BY album_mi.id, album_mi.title, artist_mi.title, album_mis.rating
                ORDER BY album_mis.rating, artist_mi.title, album_mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    album_id, album_title, artist_name, album_rating, track_count = row
                    
                    # Normaliser le rating (Plex utilise 0-10, on veut 0-5)
                    final_rating = album_rating
                    if final_rating:
                        final_rating = final_rating / 2  # Toujours diviser par 2
                    
                    albums_with_ratings.append({
                        'album_id': album_id,
                        'album_title': album_title or 'Unknown Album',
                        'artist_name': artist_name or 'Unknown Artist',
                        'rating': final_rating,
                        'track_count': track_count
                    })
                
                self.logger.info(f"✅ Trouvé {len(albums_with_ratings)} albums avec ratings")
                return albums_with_ratings
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la lecture des ratings d'albums: {e}")
            return []
    
    def get_album_tracks(self, album_id: int) -> List[Dict]:
        """Obtient tous les fichiers d'un album"""
        album_tracks = []
        
        try:
            with sqlite3.connect(self.plex_db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    track_mi.id as track_id,
                    track_mi.title as track_title,
                    track_mi.[index] as track_number,
                    mp.file as file_path,
                    track_mis.rating as track_rating,
                    track_mis.view_count as play_count
                FROM metadata_items track_mi
                LEFT JOIN media_items media ON track_mi.id = media.metadata_item_id
                LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                LEFT JOIN metadata_item_settings track_mis ON track_mi.guid = track_mis.guid
                WHERE track_mi.parent_id = ?
                AND track_mi.metadata_type = 10  -- Type 10 = Track
                AND mp.file IS NOT NULL
                ORDER BY track_mi.[index]
                """
                
                cursor.execute(query, (album_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    track_id, track_title, track_number, file_path, track_rating, play_count = row
                    
                    # Normaliser le rating de la piste si elle en a un  
                    track_final_rating = None
                    if track_rating:
                        track_final_rating = track_rating / 2  # Toujours diviser par 2
                    
                    album_tracks.append({
                        'track_id': track_id,
                        'track_title': track_title or 'Unknown Track',
                        'track_number': track_number or 0,
                        'file_path': file_path,
                        'track_rating': track_final_rating,
                        'play_count': play_count or 0
                    })
                
                return album_tracks
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la lecture des pistes de l'album {album_id}: {e}")
            return []
    
    def process_album_ratings(self, output_dir: str) -> Dict:
        """Traite tous les albums avec ratings et génère les listes de fichiers"""
        
        # Obtenir tous les albums avec ratings
        albums = self.get_album_ratings()
        
        # Listes pour les différents types de traitement
        albums_1_star = []
        albums_2_star = []
        albums_sync_rating = []
        
        # Fichiers individuels (héritage du système existant)
        files_1_star = []
        files_2_star = []
        files_sync_rating = []
        
        for album in albums:
            rating = album['rating']
            album_tracks = self.get_album_tracks(album['album_id'])
            
            # Ajouter les informations des pistes à l'album
            album['tracks'] = album_tracks
            album['files'] = [track['file_path'] for track in album_tracks if track['file_path']]
            
            self.logger.info(f"📀 Album: {album['artist_name']} - {album['album_title']} ({rating}⭐) - {len(album['files'])} fichiers")
            
            if rating == 1.0:
                albums_1_star.append(album)
                # Ajouter aussi les fichiers individuels pour compatibilité
                for track in album_tracks:
                    if track['file_path']:
                        files_1_star.append({
                            'file_path': track['file_path'],
                            'rating': rating,
                            'play_count': track['play_count'],
                            'track_title': track['track_title'],
                            'album_title': album['album_title'],
                            'artist_name': album['artist_name'],
                            'source': 'album_rating'  # Identifier la source du rating
                        })
                        
            elif rating == 2.0:
                albums_2_star.append(album)
                for track in album_tracks:
                    if track['file_path']:
                        files_2_star.append({
                            'file_path': track['file_path'],
                            'rating': rating,
                            'play_count': track['play_count'],
                            'track_title': track['track_title'],
                            'album_title': album['album_title'],
                            'artist_name': album['artist_name'],
                            'source': 'album_rating'
                        })
                        
            elif rating in [3.0, 4.0, 5.0]:
                albums_sync_rating.append(album)
                for track in album_tracks:
                    if track['file_path']:
                        files_sync_rating.append({
                            'file_path': track['file_path'],
                            'rating': rating,
                            'play_count': track['play_count'],
                            'track_title': track['track_title'],
                            'album_title': album['album_title'],
                            'artist_name': album['artist_name'],
                            'source': 'album_rating'
                        })
        
        # Maintenant, traiter les pistes individuelles (qui ont leur propre rating, pas d'album)
        individual_tracks = self.get_individual_track_ratings()
        
        for track in individual_tracks:
            rating = track['rating']
            
            if rating == 1.0:
                files_1_star.append({**track, 'source': 'track_rating'})
            elif rating == 2.0:
                files_2_star.append({**track, 'source': 'track_rating'})
            elif rating in [3.0, 4.0, 5.0]:
                files_sync_rating.append({**track, 'source': 'track_rating'})
        
        # Sauvegarder tous les résultats
        output_path = Path(output_dir)
        
        # Albums par rating
        self.logger.save_json_report(albums_1_star, 'albums_1_star.json')
        self.logger.save_json_report(albums_2_star, 'albums_2_star.json')
        self.logger.save_json_report(albums_sync_rating, 'albums_sync_rating.json')
        
        # Fichiers individuels (compatibilité avec le système existant)
        self.logger.save_json_report(files_1_star, 'files_1_star.json')
        self.logger.save_json_report(files_2_star, 'files_2_star.json')
        self.logger.save_json_report(files_sync_rating, 'files_sync_rating.json')
        
        # Statistiques
        stats = {
            'albums_1_star': len(albums_1_star),
            'albums_2_star': len(albums_2_star),
            'albums_sync_rating': len(albums_sync_rating),
            'files_1_star_total': len(files_1_star),
            'files_2_star_total': len(files_2_star),
            'files_sync_rating_total': len(files_sync_rating),
            'files_from_albums_1_star': len([f for f in files_1_star if f['source'] == 'album_rating']),
            'files_from_albums_2_star': len([f for f in files_2_star if f['source'] == 'album_rating']),
            'files_from_tracks_1_star': len([f for f in files_1_star if f['source'] == 'track_rating']),
            'files_from_tracks_2_star': len([f for f in files_2_star if f['source'] == 'track_rating'])
        }
        
        self.logger.save_json_report(stats, 'ratings_stats.json')
        
        self.logger.info(f"\n📊 Résumé :")
        self.logger.info(f"   📀 Albums 1⭐: {stats['albums_1_star']} ({stats['files_from_albums_1_star']} fichiers)")
        self.logger.info(f"   📀 Albums 2⭐: {stats['albums_2_star']} ({stats['files_from_albums_2_star']} fichiers)")
        self.logger.info(f"   🎵 Pistes seules 1⭐: {stats['files_from_tracks_1_star']}")
        self.logger.info(f"   🎵 Pistes seules 2⭐: {stats['files_from_tracks_2_star']}")
        self.logger.info(f"   📁 Total fichiers 1⭐: {stats['files_1_star_total']}")
        self.logger.info(f"   📁 Total fichiers 2⭐: {stats['files_2_star_total']}")
        
        return stats
    
    def get_individual_track_ratings(self) -> List[Dict]:
        """Obtient les pistes qui ont leur propre rating (pas hérité de l'album)"""
        individual_tracks = []
        
        try:
            with sqlite3.connect(self.plex_db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    track_mi.title as track_title,
                    track_mis.rating as user_rating,
                    track_mis.view_count as play_count,
                    mp.file as file_path,
                    album_mi.title as album_title,
                    artist_mi.title as artist_name
                FROM metadata_items track_mi
                LEFT JOIN media_items media ON track_mi.id = media.metadata_item_id
                LEFT JOIN media_parts mp ON media.id = mp.media_item_id
                LEFT JOIN metadata_items album_mi ON track_mi.parent_id = album_mi.id
                LEFT JOIN metadata_items artist_mi ON album_mi.parent_id = artist_mi.id
                LEFT JOIN metadata_item_settings track_mis ON track_mi.guid = track_mis.guid
                LEFT JOIN metadata_item_settings album_mis ON album_mi.guid = album_mis.guid
                WHERE track_mi.metadata_type = 10
                AND mp.file IS NOT NULL
                AND track_mis.rating IS NOT NULL
                AND (album_mis.rating IS NULL OR album_mis.rating != track_mis.rating)  -- Piste a un rating différent de l'album
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    track_title, user_rating, play_count, file_path, album_title, artist_name = row
                    
                    final_rating = user_rating
                    if final_rating:
                        final_rating = final_rating / 2  # Toujours diviser par 2
                    
                    individual_tracks.append({
                        'file_path': file_path,
                        'rating': final_rating,
                        'play_count': play_count or 0,
                        'track_title': track_title or 'Unknown',
                        'album_title': album_title or 'Unknown Album',
                        'artist_name': artist_name or 'Unknown Artist'
                    })
                
                self.logger.info(f"✅ Trouvé {len(individual_tracks)} pistes avec ratings individuels")
                return individual_tracks
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la lecture des ratings de pistes individuelles: {e}")
            return []

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gérer les ratings d'albums et pistes Plex")
    parser.add_argument("plex_db_path", help="Chemin vers la base de données Plex")
    parser.add_argument("--log-dir", default="logs", help="Dossier pour les logs (défaut: logs)")
    parser.add_argument("--retention-days", type=int, default=30, help="Nombre de jours à garder les logs (défaut: 30)")
    
    args = parser.parse_args()
    
    # Configuration du logging
    logger = get_audio_logger("album_ratings_manager", args.log_dir, args.retention_days)
    cleanup_all_logs(args.log_dir, args.retention_days)
    
    plex_db_path = args.plex_db_path
    
    logger.info(f"🚀 Démarrage de l'analyse des ratings Plex")
    logger.info(f"   Base de données: {plex_db_path}")
    
    if not Path(plex_db_path).exists():
        logger.error(f"❌ Base de données Plex introuvable: {plex_db_path}")
        sys.exit(1)
    
    # Traiter les ratings
    manager = PlexAlbumRatingsManager(plex_db_path, logger)
    stats = manager.process_album_ratings(args.log_dir)
    
    logger.info(f"\n✅ Analyse terminée. Rapports sauvegardés dans: {args.log_dir}")

if __name__ == "__main__":
    main()