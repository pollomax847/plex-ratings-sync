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
from typing import List, Dict, Optional, Tuple, Any
import logging
import random
import time
import os
import unicodedata
import re
import urllib.request
import urllib.parse
import io
import xml.etree.ElementTree as ET

# Préfixe pour identifier les playlists auto-générées (évite collision Soundiiz)
AUTO_PLAYLIST_PREFIX = "[Auto] "

# Configuration API Plex
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400").rstrip("/")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "WQQySxr3SBPY-Sn77Yuk")
PLEX_MACHINE_ID = os.getenv("PLEX_MACHINE_ID", "e0c0f73d4bbd7109a0aad8c16b20db9da5ffa4c4")

class PlexAmpAutoPlaylist:
    DEFAULT_POSTER_STYLE: Dict[str, Any] = {
        "size": 600,
        "overlay_alpha": 100,
        "title_size": 44,
        "subtitle_size": 24,
        "emoji_size": 80,
        "title_start_y": 300,
        "title_line_step": 50,
        "text_padding": 60,
        "title_color": [255, 255, 255, 255],
        "title_shadow_color": [0, 0, 0, 180],
        "subtitle_color": [200, 200, 200, 220],
        "line_color": [255, 255, 255, 80],
        "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "emoji_font_path": "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "strip_auto_prefix": True,
        "strip_count_suffix": True,
        "default_emoji": "🎵",
        "default_colors": [[70, 70, 140], [120, 120, 220]],
        "themes": [],
    }

    def _safe_int(self, value: Any, fallback: int, low: int, high: int) -> int:
        try:
            out = int(value)
        except Exception:
            return fallback
        return max(low, min(high, out))

    def _parse_rgba(self, value: Any, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        if not isinstance(value, (list, tuple)) or len(value) not in (3, 4):
            return fallback
        vals = [self._safe_int(x, fallback[i], 0, 255) for i, x in enumerate(value[:4])]
        if len(vals) == 3:
            vals.append(fallback[3])
        return tuple(vals)

    def _parse_rgb(self, value: Any, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        rgba = self._parse_rgba(value, (fallback[0], fallback[1], fallback[2], 255))
        return rgba[0], rgba[1], rgba[2]

    def _normalize_style(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        style = dict(self.DEFAULT_POSTER_STYLE)
        style.update(raw or {})

        style["title_color"] = self._parse_rgba(style.get("title_color"), (255, 255, 255, 255))
        style["title_shadow_color"] = self._parse_rgba(style.get("title_shadow_color"), (0, 0, 0, 180))
        style["subtitle_color"] = self._parse_rgba(style.get("subtitle_color"), (200, 200, 200, 220))
        style["line_color"] = self._parse_rgba(style.get("line_color"), (255, 255, 255, 80))

        default_colors = style.get("default_colors", self.DEFAULT_POSTER_STYLE["default_colors"])
        if isinstance(default_colors, (list, tuple)) and len(default_colors) == 2:
            style["default_colors"] = [
                self._parse_rgb(default_colors[0], (70, 70, 140)),
                self._parse_rgb(default_colors[1], (120, 120, 220)),
            ]
        else:
            style["default_colors"] = [(70, 70, 140), (120, 120, 220)]

        style["size"] = self._safe_int(style.get("size"), 600, 256, 2000)
        style["overlay_alpha"] = self._safe_int(style.get("overlay_alpha"), 100, 0, 255)
        style["title_size"] = self._safe_int(style.get("title_size"), 44, 14, 200)
        style["subtitle_size"] = self._safe_int(style.get("subtitle_size"), 24, 10, 120)
        style["emoji_size"] = self._safe_int(style.get("emoji_size"), 80, 16, 300)
        style["title_start_y"] = self._safe_int(style.get("title_start_y"), 300, 20, 1800)
        style["title_line_step"] = self._safe_int(style.get("title_line_step"), 50, 10, 200)
        style["text_padding"] = self._safe_int(style.get("text_padding"), 60, 10, 400)

        themes = style.get("themes", [])
        norm_themes = []
        if isinstance(themes, list):
            for t in themes:
                if not isinstance(t, dict):
                    continue
                keywords = t.get("keywords", [])
                colors = t.get("colors", [])
                if not (isinstance(keywords, list) and keywords and isinstance(colors, list) and len(colors) == 2):
                    continue
                norm_themes.append({
                    "keywords": [str(k).lower() for k in keywords if str(k).strip()],
                    "match": str(t.get("match", "all")).lower(),
                    "emoji": str(t.get("emoji", "🎵")),
                    "colors": [
                        self._parse_rgb(colors[0], (80, 80, 160)),
                        self._parse_rgb(colors[1], (150, 150, 230)),
                    ],
                })
        style["themes"] = norm_themes
        return style

    def _load_poster_style(self) -> Dict[str, Any]:
        path = os.getenv("PLEX_POSTER_STYLE_CONFIG", "").strip()
        if not path:
            return self._normalize_style({})
        cfg_path = Path(path)
        if not cfg_path.exists():
            self.logger.warning(f"⚠️ Fichier style posters introuvable: {cfg_path} (style par défaut utilisé)")
            return self._normalize_style({})
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("le JSON doit être un objet")
            self.logger.info(f"🎨 Style posters chargé: {cfg_path}")
            return self._normalize_style(raw)
        except Exception as e:
            self.logger.warning(f"⚠️ Style posters invalide ({cfg_path}): {e} (style par défaut utilisé)")
            return self._normalize_style({})

    def _build_all_playlists(self, tracks: List[Dict], custom_config: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Construit le dictionnaire complet des playlists à générer."""
        all_playlists: Dict[str, List[Dict]] = {}

        # Playlists natives
        all_playlists.update(self.create_rating_playlists(tracks))
        all_playlists.update(self.create_year_playlists(tracks))
        all_playlists.update(self.create_genre_playlists(tracks))
        all_playlists.update(self.create_smart_playlists(tracks))
        all_playlists.update(self.create_discovery_playlists(tracks))
        all_playlists.update(self.create_top_this_month(tracks))
        all_playlists.update(self.create_to_review_playlists(tracks))
        all_playlists.update(self.create_cleanup_playlists(tracks))
        all_playlists.update(self.create_radio_playlists(tracks))
        all_playlists.update(self.create_stars80_playlist(tracks))
        all_playlists.update(self.create_top50_playlist(tracks))

        # Playlists thématiques par mots-clés (recherche dans tous les genres)
        def _match_keywords(track, keywords):
            searchable = ' '.join(track.get('genres', [track['genre']])).lower()
            searchable += ' ' + track['album'].lower() + ' ' + track['title'].lower()
            return any(k in searchable for k in keywords)

        funk_tracks = [t for t in tracks if _match_keywords(t, ['funk', 'disco', 'groove', 'boogie', 'soul'])]
        if funk_tracks:
            all_playlists[f'{AUTO_PLAYLIST_PREFIX}Funk & Disco ({len(funk_tracks)} titres)'] = funk_tracks

        workout_tracks = [t for t in tracks if _match_keywords(t, ['workout', 'running', 'cardio', 'power', 'training'])]
        if workout_tracks:
            all_playlists[f'{AUTO_PLAYLIST_PREFIX}Running & Workout ({len(workout_tracks)} titres)'] = workout_tracks

        # Playlists personnalisées depuis JSON (optionnel)
        all_playlists.update(self._load_custom_playlists_from_json(tracks, custom_config))
        return all_playlists

    def _track_search_blob(self, track: Dict) -> str:
        parts = [
            track.get('title', ''),
            track.get('artist', ''),
            track.get('album', ''),
            track.get('genre', ''),
            ' '.join(track.get('genres', [])),
        ]
        return ' '.join(parts).lower()

    def _filter_tracks_with_rule(self, tracks: List[Dict], rule: Dict) -> List[Dict]:
        """Filtre des pistes via une règle JSON simple."""
        include_any = [str(v).lower() for v in rule.get('include_any', [])]
        include_all = [str(v).lower() for v in rule.get('include_all', [])]
        exclude_any = [str(v).lower() for v in rule.get('exclude_any', [])]
        genres_any = [str(v).lower() for v in rule.get('genres_any', [])]

        min_rating = rule.get('min_rating')
        max_rating = rule.get('max_rating')
        min_plays = rule.get('min_play_count')
        max_plays = rule.get('max_play_count')
        limit = rule.get('limit')
        sort_by = str(rule.get('sort_by', 'play_count')).lower()

        out: List[Dict] = []
        for track in tracks:
            blob = self._track_search_blob(track)
            track_genres = [g.lower() for g in track.get('genres', [track.get('genre', 'Unknown')])]
            rating = track.get('rating', 0) or 0
            plays = track.get('play_count', 0) or 0

            if include_any and not any(tok in blob for tok in include_any):
                continue
            if include_all and not all(tok in blob for tok in include_all):
                continue
            if exclude_any and any(tok in blob for tok in exclude_any):
                continue
            if genres_any and not any(g in track_genres for g in genres_any):
                continue

            if min_rating is not None and rating < float(min_rating):
                continue
            if max_rating is not None and rating > float(max_rating):
                continue
            if min_plays is not None and plays < int(min_plays):
                continue
            if max_plays is not None and plays > int(max_plays):
                continue

            out.append(track)

        if sort_by == 'recent':
            out.sort(key=lambda t: t.get('added_at', ''), reverse=True)
        elif sort_by == 'rating':
            out.sort(key=lambda t: (t.get('rating', 0) or 0, t.get('play_count', 0) or 0), reverse=True)
        else:
            out.sort(key=lambda t: (t.get('play_count', 0) or 0, t.get('rating', 0) or 0), reverse=True)

        if isinstance(limit, int) and limit > 0:
            out = out[:limit]
        return out

    def _load_custom_playlists_from_json(self, tracks: List[Dict], config_path: Optional[str]) -> Dict[str, List[Dict]]:
        """Charge des playlists personnalisées depuis un fichier JSON.

        Format attendu:
        {
          "playlists": [
            {
              "name": "Nom playlist",
              "prefix_auto": true,
              "include_any": ["token1", "token2"],
              "exclude_any": ["live"],
              "genres_any": ["electronic", "pop/rock"],
              "min_rating": 3,
              "min_play_count": 5,
              "limit": 200,
              "sort_by": "play_count"
            }
          ]
        }
        """
        if not config_path:
            return {}

        path = Path(config_path)
        if not path.exists():
            self.logger.warning(f"⚠️ Config playlists personnalisées introuvable: {path}")
            return {}

        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            self.logger.error(f"❌ Impossible de lire {path}: {e}")
            return {}

        playlists = payload.get('playlists', [])
        if not isinstance(playlists, list):
            self.logger.error(f"❌ Format invalide dans {path}: 'playlists' doit être une liste")
            return {}

        result: Dict[str, List[Dict]] = {}
        for rule in playlists:
            if not isinstance(rule, dict):
                continue
            name = str(rule.get('name', '')).strip()
            if not name:
                continue

            filtered = self._filter_tracks_with_rule(tracks, rule)
            if not filtered:
                continue

            prefix_auto = bool(rule.get('prefix_auto', True))
            full_name = f"{AUTO_PLAYLIST_PREFIX if prefix_auto else ''}{name} ({len(filtered)} titres)"
            result[full_name] = filtered

        if result:
            self.logger.info(f"🧩 {len(result)} playlists personnalisées chargées depuis {path}")
        return result

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convertit un nom de playlist en nom de fichier sûr."""
        # Supprimer les emojis et caractères spéciaux via unicodedata
        cleaned = unicodedata.normalize('NFKD', name)
        cleaned = re.sub(r'[^\w\s-]', '', cleaned, flags=re.UNICODE)
        cleaned = re.sub(r'[\s]+', '_', cleaned.strip())
        return cleaned or 'playlist'

    def _connect_db(self):
        """Crée une connexion DB avec collation icu_root et text_factory."""
        # La DB Plex est souvent montée en lecture seule dans Docker.
        db_uri = f"file:{urllib.parse.quote(str(self.plex_db_path), safe='/')}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        conn.create_collation('icu_root', lambda a, b: (a > b) - (a < b))
        conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        return conn

    def export_playlists_m3u(self, playlists: Dict[str, List[Dict]], export_dir: str):
        """Exporte chaque playlist au format M3U étendu dans le dossier export_dir."""
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"📤 Export M3U de {len(playlists)} playlists vers {export_path}")
        exported = 0
        for name, tracks in playlists.items():
            file_name = self._safe_filename(name)
            m3u_path = export_path / f"{file_name}.m3u"
            with open(m3u_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{name}\n\n")
                for track in tracks:
                    fp = track.get('file_path')
                    if not fp:
                        continue
                    duration = int(track.get('duration_ms', 0) / 1000) if track.get('duration_ms') else -1
                    artist = track.get('artist', 'Unknown')
                    title = track.get('title', 'Unknown')
                    f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                    # Chemin relatif si possible
                    try:
                        rel_path = str(Path(fp).relative_to(export_path.parent))
                    except Exception:
                        rel_path = fp
                    f.write(rel_path + "\n")
            exported += 1
        self.logger.info(f"✅ {exported} playlists exportées vers {export_path}")
    def __init__(self, plex_db_path: str, verbose: bool = False):
        self.plex_db_path = Path(plex_db_path)
        self.verbose = verbose
        self._last_tracks: List[Dict] = []
        self._last_playlists: Dict[str, List[Dict]] = {}
        self.setup_logging()
        self.poster_style = self._load_poster_style()
        
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
        """Récupère toutes les données des pistes avec métadonnées enrichies.
        Déduplique par id (une piste peut avoir plusieurs genres)."""
        try:
            with self._connect_db() as conn:
                cursor = conn.cursor()
                
                # Récupère toutes les pistes avec tous leurs genres
                query = """
                SELECT
                    mi.id,
                    mi.title as track_title,
                    mi.year,
                    mi.originally_available_at,
                    mitem.duration,
                    mis.rating as user_rating,
                    mis.view_count as play_count,
                    mis.last_viewed_at,
                    mis.created_at as added_at,
                    albums.title as album_title,
                    artists.title as artist_name,
                    GROUP_CONCAT(DISTINCT genres.tag) as genres,
                    mp.file as file_path
                FROM metadata_items mi
                LEFT JOIN metadata_item_settings mis ON mi.guid = mis.guid
                LEFT JOIN metadata_items albums ON mi.parent_id = albums.id
                LEFT JOIN metadata_items artists ON albums.parent_id = artists.id
                LEFT JOIN taggings ON mi.id = taggings.metadata_item_id
                LEFT JOIN tags genres ON taggings.tag_id = genres.id AND genres.tag_type = 1
                JOIN media_items mitem ON mi.id = mitem.metadata_item_id
                JOIN media_parts mp ON mitem.id = mp.media_item_id
                WHERE mi.metadata_type = 10
                AND mp.file IS NOT NULL
                GROUP BY mi.id
                ORDER BY mi.title
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                tracks = []
                for row in rows:
                    all_genres = (row[11] or 'Unknown').split(',')
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
                        'genre': all_genres[0].strip(),  # Genre principal
                        'genres': [g.strip() for g in all_genres],  # Tous les genres
                        'file_path': row[12]
                    }
                    tracks.append(track)
                
                self.logger.info(f"📊 {len(tracks)} pistes chargées (dédupliquées)")
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
                playlist_name = f"{AUTO_PLAYLIST_PREFIX}⭐ {rating} étoiles ({len(rated_tracks)} titres)"
                rating_playlists[playlist_name] = rated_tracks
                
        return rating_playlists

    def create_year_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists par décennie/année"""
        year_playlists = {}
        
        # Par décennie
        decades = {}
        for track in tracks:
            if track['year'] and track['year'] > 0:
                decade = (track['year'] // 10) * 10
                if decade not in decades:
                    decades[decade] = []
                decades[decade].append(track)
        
        for decade, decade_tracks in decades.items():
            if len(decade_tracks) >= 10:  # Au moins 10 titres
                playlist_name = f"{AUTO_PLAYLIST_PREFIX}🕰️ Années {decade}s ({len(decade_tracks)} titres)"
                year_playlists[playlist_name] = decade_tracks
        
        # Années récentes (5 dernières années)
        current_year = datetime.datetime.now().year
        recent_tracks = [t for t in tracks if t['year'] and t['year'] >= current_year - 5]
        if recent_tracks:
            year_playlists[f"{AUTO_PLAYLIST_PREFIX}🆕 Récents ({len(recent_tracks)} titres)"] = recent_tracks
        
        return year_playlists

    def create_genre_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists par genre (utilise tous les genres de chaque piste)"""
        genre_playlists = {}
        
        # Grouper par genre (une piste peut apparaître dans plusieurs genres)
        genres = {}
        for track in tracks:
            for genre in track.get('genres', [track['genre']]):
                genre = genre.strip()
                if genre and genre != 'Unknown':
                    if genre not in genres:
                        genres[genre] = []
                    genres[genre].append(track)
        
        # Créer playlists pour les genres avec assez de contenu
        for genre, genre_tracks in sorted(genres.items()):
            if len(genre_tracks) >= 15:
                playlist_name = f"{AUTO_PLAYLIST_PREFIX}🎵 {genre} ({len(genre_tracks)} titres)"
                genre_playlists[playlist_name] = genre_tracks
        
        return genre_playlists

    def create_smart_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists intelligentes basées sur l'écoute"""
        smart_playlists = {}
        
        # Les plus écoutés
        most_played = sorted([t for t in tracks if t['play_count'] > 0], 
                            key=lambda x: x['play_count'], reverse=True)[:100]
        if most_played:
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}🔥 Top 100 plus écoutés"] = most_played
        
        # Favoris (5★ + beaucoup écoutés)
        favorites = [t for t in tracks if t['rating'] >= 8 and t['play_count'] >= 3]
        if favorites:
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}❤️ Mes favoris ({len(favorites)} titres)"] = favorites
        
        # Découverte (peu/pas écoutés, bien notés)
        discovery = [t for t in tracks if t['play_count'] <= 1 and t['rating'] >= 6]
        if discovery:
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}🔍 À redécouvrir ({len(discovery)} titres)"] = discovery
        
        # Récemment ajoutés (30 derniers jours)
        now = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        recently_added = [t for t in tracks if t['date_added'] and 
                         (now - t['date_added']) <= thirty_days]
        if recently_added:
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}🆕 Ajoutés récemment ({len(recently_added)} titres)"] = recently_added
        
        # Mix de l'humeur - titres longs pour se concentrer
        long_tracks = [t for t in tracks if t['duration_ms'] >= 300000 and t['rating'] >= 6]  # >5min
        if long_tracks:
            random.shuffle(long_tracks)
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}🧘 Mix concentration ({len(long_tracks[:50])} titres)"] = long_tracks[:50]
        
        # Mix énergique - titres courts et bien notés
        energy_tracks = [t for t in tracks if t['duration_ms'] <= 240000 and t['rating'] >= 8]  # <4min
        if energy_tracks:
            random.shuffle(energy_tracks)
            smart_playlists[f"{AUTO_PLAYLIST_PREFIX}⚡ Mix énergique ({len(energy_tracks[:50])} titres)"] = energy_tracks[:50]
        
        return smart_playlists

    def create_discovery_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée une playlist 'Découvertes' pour les pistes 2★ peu écoutées"""
        discovery_playlists = {}
        # Plex uses 1-10 scale in DB; 2★ ~ 4
        discoveries = [t for t in tracks if t['rating'] == 4 and t['play_count'] <= 1]
        if discoveries:
            discovery_playlists[f"{AUTO_PLAYLIST_PREFIX}🔎 Découvertes (2★) ({len(discoveries)} titres)"] = discoveries
        return discovery_playlists

    def create_top_this_month(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Créer une playlist 'Top This Month' pour nouveaux 4-5★"""
        top_playlists = {}
        now = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        recent_high_rated = [t for t in tracks if t['date_added'] and (now - t['date_added']) <= thirty_days and t['rating'] >= 8]
        if recent_high_rated:
            top_playlists[f"{AUTO_PLAYLIST_PREFIX}🏆 Top du mois ({len(recent_high_rated)} titres)"] = recent_high_rated
        return top_playlists

    def create_to_review_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Créer une playlist 'À réévaluer' pour pistes 3★ avec beaucoup d'écoutes"""
        to_review = [t for t in tracks if t['rating'] == 6 and t['play_count'] >= 20]
        playlists = {}
        if to_review:
            playlists[f"{AUTO_PLAYLIST_PREFIX}🔁 À réévaluer (3★, >20 plays) ({len(to_review)} titres)"] = to_review
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
            cleanup_playlists[f"{AUTO_PLAYLIST_PREFIX}🧹 Nettoyage (0 plays, 6+ mois) ({len(candidates)} titres)"] = candidates
        return cleanup_playlists

    def create_radio_playlists(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée des playlists imitant le style des radios françaises (RFM, NRJ, Fun Radio).
        Note: la plupart des pistes n'ont pas d'année renseignée → pas de filtre year."""
        radio_playlists = {}

        def _genres_match(track, genre_keywords):
            return any(k in g.lower() for g in track.get('genres', [track['genre']]) for k in genre_keywords)

        def _text_match(track, keywords):
            text = (track['title'] + ' ' + track['album'] + ' ' + track['artist']).lower()
            return any(k in text for k in keywords)

        # --- RFM : pop-rock adulte, variétés, soft, ballades, soul ---
        # Pas de filtre année (la majorité des pistes n'en ont pas)
        rfm_tracks = [
            t for t in tracks
            if _genres_match(t, ['pop/rock', 'vocal', 'easy listening', 'folk', 'blues', 'country'])
            and not _genres_match(t, ['rap', 'electronic'])
            and t.get('duration_ms', 0) >= 150000  # > 2m30 (pas de jingles)
        ]
        if rfm_tracks:
            # Mix aléatoire pondéré par les plus écoutés
            rfm_tracks.sort(key=lambda x: x['play_count'] + (x['rating'] or 0), reverse=True)
            rfm_selection = rfm_tracks[:300]
            radio_playlists[f'{AUTO_PLAYLIST_PREFIX}📻 Top Radio RFM ({len(rfm_selection)} titres)'] = rfm_selection

        # --- NRJ : hits pop mainstream, dance, R&B, rap ---
        nrj_tracks = [
            t for t in tracks
            if _genres_match(t, ['pop/rock', 'r&b', 'rap', 'electronic', 'latin'])
            and t.get('duration_ms', 0) >= 120000  # > 2 min
        ]
        if nrj_tracks:
            # Favoriser les plus écoutés (= les hits)
            nrj_tracks.sort(key=lambda x: x['play_count'], reverse=True)
            nrj_selection = nrj_tracks[:300]
            radio_playlists[f'{AUTO_PLAYLIST_PREFIX}📻 Top NRJ ({len(nrj_selection)} titres)'] = nrj_selection

        # --- Fun Radio : dance, electro, EDM, club, house, techno ---
        fun_tracks = [
            t for t in tracks
            if _genres_match(t, ['electronic'])
            or _text_match(t, ['remix', 'mix', 'dj ', 'club', 'dance', 'house', 'techno', 'trance', 'edm', 'rave'])
        ]
        if fun_tracks:
            random.shuffle(fun_tracks)
            fun_selection = fun_tracks[:300]
            radio_playlists[f'{AUTO_PLAYLIST_PREFIX}📻 Top Fun Radio ({len(fun_selection)} titres)'] = fun_selection

        return radio_playlists

    def create_stars80_playlist(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée une playlist Stars 80 : tubes francophones et américains/internationaux des années 80.
        Cherche par artistes connus, mots-clés albums, et genres pop/rock."""
        playlists = {}

        # Artistes francophones emblématiques des années 80
        artistes_fr_80 = [
            'indochine', 'téléphone', 'jean-jacques goldman', 'goldman', 'francis cabrel',
            'michel sardou', 'daniel balavoine', 'mylène farmer', 'alain souchon',
            'véronique sanson', 'laurent voulzy', 'michel berger', 'france gall',
            'desireless', 'niagara', 'étienne daho', 'etienne daho', 'marc lavoine',
            'jean-pierre mader', 'cookie dingler', 'jeanne mas', 'gold', 'images',
            'début de soirée', 'caroline loeb', 'rose laurens', 'peter et sloane',
            'peter & sloane', 'karen cheryl', 'bandolero', 'bibi flash', 'lio',
            'plastic bertrand', 'partenaire particulier', 'julien clerc', 'patrick hernandez',
            'gilbert montagné', 'catherine lara', 'jean-luc lahaye', 'stéphanie',
            'elsa', 'les rita mitsouko', 'rita mitsouko', 'émile et images',
            'patrick bruel', 'renaud', 'alain bashung', 'serge gainsbourg',
            'jacques dutronc', 'patrick coutin', 'pauline ester', 'sabine paturel',
            'jean schultheis', 'kim wilde', 'laroche valmont', 'philippe lavil',
            'yves simon', 'bernard lavilliers', 'herbert léonard', 'louis bertignac',
            'corynne charby', 'début de soirée', 'les avions', 'imagination',
            'ottawan', 'dalida', 'claude françois', 'mike brant',
        ]

        # Artistes américains/internationaux emblématiques des années 80
        artistes_us_80 = [
            'michael jackson', 'prince', 'madonna', 'cyndi lauper', 'tina turner',
            'whitney houston', 'bruce springsteen', 'bonnie tyler', 'phil collins',
            'duran duran', 'depeche mode', 'a-ha', 'eurythmics', 'culture club',
            'tears for fears', 'the cure', 'simple minds', 'wham', 'george michael',
            'queen', 'u2', 'pat benatar', 'blondie', 'toto', 'foreigner',
            'journey', 'bon jovi', 'def leppard', 'van halen', 'billy idol',
            'rick astley', 'kenny loggins', 'survivor', 'irene cara', 'berlin',
            'pet shop boys', 'new order', 'talk talk', 'the human league',
            'soft cell', 'abc', 'spandau ballet', 'alphaville', 'falco',
            'sabrina', 'sandra', 'samantha fox', 'gloria estefan', 'belinda carlisle',
            'bananarama', 'michael sembello', 'ray parker jr', 'glenn frey',
            'hall & oates', 'dire straits', 'sting', 'the police', 'inxs',
            'dead or alive', 'laura branigan', 'men at work', 'limahl',
            'baltimora', 'nena', 'scorpions', 'europe', 'white snake',
            'robert palmer', 'billy joel', 'lionel richie', 'stevie wonder',
            'donna summer', 'kool & the gang', 'earth wind', 'chaka khan',
        ]

        all_artists = artistes_fr_80 + artistes_us_80

        # Mots-clés albums typiques
        album_keywords_80 = [
            'stars 80', 'années 80', 'annees 80', 'hits 80', '80s',
            'top 50', 'soirées années 80', 'best of 80', 'decade 80',
            'délire 80', 'la bande à basile', 'le meilleur des années 80',
        ]

        selected = set()
        result = []

        for t in tracks:
            if t['id'] in selected:
                continue
            artist_lower = t['artist'].lower()
            album_lower = t['album'].lower()
            title_lower = t['title'].lower()

            # Match artiste
            artist_match = any(a in artist_lower for a in all_artists)

            # Match album
            album_match = any(kw in album_lower for kw in album_keywords_80)

            if artist_match or album_match:
                # Filtrer les pistes trop courtes (jingles, intros)
                if t.get('duration_ms', 0) >= 120000:
                    selected.add(t['id'])
                    result.append(t)

        # Trier par popularité (play_count + rating)
        result.sort(key=lambda x: x['play_count'] + (x['rating'] or 0), reverse=True)

        if result:
            playlists[f'{AUTO_PLAYLIST_PREFIX}⭐ Stars 80 FR & US ({len(result)} titres)'] = result

        return playlists

    def create_top50_playlist(self, tracks: List[Dict]) -> Dict[str, List[Dict]]:
        """Crée une playlist Génération Top 50 : les tubes du Top 50 français (1984-1993+).
        Mix de variété française, pop internationale, dance/eurodance des compils Top 50."""
        playlists = {}

        # Artistes emblématiques du Top 50 français
        artistes_top50 = [
            # Variété française Top 50
            'jean-jacques goldman', 'goldman', 'daniel balavoine', 'france gall',
            'mylène farmer', 'indochine', 'laurent voulzy', 'michel berger',
            'alain souchon', 'patrick bruel', 'marc lavoine', 'julien clerc',
            'francis cabrel', 'michel sardou', 'renaud', 'alain bashung',
            'étienne daho', 'etienne daho', 'jean-pierre mader', 'niagara',
            'les rita mitsouko', 'rita mitsouko', 'jeanne mas', 'lio',
            'desireless', 'images', 'gold', 'cookie dingler', 'pauline ester',
            'elsa', 'stéphanie', 'vanessa paradis', 'patricia kaas',
            'florent pagny', 'pascal obispo', 'liane foly', 'khaled',
            'jordy', 'les inconnus', 'lagaf', 'hélène', 'hélène ségara',
            # Pop internationale Top 50
            'michael jackson', 'madonna', 'prince', 'george michael',
            'phil collins', 'whitney houston', 'a-ha', 'duran duran',
            'rick astley', 'sabrina', 'samantha fox', 'kylie minogue',
            'jason donovan', 'bros', 'milli vanilli', 'mc hammer',
            'vanilla ice', 'snap', 'technotronic', 'black box',
            'roxette', 'ace of base', 'la bouche', 'dr alban',
            'haddaway', 'corona', 'double you', '2 unlimited',
            # Dance / Eurodance
            'début de soirée', 'caroline loeb', 'laroche valmont', 'cock robin',
            'patrick hernandez', 'plastic bertrand', 'ottawan', 'peter et sloane',
            'peter & sloane', 'jean schultheis', 'bandolero', 'bibi flash',
            'corynne charby', 'philippe lavil', 'gilbert montagné',
            'karen cheryl', 'rose laurens', 'herbert léonard', 'partenaire particulier',
        ]

        # Mots-clés albums Top 50
        album_keywords_top50 = [
            'top 50', 'génération top', 'generation top', 'top 50 30 ans',
            'stars 80', 'années 80', 'annees 80', 'hits 80', 'tubes 80',
            'nuit de folie', 'soirées années 80', 'best of 80',
            'fan des années 80', 'fans des années 80',
            'anthologie', 'chanson française',
        ]

        selected = set()
        result = []

        for t in tracks:
            if t['id'] in selected:
                continue
            artist_lower = t['artist'].lower()
            album_lower = t['album'].lower()

            artist_match = any(a in artist_lower for a in artistes_top50)
            album_match = any(kw in album_lower for kw in album_keywords_top50)

            if artist_match or album_match:
                if t.get('duration_ms', 0) >= 120000:
                    selected.add(t['id'])
                    result.append(t)

        result.sort(key=lambda x: x['play_count'] + (x['rating'] or 0), reverse=True)

        if result:
            playlists[f'{AUTO_PLAYLIST_PREFIX}🎤 Génération Top 50 ({len(result)} titres)'] = result

        return playlists

    def export_playlists_to_usb(self, playlist_names: List[str], usb_path: str = '/media/paulceline/MUSIC'):
        """Copie les fichiers audio des playlists données vers la clé USB.
        Crée un dossier par playlist et un fichier .m3u à la racine."""
        import shutil

        if not os.path.isdir(usb_path):
            self.logger.error(f"❌ Clé USB non trouvée: {usb_path}")
            return

        # Récupérer les playlists depuis Plex API
        try:
            url = f"{PLEX_URL}/playlists?X-Plex-Token={PLEX_TOKEN}"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req)
            root = ET.fromstring(resp.read())
        except Exception as e:
            self.logger.error(f"❌ Impossible de lister les playlists: {e}")
            return

        for pname in playlist_names:
            # Trouver la playlist par titre (match partiel)
            playlist_el = None
            for p in root.findall('.//Playlist'):
                if pname.lower() in p.get('title', '').lower():
                    playlist_el = p
                    break

            if not playlist_el:
                self.logger.warning(f"⚠️ Playlist '{pname}' non trouvée dans Plex")
                continue

            pl_title = playlist_el.get('title')
            rk = playlist_el.get('ratingKey')
            self.logger.info(f"📀 Export USB: {pl_title}")

            # Récupérer les pistes
            url = f"{PLEX_URL}/playlists/{rk}/items?X-Plex-Token={PLEX_TOKEN}"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req)
            items_root = ET.fromstring(resp.read())

            # Dossier sur USB
            safe_name = self._safe_filename(pl_title)
            dest_dir = os.path.join(usb_path, safe_name)
            os.makedirs(dest_dir, exist_ok=True)

            m3u_lines = ['#EXTM3U', f'#PLAYLIST:{pl_title}', '']
            copied = 0
            skipped = 0

            for track in items_root.findall('.//Track'):
                title = track.get('title', 'Unknown')
                artist = track.get('grandparentTitle', 'Unknown')
                duration = int(track.get('duration', '0')) // 1000

                # Trouver le fichier source
                media = track.find('.//Part')
                if media is None:
                    skipped += 1
                    continue
                src_file = media.get('file', '')
                if not src_file or not os.path.isfile(src_file):
                    skipped += 1
                    continue

                # Nom du fichier destination
                ext = os.path.splitext(src_file)[1]
                # Numéroter pour garder l'ordre
                dest_name = f"{copied + 1:03d} - {artist} - {title}"
                # Nettoyer le nom
                dest_name = re.sub(r'[<>:"/\\|?*]', '', dest_name)[:200]
                dest_name += ext
                dest_file = os.path.join(dest_dir, dest_name)

                # Copier si pas déjà présent ou taille différente
                if not os.path.exists(dest_file) or os.path.getsize(dest_file) != os.path.getsize(src_file):
                    try:
                        shutil.copy2(src_file, dest_file)
                        copied += 1
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ {dest_name}: {e}")
                        skipped += 1
                        continue
                else:
                    copied += 1  # Already there

                m3u_lines.append(f"#EXTINF:{duration},{artist} - {title}")
                m3u_lines.append(f"{safe_name}/{dest_name}")
                m3u_lines.append('')

            # Écrire le fichier M3U à la racine USB
            m3u_path = os.path.join(usb_path, f"{safe_name}.m3u")
            with open(m3u_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(m3u_lines))

            self.logger.info(f"  ✅ {copied} fichiers copiés, {skipped} ignorés → {dest_dir}")

    def _plex_api(self, method: str, path: str) -> dict:
        """Appel API Plex. Retourne le JSON parsé ou {} si pas de body."""
        url = f"{PLEX_URL}{path}"
        if '?' in url:
            url += f"&X-Plex-Token={PLEX_TOKEN}"
        else:
            url += f"?X-Plex-Token={PLEX_TOKEN}"
        req = urllib.request.Request(url, method=method)
        req.add_header('Accept', 'application/json')
        resp = urllib.request.urlopen(req)
        body = resp.read()
        return json.loads(body) if body else {}

    def cleanup_old_auto_playlists(self):
        """Supprime les anciennes playlists auto-générées (préfixe [Auto]) via l'API Plex."""
        try:
            data = self._plex_api('GET', '/playlists')
            playlists = data.get('MediaContainer', {}).get('Metadata', [])
            count = 0
            for p in playlists:
                if p.get('title', '').startswith(AUTO_PLAYLIST_PREFIX):
                    rk = p['ratingKey']
                    try:
                        self._plex_api('DELETE', f'/playlists/{rk}')
                        count += 1
                        self.logger.debug(f"  Supprimé: {p['title']}")
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ Impossible de supprimer {p['title']}: {e}")
            if count:
                self.logger.info(f"🧹 {count} anciennes playlists auto supprimées")
        except Exception as e:
            self.logger.error(f"❌ Erreur nettoyage: {e}")



    def save_playlist_to_plex(self, playlist_name: str, tracks: List[Dict], append_existing: bool = False) -> bool:
        """Sauvegarde une playlist dans Plex via l'API HTTP."""
        if not tracks:
            self.logger.debug(f"⏭️ Playlist vide ignorée: {playlist_name}")
            return False
        try:
            data = self._plex_api('GET', '/playlists')
            existing_rk = None
            for p in data.get('MediaContainer', {}).get('Metadata', []):
                if p.get('title') == playlist_name:
                    existing_rk = p['ratingKey']
                    break

            # Mode ajout: conserve la playlist existante et ajoute uniquement les nouvelles pistes.
            if append_existing and existing_rk is not None:
                meta = self._plex_api('GET', f'/playlists/{existing_rk}/items')
                existing_items = meta.get('MediaContainer', {}).get('Metadata', [])
                existing_ids = {int(i.get('ratingKey')) for i in existing_items if i.get('ratingKey')}
                to_add = [t for t in tracks if int(t['id']) not in existing_ids]
                if not to_add:
                    self.logger.info(f"✅ Playlist inchangée: {playlist_name} (aucune nouvelle piste)")
                    return True

                BATCH = 200
                for i in range(0, len(to_add), BATCH):
                    batch = to_add[i:i+BATCH]
                    ids_str = ','.join(str(t['id']) for t in batch)
                    uri = f'server://{PLEX_MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{ids_str}'
                    params = urllib.parse.urlencode({'uri': uri})
                    self._plex_api('PUT', f'/playlists/{existing_rk}/items?{params}')

                self.logger.info(f"✅ Playlist mise à jour: {playlist_name} (+{len(to_add)} pistes)")
                return True

            # Mode remplacement: supprimer puis recréer si la playlist existe déjà
            if existing_rk is not None:
                self._plex_api('DELETE', f'/playlists/{existing_rk}')

            # Créer la playlist avec le 1er item
            first_uri = f'server://{PLEX_MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{tracks[0]["id"]}'
            params = urllib.parse.urlencode({
                'type': 'audio', 'title': playlist_name,
                'smart': 0, 'uri': first_uri
            })
            resp = self._plex_api('POST', f'/playlists?{params}')
            rk = resp['MediaContainer']['Metadata'][0]['ratingKey']

            # Ajouter les items restants par lots de 200
            BATCH = 200
            remaining = tracks[1:]
            for i in range(0, len(remaining), BATCH):
                batch = remaining[i:i+BATCH]
                ids_str = ','.join(str(t['id']) for t in batch)
                uri = f'server://{PLEX_MACHINE_ID}/com.plexapp.plugins.library/library/metadata/{ids_str}'
                params = urllib.parse.urlencode({'uri': uri})
                self._plex_api('PUT', f'/playlists/{rk}/items?{params}')

            self.logger.info(f"✅ Playlist créée: {playlist_name} ({len(tracks)} pistes)")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur playlist {playlist_name}: {e}")
            return False

    # --- Définitions visuelles pour les posters de playlists ---
    # Chaque entrée: (mots-clés à chercher dans le titre, emoji, couleurs gradient, sous-titre optionnel)
    POSTER_THEMES = [
        # Auto playlists
        (['⭐', 'étoile'], '⭐', [(255, 180, 0), (200, 100, 0)], None),
        (['🔥', 'top 100', 'plus écoutés'], '🔥', [(200, 50, 0), (255, 150, 0)], None),
        (['❤️', 'favoris'], '❤️', [(180, 0, 50), (255, 50, 100)], None),
        (['🔍', 'redécouvrir'], '🔍', [(0, 100, 150), (0, 200, 200)], None),
        (['🔎', 'découvertes'], '🔎', [(50, 100, 180), (0, 200, 150)], None),
        (['⚡', 'énergique'], '⚡', [(200, 150, 0), (255, 50, 0)], None),
        (['🧘', 'concentration'], '🧘', [(0, 80, 120), (0, 180, 180)], None),
        (['🎵', 'blues'], '🎵', [(0, 0, 120), (50, 50, 200)], None),
        (['🎵', 'electronic'], '🎛️', [(0, 0, 150), (150, 0, 255)], None),
        (['🎵', 'pop/rock'], '🎸', [(200, 0, 50), (255, 100, 0)], None),
        (['🎵', 'r&b'], '🎤', [(100, 0, 150), (200, 50, 200)], None),
        (['🎵', 'rap'], '🎤', [(40, 40, 40), (100, 0, 0)], None),
        (['🎵', 'jazz'], '🎷', [(50, 30, 0), (150, 100, 0)], None),
        (['🎵', 'latin'], '💃', [(200, 50, 0), (255, 200, 0)], None),
        (['🎵', 'country'], '🤠', [(100, 80, 0), (200, 150, 50)], None),
        (['🎵', 'reggae'], '🟢', [(0, 120, 0), (200, 200, 0)], None),
        (['🎵', 'folk'], '🪕', [(80, 60, 20), (180, 140, 60)], None),
        (['🎵', 'holiday'], '🎄', [(150, 0, 0), (0, 100, 0)], None),
        (['📻', 'rfm'], '📻', [(200, 0, 50), (255, 100, 0)], None),
        (['📻', 'nrj'], '📻', [(0, 80, 200), (0, 200, 100)], None),
        (['📻', 'fun radio'], '📻', [(150, 0, 200), (0, 100, 255)], None),
        (['funk', 'disco'], '🕺', [(220, 20, 180), (255, 140, 0)], None),
        (['running', 'workout'], '🏃', [(0, 150, 50), (0, 200, 150)], None),
        (['🕰️', 'années'], '📅', [(80, 0, 150), (0, 100, 200)], None),
        (['🆕', 'récent', 'ajouté'], '🆕', [(0, 150, 100), (0, 200, 200)], None),
        (['🏆', 'top du mois'], '🏆', [(180, 130, 0), (255, 200, 0)], None),
        (['🔁', 'réévaluer'], '🔁', [(100, 100, 0), (200, 150, 0)], None),
        (['🧹', 'nettoyage'], '🧹', [(80, 80, 80), (150, 150, 150)], None),
        # Manual playlists (partial match on title)
        (['disco', '2007'], '🕺', [(220, 20, 180), (255, 140, 0)], None),
        (["90s", "'90s", "90"], '💿', [(0, 100, 200), (0, 200, 150)], None),
        (['dance', '2008'], '💃', [(200, 0, 100), (255, 100, 0)], None),
        (['2000s'], '🎧', [(80, 0, 180), (0, 150, 255)], None),
        (['soundiiz', 'ai '], '🤖', [(0, 80, 160), (0, 200, 200)], None),
        (['move your body', 'absolute'], '🏋️', [(200, 50, 0), (255, 200, 0)], None),
        (['apéro', 'aperitif'], '🍹', [(255, 100, 0), (255, 200, 50)], None),
        (['car music'], '🚗', [(40, 40, 40), (180, 0, 0)], None),
        (['chill', 'relax', 'massage'], '🧘', [(0, 100, 150), (100, 200, 180)], None),
        (['club', 'electro'], '🎛️', [(0, 0, 150), (150, 0, 255)], None),
        (['favorite', 'liked', 'loved'], '💜', [(100, 0, 200), (200, 50, 255)], None),
        (['fiesta', 'party'], '🎉', [(255, 50, 0), (255, 200, 0)], None),
        (['discothèque', 'la plus grande'], '🌍', [(0, 50, 150), (200, 0, 100)], None),
        (['moins écoutés'], '🔇', [(60, 60, 80), (120, 120, 140)], None),
        (['plus écoutés'], '🔊', [(200, 150, 0), (255, 50, 0)], None),
        (['classement', 'meilleur'], '🏆', [(180, 130, 0), (255, 200, 0)], None),
        (['rfm party', '80-90'], '📻', [(200, 0, 50), (255, 100, 0)], None),
        (['running', 'hits 2025'], '🏃', [(0, 150, 50), (0, 200, 150)], None),
        (['stars 80', 'soirées'], '⭐', [(50, 0, 150), (200, 0, 200)], None),
        (['rhythm', 'the rhythm'], '🎶', [(0, 80, 200), (0, 180, 255)], None),
        (['itunes', 'hot tracks'], '🔥', [(200, 50, 0), (255, 150, 0)], None),
        (['stars 80'], '⭐', [(180, 0, 220), (255, 100, 0)], None),
        (['génération top 50', 'generation top 50'], '🎤', [(0, 50, 150), (200, 50, 200)], None),
    ]

    def _find_poster_theme(self, title: str) -> Tuple[str, list, list]:
        """Trouve le thème visuel pour un titre de playlist. Retourne (emoji, [c1], [c2])."""
        title_lower = title.lower()

        # Priorité aux thèmes custom définis dans le JSON de style.
        for theme in self.poster_style.get("themes", []):
            keywords = theme.get("keywords", [])
            if not keywords:
                continue
            match_mode = theme.get("match", "all")
            is_match = any(k in title_lower for k in keywords) if match_mode == "any" else all(k in title_lower for k in keywords)
            if is_match:
                colors = theme.get("colors", [(80, 80, 160), (150, 150, 230)])
                return theme.get("emoji", "🎵"), colors[0], colors[1]

        for keywords, emoji, colors, _ in self.POSTER_THEMES:
            if all(k.lower() in title_lower for k in keywords):
                return emoji, colors[0], colors[1]

        default_emoji = str(self.poster_style.get("default_emoji", "🎵"))
        default_colors = self.poster_style.get("default_colors", [(70, 70, 140), (120, 120, 220)])
        if isinstance(default_colors, list) and len(default_colors) == 2:
            return default_emoji, default_colors[0], default_colors[1]

        # Fallback: couleur basée sur le hash du titre
        h = hash(title) % 360
        import colorsys
        r1, g1, b1 = [int(c * 255) for c in colorsys.hsv_to_rgb(h / 360, 0.7, 0.6)]
        r2, g2, b2 = [int(c * 255) for c in colorsys.hsv_to_rgb(((h + 60) % 360) / 360, 0.7, 0.8)]
        return '🎵', (r1, g1, b1), (r2, g2, b2)

    def generate_playlist_posters(self):
        """Génère et applique des images de poster pour toutes les playlists Plex."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.logger.warning("⚠️ Pillow non installé, pas de génération de posters (pip install Pillow)")
            return

        FONT_PATH = str(self.poster_style.get("font_path", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        EMOJI_FONT_PATH = str(self.poster_style.get("emoji_font_path", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"))
        SIZE = int(self.poster_style.get("size", 600))
        OVERLAY_ALPHA = int(self.poster_style.get("overlay_alpha", 100))
        TITLE_SIZE = int(self.poster_style.get("title_size", 44))
        SUBTITLE_SIZE = int(self.poster_style.get("subtitle_size", 24))
        EMOJI_SIZE = int(self.poster_style.get("emoji_size", 80))
        TITLE_START_Y = int(self.poster_style.get("title_start_y", 300))
        TITLE_LINE_STEP = int(self.poster_style.get("title_line_step", 50))
        TEXT_PADDING = int(self.poster_style.get("text_padding", 60))
        TITLE_COLOR = tuple(self.poster_style.get("title_color", (255, 255, 255, 255)))
        TITLE_SHADOW_COLOR = tuple(self.poster_style.get("title_shadow_color", (0, 0, 0, 180)))
        SUBTITLE_COLOR = tuple(self.poster_style.get("subtitle_color", (200, 200, 200, 220)))
        LINE_COLOR = tuple(self.poster_style.get("line_color", (255, 255, 255, 80)))

        # Récupérer toutes les playlists
        try:
            url = f"{PLEX_URL}/playlists?X-Plex-Token={PLEX_TOKEN}"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req)
            root = ET.fromstring(resp.read())
        except Exception as e:
            self.logger.error(f"❌ Impossible de lister les playlists: {e}")
            return

        playlists = root.findall('.//Playlist')
        self.logger.info(f"🎨 Génération des posters pour {len(playlists)} playlists...")

        ok = 0
        fail = 0
        for playlist in playlists:
            title = playlist.get('title', '')
            rk = playlist.get('ratingKey', '')
            if not rk:
                continue

            emoji, c1, c2 = self._find_poster_theme(title)

            # Créer l'image
            img = Image.new('RGB', (SIZE, SIZE))
            for y in range(SIZE):
                for x in range(SIZE):
                    t = (x + y) / (2 * SIZE)
                    r = int(c1[0] + (c2[0] - c1[0]) * t)
                    g = int(c1[1] + (c2[1] - c1[1]) * t)
                    b = int(c1[2] + (c2[2] - c1[2]) * t)
                    img.putpixel((x, y), (r, g, b))

            # Overlay sombre
            overlay = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, OVERLAY_ALPHA))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            # Emoji
            try:
                emoji_font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_SIZE)
                bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
                ew = bbox[2] - bbox[0]
                draw.text(((SIZE - ew) // 2, 140), emoji, font=emoji_font, embedded_color=True)
            except Exception:
                pass

            # Titre (retirer le préfixe [Auto] pour l'affichage)
            display_title = title
            if bool(self.poster_style.get("strip_auto_prefix", True)):
                display_title = display_title.replace(AUTO_PLAYLIST_PREFIX, '').strip()
            # Retirer le compteur "(XXX titres)" pour un affichage plus propre
            if bool(self.poster_style.get("strip_count_suffix", True)):
                display_title = re.sub(r'\s*\(\d+ titres?\)\s*$', '', display_title)

            font_title = ImageFont.truetype(FONT_PATH, TITLE_SIZE)
            font_sub = ImageFont.truetype(FONT_PATH, SUBTITLE_SIZE)

            # Word-wrap
            words = display_title.split()
            lines = []
            line = ""
            for w in words:
                test = f"{line} {w}".strip()
                bbox = draw.textbbox((0, 0), test, font=font_title)
                if bbox[2] - bbox[0] > SIZE - TEXT_PADDING:
                    if line:
                        lines.append(line)
                    line = w
                else:
                    line = test
            if line:
                lines.append(line)

            y_pos = TITLE_START_Y
            for ln in lines:
                bbox = draw.textbbox((0, 0), ln, font=font_title)
                tw = bbox[2] - bbox[0]
                draw.text(((SIZE - tw) // 2 + 2, y_pos + 2), ln, fill=TITLE_SHADOW_COLOR, font=font_title)
                draw.text(((SIZE - tw) // 2, y_pos), ln, fill=TITLE_COLOR, font=font_title)
                y_pos += TITLE_LINE_STEP

            # Ligne décorative
            draw.line([(TEXT_PADDING, y_pos + 10), (SIZE - TEXT_PADDING, y_pos + 10)], fill=LINE_COLOR, width=2)

            # Sous-titre (nombre de pistes)
            leaf_count = playlist.get('leafCount', '')
            if leaf_count:
                sub = f"{leaf_count} titres"
                bbox = draw.textbbox((0, 0), sub, font=font_sub)
                sw = bbox[2] - bbox[0]
                draw.text(((SIZE - sw) // 2, y_pos + 20), sub, fill=SUBTITLE_COLOR, font=font_sub)

            img = img.convert('RGB')

            # Encoder en PNG en mémoire
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            png_data = buf.getvalue()

            # Upload via API
            try:
                upload_url = f"{PLEX_URL}/library/metadata/{rk}/posters?X-Plex-Token={PLEX_TOKEN}"
                req = urllib.request.Request(upload_url, data=png_data, method='POST')
                req.add_header('Content-Type', 'image/png')
                urllib.request.urlopen(req)
                ok += 1
                self.logger.debug(f"  🖼️ {title}")
            except Exception as e:
                fail += 1
                self.logger.warning(f"  ⚠️ Poster échoué pour {title}: {e}")

        self.logger.info(f"🖼️ Posters: {ok} appliqués, {fail} échoués sur {len(playlists)}")

    def generate_all_playlists(self, save_to_plex: bool = True,
                               append_existing: bool = False,
                               custom_config: Optional[str] = None) -> Dict[str, int]:
        """Génère toutes les playlists automatiques"""
        self.logger.info("🎵 Génération des playlists automatiques PlexAmp")
        
        # Charger les données
        tracks = self.get_track_data()
        if not tracks:
            self.logger.error("❌ Aucune piste trouvée")
            return {}
        
        # Nettoyer les anciennes playlists auto avant de recréer (pas en mode ajout)
        if save_to_plex and not append_existing:
            self.cleanup_old_auto_playlists()

        # Générer toutes les playlists
        all_playlists = self._build_all_playlists(tracks, custom_config=custom_config)
        self._last_tracks = tracks
        self._last_playlists = all_playlists

        # Statistiques et export
        created_count = 0
        results = {}

        # Sauvegarder dans Plex si demandé
        if save_to_plex:
            for playlist_name, playlist_tracks in all_playlists.items():
                if self.save_playlist_to_plex(playlist_name, playlist_tracks, append_existing=append_existing):
                    created_count += 1
                    results[playlist_name] = len(playlist_tracks)
        else:
            # Mode simulation
            for playlist_name, playlist_tracks in all_playlists.items():
                self.logger.info(f"📋 {playlist_name}: {len(playlist_tracks)} titres")
                results[playlist_name] = len(playlist_tracks)
        self.logger.info(f"\n🎉 {created_count if save_to_plex else len(all_playlists)} playlists {'créées' if save_to_plex else 'simulées'}")

        # Générer les posters pour toutes les playlists
        if save_to_plex and not getattr(self, '_no_posters', False):
            self.generate_playlist_posters()

        return results

# Chemin par défaut de l'export M3U
DEFAULT_M3U_EXPORT_DIR = os.getenv('PLAYLISTS_DIR', '/mnt/ssd/Musiques/Playlists')

def main():
    parser = argparse.ArgumentParser(description="Générateur de playlists automatiques PlexAmp")
    default_plex_db = os.getenv(
        "PLEX_DB",
        "/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    )
    parser.add_argument("--plex-db", 
                       default=default_plex_db,
                       help="Chemin vers la base de données Plex")
    parser.add_argument("--dry-run", action="store_true",
                       help="Mode simulation (ne crée pas les playlists)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Mode verbeux")
    parser.add_argument("--export-dir",
                       default=DEFAULT_M3U_EXPORT_DIR,
                       help="Répertoire d'export des fichiers M3U")
    parser.add_argument("--no-export", action="store_true",
                       help="Ne pas exporter en M3U")
    parser.add_argument("--no-posters", action="store_true",
                       help="Ne pas générer les images de poster")
    parser.add_argument("--posters-only", action="store_true",
                       help="Regénérer uniquement les posters (sans toucher aux playlists)")
    parser.add_argument("--usb", nargs='?', const='/media/paulceline/MUSIC',
                       help="Exporter Stars 80 et Top 50 vers clé USB (défaut: /media/paulceline/MUSIC)")
    parser.add_argument("--usb-playlists", nargs='+', default=['Stars 80', 'Top 50'],
                       help="Noms des playlists à exporter sur USB (défaut: Stars 80, Top 50)")
    parser.add_argument("--append-existing", action="store_true",
                       help="Ajoute les nouvelles pistes aux playlists existantes au lieu de les recréer")
    parser.add_argument("--custom-config",
                       default=os.getenv("PLEX_CUSTOM_PLAYLISTS_CONFIG", ""),
                       help="Chemin vers un fichier JSON de playlists personnalisées")
    
    args = parser.parse_args()
    
    generator = PlexAmpAutoPlaylist(args.plex_db, verbose=args.verbose)
    generator._no_posters = args.no_posters

    # Mode posters uniquement
    if args.posters_only:
        generator.generate_playlist_posters()
        return

    # generate_all_playlists gère le dry-run et le nettoyage des anciennes
    results = generator.generate_all_playlists(
        save_to_plex=not args.dry_run,
        append_existing=args.append_existing,
        custom_config=args.custom_config or None,
    )

    # Export M3U (réutilise les données déjà en mémoire)
    if not args.dry_run and not args.no_export and results:
        all_playlists = generator._last_playlists or generator._build_all_playlists(
            generator._last_tracks or generator.get_track_data(),
            custom_config=args.custom_config or None,
        )
        generator.export_playlists_m3u(all_playlists, args.export_dir)

    # Export USB si demandé
    if args.usb:
        generator.export_playlists_to_usb(args.usb_playlists, args.usb)

    # Résumé
    print(f"\n📊 RÉSUMÉ: {len(results)} playlists")
    print("=" * 50)
    for playlist_name, count in results.items():
        print(f"  {playlist_name}: {count} titres")
    total = sum(results.values())
    print(f"\n  Total: {total} pistes (avec doublons inter-playlists)")

if __name__ == "__main__":
    main()