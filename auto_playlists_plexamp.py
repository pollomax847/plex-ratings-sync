#!/home/paulceline/bin/plex-ratings-sync/.venv/bin/python3
"""
Générateur de playlists automatiques pour PlexAmp
Crée des playlists intelligentes basées sur différents critères
"""

import sqlite3
import json
import sys
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import random
import time

class PlexAmpAutoPlaylist:
    def export_playlists_m3u(self, playlists: Dict[str, List[Dict]], export_dir: str):
        """Exporte chaque playlist au format M3U dans le dossier export_dir."""
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        for name, tracks in playlists.items():
            # Nettoyer le nom pour le fichier
            file_name = name.replace(' ', '_').replace('★', 'star').replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('ç', 'c').replace('œ', 'oe').replace('(', '').replace(')', '').replace('🧘', 'zen').replace('⚡', 'energy').replace('🔥', 'top').replace('❤️', 'fav').replace('🔍', 'discover').replace('🆕', 'new').replace('🏆', 'topmonth').replace('🔁', 'review').replace('🧹', 'clean').replace('🎵', 'genre').replace('🕰️', 'decade').replace('🔎', 'discover2').replace('Unknown', 'inconnu')
            file_name = ''.join(c for c in file_name if c.isalnum() or c in ['_', '-'])
            m3u_path = export_path / f"{file_name}.m3u"
            with open(m3u_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for track in tracks:
                    if track.get('file_path'):
                        # Chemin relatif depuis le dossier Playlists
                        try:
                            rel_path = str(Path(track['file_path']).relative_to(export_path.parent))
                        except Exception:
                            rel_path = track['file_path']  # fallback: chemin absolu
                        f.write(rel_path + "\n")
            self.logger.info(f"✅ Playlist exportée: {m3u_path}")
    def __init__(self, plex_db_path: str, verbose: bool = False):
        self.plex_db_path = Path(plex_db_path)
        self.verbose = verbose
        self.setup_logging()
        
    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def get_track_data(self) -> List[Dict]:
        """Récupère toutes les données des pistes avec métadonnées enrichies"""
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT DISTINCT
                    mi.id,
                    mi.title as track_title,
                    mi.year,
                    mi.originally_available_at,
                    mi.duration,
                    mis.rating as user_rating,
                    mis.view_count as play_count,
                    mis.last_viewed_at,
                    mis.created_at as added_at,
                    albums.title as album_title,
                    artists.title as artist_name,
                    genres.tag as genre,
                    mp.file as file_path
                FROM metadata_items mi
                LEFT JOIN metadata_item_settings mis ON mi.id = mis.guid
                LEFT JOIN metadata_items albums ON mi.parent_id = albums.id
                LEFT JOIN metadata_items artists ON albums.parent_id = artists.id
                LEFT JOIN taggings ON mi.id = taggings.metadata_item_id
                LEFT JOIN tags genres ON taggings.tag_id = genres.id AND genres.tag_type = 1
                JOIN media_items mitem ON mi.id = mitem.metadata_item_id
                JOIN media_parts mp ON mitem.id = mp.media_item_id
                WHERE mi.metadata_type = 10
                AND mp.file IS NOT NULL
                ORDER BY mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                tracks = []
                for row in rows:
                    track = {
                        'id': row[0],
                        'title': row[1] or 'Unknown',
                        'year': row[2],
                        'release_date': row[3],
                        'duration_ms': row[4] or 0,
                        'rating': row[5] or 0,
                        'play_count': row[6] or 0,
                        'last_played': row[7],
                        'date_added': row[8],
                        'album': row[9] or 'Unknown Album',
                        'artist': row[10] or 'Unknown Artist',
                        'genre': row[11] or 'Unknown',
                        'file_path': row[12]
                    }
                    tracks.append(track)
                
                self.logger.info(f"📊 {len(tracks)} pistes chargées")
                return tracks
                
        except Exception as e:
            self.logger.error(f"❌ Erreur base de données: {e}")
            return []

    def create_rating_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists par note (5★, 4★, etc.)"""
        rating_playlists = {}
        
        for rating in [5, 4, 3, 2, 1]:
            rated_tracks = [t for t in tracks if t['rating'] == rating * 2]  # Plex utilise 1-10
            if rated_tracks:
                playlist_name = f"⭐ {rating} étoiles ({len(rated_tracks)} titres)"
                rating_playlists[playlist_name] = rated_tracks
                
        return rating_playlists

    def create_year_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists par décennie/année"""
        year_playlists = {}
        
        # Par décennie
        decades = {}
        for track in tracks:
            if track['year']:
                decade = (track['year'] // 10) * 10
                if decade not in decades:
                    decades[decade] = []
                decades[decade].append(track)
        
        for decade, decade_tracks in decades.items():
            if len(decade_tracks) >= 10:  # Au moins 10 titres
                playlist_name = f"🕰️ Années {decade}s ({len(decade_tracks)} titres)"
                year_playlists[playlist_name] = decade_tracks
        
        # Années récentes (5 dernières années)
        current_year = datetime.datetime.now().year
        recent_tracks = [t for t in tracks if t['year'] and t['year'] >= current_year - 5]
        if recent_tracks:
            year_playlists[f"🆕 Récents ({len(recent_tracks)} titres)"] = recent_tracks
        
        return year_playlists

    def create_genre_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists par genre"""
        genre_playlists = {}
        
        # Grouper par genre
        genres = {}
        for track in tracks:
            genre = track['genre']
            if genre not in genres:
                genres[genre] = []
            genres[genre].append(track)
        
        # Créer playlists pour les genres avec assez de contenu
        for genre, genre_tracks in genres.items():
            if len(genre_tracks) >= 15 and genre != 'Unknown':  # Au moins 15 titres
                playlist_name = f"🎵 {genre} ({len(genre_tracks)} titres)"
                genre_playlists[playlist_name] = genre_tracks
        
        return genre_playlists

    def create_smart_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists intelligentes basées sur l'écoute"""
        smart_playlists = {}
        
        # Les plus écoutés
        most_played = sorted([t for t in tracks if t['play_count'] > 0], 
                            key=lambda x: x['play_count'], reverse=True)[:100]
        if most_played:
            smart_playlists[f"🔥 Top 100 plus écoutés"] = most_played
        
        # Favoris (5★ + beaucoup écoutés)
        favorites = [t for t in tracks if t['rating'] >= 8 and t['play_count'] >= 3]
        if favorites:
            smart_playlists[f"❤️ Mes favoris ({len(favorites)} titres)"] = favorites
        
        # Découverte (peu/pas écoutés, bien notés)
        discovery = [t for t in tracks if t['play_count'] <= 1 and t['rating'] >= 6]
        if discovery:
            smart_playlists[f"🔍 À redécouvrir ({len(discovery)} titres)"] = discovery
        
        # Récemment ajoutés (30 derniers jours)
        now = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        recently_added = [t for t in tracks if t['date_added'] and 
                         (now - t['date_added']) <= thirty_days]
        if recently_added:
            smart_playlists[f"🆕 Ajoutés récemment ({len(recently_added)} titres)"] = recently_added
        
        # Mix de l'humeur - titres longs pour se concentrer
        long_tracks = [t for t in tracks if t['duration_ms'] >= 300000 and t['rating'] >= 6]  # >5min
        if long_tracks:
            random.shuffle(long_tracks)
            smart_playlists[f"🧘 Mix concentration ({len(long_tracks[:50])} titres)"] = long_tracks[:50]
        
        # Mix énergique - titres courts et bien notés
        energy_tracks = [t for t in tracks if t['duration_ms'] <= 240000 and t['rating'] >= 8]  # <4min
        if energy_tracks:
            random.shuffle(energy_tracks)
            smart_playlists[f"⚡ Mix énergique ({len(energy_tracks[:50])} titres)"] = energy_tracks[:50]
        
        return smart_playlists

    def create_discovery_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée une playlist 'Découvertes' pour les pistes 2★ peu écoutées"""
        discovery_playlists = {}
        # Plex uses 1-10 scale in DB; 2★ ~ 4
        discoveries = [t for t in tracks if t['rating'] == 4 and t['play_count'] <= 1]
        if discoveries:
            discovery_playlists[f"🔎 Découvertes (2★) ({len(discoveries)} titres)"] = discoveries
        return discovery_playlists

    def create_top_this_month(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Créer une playlist 'Top This Month' pour nouveaux 4-5★"""
        top_playlists = {}
        now = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        recent_high_rated = [t for t in tracks if t['date_added'] and (now - t['date_added']) <= thirty_days and t['rating'] >= 8]
        if recent_high_rated:
            top_playlists[f"🏆 Top du mois ({len(recent_high_rated)} titres)"] = recent_high_rated
        return top_playlists

    def create_to_review_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Créer une playlist 'À réévaluer' pour pistes 3★ avec beaucoup d'écoutes"""
        to_review = [t for t in tracks if t['rating'] == 6 and t['play_count'] >= 20]
        playlists = {}
        if to_review:
            playlists[f"🔁 À réévaluer (3★, >20 plays) ({len(to_review)} titres)"] = to_review
        return playlists

    def create_cleanup_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Créer une playlist de nettoyage (0 plays en 6 mois)"""
        cleanup_playlists = {}
        six_months = 6 * 30 * 24 * 60 * 60
        now = int(time.time())
        candidates = []
        for t in tracks:
            last_played = t.get('last_played')
            if last_played is None and t.get('date_added') and (now - t['date_added']) >= six_months:
                candidates.append(t)
            elif last_played and (now - last_played) >= six_months:
                candidates.append(t)
        if candidates:
            cleanup_playlists[f"🧹 Nettoyage (0 plays, 6+ mois) ({len(candidates)} titres)"] = candidates
        return cleanup_playlists

    def create_artist_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists des meilleurs titres par artiste"""
        artist_playlists = {}
        
        # Grouper par artiste
        artists = {}
        for track in tracks:
            artist = track['artist']
            if artist not in artists:
                artists[artist] = []
            artists[artist].append(track)
        
        # Pour les artistes avec beaucoup de contenu, créer des "Best Of"
        for artist, artist_tracks in artists.items():
            if len(artist_tracks) >= 20 and artist != 'Unknown Artist':
                # Trier par note puis nombre d'écoutes
                best_tracks = sorted(artist_tracks, 
                                   key=lambda x: (x['rating'], x['play_count']), 
                                   reverse=True)[:25]
                playlist_name = f"🎤 Best of {artist} ({len(best_tracks)} titres)"
                artist_playlists[playlist_name] = best_tracks
        
        return artist_playlists

    def save_playlist_to_plex(self, playlist_name: str, tracks: List[Dict]) -> bool:
        """Sauvegarde une playlist dans Plex"""
        try:
            with sqlite3.connect(str(self.plex_db_path)) as conn:
                cursor = conn.cursor()
                
                # Vérifier si la playlist existe déjà
                cursor.execute("""
                    SELECT id FROM metadata_items 
                    WHERE title = ? AND metadata_type = 15
                """, (playlist_name,))
                
                existing = cursor.fetchone()
                if existing:
                    # Supprimer l'ancienne playlist
                    playlist_id = existing[0]
                    cursor.execute("DELETE FROM playlist_items WHERE playlist_id = ?", (playlist_id,))
                    cursor.execute("DELETE FROM metadata_items WHERE id = ?", (playlist_id,))
                
                # Créer la nouvelle playlist
                cursor.execute("""
                    INSERT INTO metadata_items (
                        metadata_type, library_section_id, guid, title, 
                        created_at, updated_at
                    ) VALUES (15, 1, ?, ?, ?, ?)
                """, (
                    f"com.plexapp.agents.localmedia://playlist/{int(time.time())}",
                    playlist_name,
                    int(time.time()),
                    int(time.time())
                ))
                
                playlist_id = cursor.lastrowid
                
                # Ajouter les pistes
                for i, track in enumerate(tracks):
                    cursor.execute("""
                        INSERT INTO playlist_items (playlist_id, metadata_item_id, "order")
                        VALUES (?, ?, ?)
                    """, (playlist_id, track['id'], i))
                
                conn.commit()
                self.logger.info(f"✅ Playlist créée: {playlist_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erreur playlist {playlist_name}: {e}")
            return False

    def generate_all_playlists(self, save_to_plex: bool = True) -> Dict[str, int]:
        """Génère toutes les playlists automatiques"""
        self.logger.info("🎵 Génération des playlists automatiques PlexAmp")
        
        # Charger les données
        tracks = self.get_track_data()
        if not tracks:
            self.logger.error("❌ Aucune piste trouvée")
            return {}
        
        # Générer toutes les playlists
        all_playlists = {}
        
        # Playlists par note
        rating_playlists = self.create_rating_playlists(tracks)
        all_playlists.update(rating_playlists)
        
        # Playlists par année/décennie
        year_playlists = self.create_year_playlists(tracks)
        all_playlists.update(year_playlists)
        
        # Playlists par genre
        genre_playlists = self.create_genre_playlists(tracks)
        all_playlists.update(genre_playlists)
        
        # Playlists intelligentes
        smart_playlists = self.create_smart_playlists(tracks)
        all_playlists.update(smart_playlists)
        
        # Playlists d'artistes
        artist_playlists = self.create_artist_playlists(tracks)
        all_playlists.update(artist_playlists)

        # Playlists supplémentaires demandées
        discovery_playlists = self.create_discovery_playlists(tracks)
        all_playlists.update(discovery_playlists)

        # Playlists AI spéciales
        funk_keywords = ['funk', 'disco', 'groove', 'boogie', 'soul', 'dance']
        funk_tracks = [t for t in tracks if any(k in t['genre'].lower() or k in t['album'].lower() or k in t['title'].lower() for k in funk_keywords)]
        all_playlists['Funk_Disco'] = funk_tracks

        workout_keywords = ['workout', 'run', 'energy', 'cardio', 'power', 'training', 'remix', 'electro', 'dance', 'upbeat']
        workout_tracks = [t for t in tracks if any(k in t['genre'].lower() or k in t['album'].lower() or k in t['title'].lower() for k in workout_keywords)]
        all_playlists['Running_Workout'] = workout_tracks

        drive_keywords = ['road', 'drive', 'car', 'party', 'night', 'club', 'festival', 'hit', 'anthem', 'summer', 'mix', 'dance', 'pop', 'electro', 'rock']
        drive_tracks = [t for t in tracks if any(k in t['genre'].lower() or k in t['album'].lower() or k in t['title'].lower() for k in drive_keywords)]
        all_playlists['Conduite_Fetes'] = drive_tracks

        top_month_playlists = self.create_top_this_month(tracks)
        all_playlists.update(top_month_playlists)

        to_review_playlists = self.create_to_review_playlists(tracks)
        all_playlists.update(to_review_playlists)

        cleanup_playlists = self.create_cleanup_playlists(tracks)
        all_playlists.update(cleanup_playlists)

        # Statistiques et export
        created_count = 0
        results = {}

        # Sauvegarder dans Plex si demandé
        if save_to_plex:
            for playlist_name, playlist_tracks in all_playlists.items():
                if self.save_playlist_to_plex(playlist_name, playlist_tracks):
                    created_count += 1
                    results[playlist_name] = len(playlist_tracks)
        else:
            # Mode simulation
            for playlist_name, playlist_tracks in all_playlists.items():
                self.logger.info(f"📋 {playlist_name}: {len(playlist_tracks)} titres")
                results[playlist_name] = len(playlist_tracks)
        self.logger.info(f"\n🎉 {created_count if save_to_plex else len(all_playlists)} playlists {'créées' if save_to_plex else 'simulées'}")
        return results
        return results

def main():
    parser = argparse.ArgumentParser(description="Générateur de playlists automatiques PlexAmp")
    parser.add_argument("--plex-db", 
                       default="/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db",
                       help="Chemin vers la base de données Plex")
    parser.add_argument("--dry-run", action="store_true",
                       help="Mode simulation (ne crée pas les playlists)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Créer le générateur
    generator = PlexAmpAutoPlaylist(args.plex_db, verbose=args.verbose)
    
    # Générer toutes les playlists
    tracks = generator.get_track_data()
    all_playlists = {}
    all_playlists.update(generator.create_rating_playlists(tracks))
    all_playlists.update(generator.create_year_playlists(tracks))
    all_playlists.update(generator.create_genre_playlists(tracks))
    all_playlists.update(generator.create_smart_playlists(tracks))
    all_playlists.update(generator.create_discovery_playlists(tracks))
    all_playlists.update(generator.create_top_this_month(tracks))
    all_playlists.update(generator.create_to_review_playlists(tracks))
    all_playlists.update(generator.create_cleanup_playlists(tracks))
    all_playlists.update(generator.create_artist_playlists(tracks))

    # Export automatique dans Playlists
    generator.export_playlists_m3u(all_playlists, '/mnt/mybook/Musiques/Playlists')

    # Afficher le résumé
    print("\n📊 RÉSUMÉ DES PLAYLISTS:")
    print("=" * 50)
    for playlist_name, tracks in all_playlists.items():
        print(f"  {playlist_name}: {len(tracks)} titres")

if __name__ == "__main__":
    main()