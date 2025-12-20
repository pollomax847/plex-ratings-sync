#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple pour nettoyer ET organiser les fichiers audio
Version rapide avec Mutagen + recherche en ligne (Last.fm + AcoustID)
"""

import os
import sys
import logging
import json
import re
import unicodedata
import shutil
import time
import requests
import hashlib
from datetime import datetime
from mutagen._file import File

# Dépendances optionnelles pour la recherche en ligne
try:
    import acoustid
    ACOUSTID_AVAILABLE = True
except ImportError:
    ACOUSTID_AVAILABLE = False
    
try:
    import pylast
    LASTFM_AVAILABLE = True
except ImportError:
    LASTFM_AVAILABLE = False

class SimpleMusicCleaner:
    # Codes couleurs ANSI
    COLOR_RESET = "\033[0m"
    COLOR_RED = "\033[31m"
    COLOR_GREEN = "\033[32m"
    COLOR_YELLOW = "\033[33m"
    COLOR_BLUE = "\033[34m"
    
    def __init__(self, music_dir, organize_mode=False, dest_dir=None, online_mode=False):
        self.music_dir = music_dir
        self.organize_mode = organize_mode
        self.online_mode = online_mode
        self.dest_dir = dest_dir or os.path.join(os.path.dirname(music_dir), "Organisé")
        self.audio_extensions = ('.mp3', '.flac', '.m4a', '.ogg', '.wma', '.wav', '.aac')
        self.deleted_files = []
        self.organized_files = []
        self.enriched_files = []
        self.processed_files = 0
        self.errors = []
        self.renamed_files = []
        
        # Seuils de détection (configurables)
        self.min_file_size_mb = 0.5  # Fichiers < 0.5MB suspects
        self.min_duration_seconds = 15  # Fichiers < 15 secondes suspects
        self.min_bitrate_kbps = 32  # Bitrate < 32kbps suspect
        
        # Configuration APIs
        self.acoustid_api_key = "8XaBELgH"  # Clé publique AcoustID
        self.lastfm_api_key = "d25f80cfb53e2f8b9d46a3309ffb5fd5"  # Clé publique Last.fm
        self.lastfm_api_secret = "c51bb3e8e59c2bb445c4bb69bc9a5fb5"
        
        # Configuration du logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure le système de logging"""
        log_filename = f"music_cleaner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Démarrage du nettoyage pour: {self.music_dir}")
        
    def normalize_filename(self, file_path):
        """Normalise le nom d'un fichier en remplaçant les caractères problématiques"""
        try:
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            # Normaliser les caractères Unicode
            normalized_name = unicodedata.normalize('NFKD', name)
            
            # Remplacer les caractères non-ASCII par des équivalents
            normalized_name = normalized_name.encode('ascii', 'ignore').decode('ascii')
            
            # Remplacer les caractères spéciaux problématiques
            replacements = {
                '&': 'and',
                '@': 'at',
                '#': 'hash',
                '%': 'percent',
                '+': 'plus',
                '=': 'equal',
                '?': '',
                '<': '',
                '>': '',
                '|': '',
                '*': '',
                '"': '',
                ':': '-',
                ';': '-',
                '/': '-',
                '\\': '-',
                '[': '(',
                ']': ')',
                '{': '(',
                '}': ')',
                '  ': ' '  # Double espaces
            }
            
            for old, new in replacements.items():
                normalized_name = normalized_name.replace(old, new)
            
            # Nettoyer les espaces multiples et les tirets multiples
            normalized_name = re.sub(r'\s+', ' ', normalized_name)
            normalized_name = re.sub(r'-+', '-', normalized_name)
            normalized_name = normalized_name.strip(' -')
            
            # Éviter les noms vides
            if not normalized_name:
                normalized_name = "unnamed_file"
            
            new_filename = normalized_name + ext
            new_file_path = os.path.join(directory, new_filename)
            
            # Renommer si nécessaire et si différent
            if file_path != new_file_path and not os.path.exists(new_file_path):
                try:
                    os.rename(file_path, new_file_path)
                    rename_info = {
                        'original': filename,
                        'new': new_filename,
                        'path': new_file_path
                    }
                    self.renamed_files.append(rename_info)
                    self.logger.info(f"Fichier renommé: {filename} -> {new_filename}")
                    print(f"{self.COLOR_YELLOW}📝 Renommé: {filename} -> {new_filename}{self.COLOR_RESET}")
                    return new_file_path
                except OSError as e:
                    self.logger.warning(f"Impossible de renommer {file_path}: {e}")
                    return file_path
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la normalisation de {file_path}: {e}")
            return file_path
        
    def get_file_info(self, file_path):
        """Analyse un fichier audio avec gestion d'erreurs robuste et normalisation des noms"""
        original_path = file_path
        
        try:
            # Vérifier que le fichier existe et est accessible
            if not os.path.exists(file_path):
                self.logger.warning(f"Fichier inexistant: {file_path}")
                return None
                
            if not os.access(file_path, os.R_OK):
                self.logger.warning(f"Fichier non lisible: {file_path}")
                return None
            
            # Taille du fichier
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Première tentative de lecture des métadonnées audio
            audio = None
            try:
                audio = File(file_path)
            except Exception as e:
                self.logger.warning(f"Première tentative échouée pour {file_path}: {e}")
                print(f"{self.COLOR_YELLOW}⚠️  Problème de lecture, tentative de normalisation du nom...{self.COLOR_RESET}")
                
                # Essayer de normaliser le nom de fichier
                normalized_path = self.normalize_filename(file_path)
                if normalized_path != file_path:
                    file_path = normalized_path
                    try:
                        audio = File(file_path)
                        print(f"{self.COLOR_GREEN}✅ Lecture réussie après normalisation!{self.COLOR_RESET}")
                    except Exception as e2:
                        self.logger.error(f"Échec même après normalisation pour {file_path}: {e2}")
                        audio = None
            
            if audio is None:
                self.logger.warning(f"Fichier audio non reconnu: {file_path}")
                return None
            
            # Extraction sécurisée des métadonnées
            duration = 0
            bitrate = 0
            
            if hasattr(audio, 'info') and audio.info:
                duration = getattr(audio.info, 'length', 0) or 0
                bitrate = getattr(audio.info, 'bitrate', 0) or 0
            
            return {
                'file_path': file_path,
                'original_path': original_path,
                'file_size': file_size,
                'file_size_mb': file_size_mb,
                'duration': duration,
                'bitrate': bitrate,
                'filename': os.path.basename(file_path),
                'was_renamed': file_path != original_path
            }
            
        except PermissionError as e:
            error_msg = f"Permission refusée pour {original_path}: {e}"
            print(f"❌ {error_msg}")
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return None
        except OSError as e:
            error_msg = f"Erreur système pour {original_path}: {e}"
            print(f"❌ {error_msg}")
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return None
        except Exception as e:
            error_msg = f"Erreur inattendue pour {original_path}: {e}"
            print(f"❌ {error_msg}")
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return None
    
    def is_file_suspect(self, file_info):
        """Détermine si un fichier est suspect/incomplet avec critères améliorés"""
        reasons = []
        
        # Vérification 1: Taille très petite
        if file_info['file_size_mb'] < self.min_file_size_mb:
            reasons.append(f"Fichier très petit: {file_info['file_size_mb']:.2f} MB")
        
        # Vérification 2: Durée très courte (sauf pour les samples légitimes)
        if file_info['duration'] > 0 and file_info['duration'] < self.min_duration_seconds:
            # Exception pour les fichiers explicitement marqués comme samples
            filename_lower = file_info['filename'].lower()
            if not any(keyword in filename_lower for keyword in ['sample', 'intro', 'outro', 'interlude']):
                reasons.append(f"Durée très courte: {file_info['duration']:.1f} secondes")
        
        # Vérification 3: Fichier de durée nulle ou négative
        if file_info['duration'] <= 0:
            reasons.append("Durée invalide ou nulle")
        
        # Vérification 4: Bitrate très faible (si disponible)
        if file_info['bitrate'] > 0 and file_info['bitrate'] < self.min_bitrate_kbps:
            reasons.append(f"Bitrate très faible: {file_info['bitrate']} kbps")
        
        # Vérification 5: Ratio taille/durée anormal
        if file_info['duration'] > 0:
            mb_per_minute = file_info['file_size_mb'] / (file_info['duration'] / 60)
            # Seuil plus nuancé selon le format
            min_ratio = 0.08 if file_info['filename'].lower().endswith('.mp3') else 0.05
            if mb_per_minute < min_ratio:
                reasons.append(f"Ratio taille/durée anormal: {mb_per_minute:.3f} MB/min")
        
        # Vérification 6: Fichier de taille nulle
        if file_info['file_size'] == 0:
            reasons.append("Fichier vide (0 octets)")
        
        return reasons
    
    def format_duration(self, seconds):
        """Formate la durée en mm:ss"""
        if seconds <= 0:
            return "0:00"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def sanitize_folder_name(self, name):
        """Nettoie un nom selon les conventions Lidarr"""
        if not name or name.strip() == "":
            return "Unknown"
        
        # Normaliser Unicode
        name = unicodedata.normalize('NFKC', str(name)).strip()
        
        # Remplacer caractères interdits par Lidarr/système de fichiers
        replacements = {
            '/': '⧸', '\\': '∖', '|': '│', ':': '∶', '*': '✱', 
            '?': '？', '"': '"', '<': '‹', '>': '›',
            '\r': '', '\n': '', '\t': ' '
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Supprimer espaces multiples et nettoyer
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Supprimer points de fin (problématique Windows)
        name = name.rstrip('.')
        
        # Limiter la longueur (compatible Lidarr)
        if len(name) > 100:
            name = name[:97] + "..."
        
        return name or "Unknown"
    
    def get_audio_tags(self, file_path):
        """Extrait les tags audio d'un fichier"""
        try:
            audio = File(file_path)
            if not audio:
                return None
            
            # Fonctions pour extraire proprement les tags
            def get_tag_value(tags, keys):
                """Cherche une valeur dans plusieurs clés possibles"""
                for key in keys:
                    if key in tags:
                        value = tags[key]
                        if isinstance(value, list) and value:
                            return str(value[0]).strip()
                        elif value:
                            return str(value).strip()
                return ""
            
            tags = {}
            
            # Artiste
            artist = get_tag_value(audio, ['TPE1', 'ARTIST', 'Artist', '©ART', 'ALBUMARTIST', 'TPE2'])
            tags['artist'] = self.sanitize_folder_name(artist) if artist else "Unknown Artist"
            
            # Album
            album = get_tag_value(audio, ['TALB', 'ALBUM', 'Album', '©alb'])
            tags['album'] = self.sanitize_folder_name(album) if album else "Unknown Album"
            
            # Titre
            title = get_tag_value(audio, ['TIT2', 'TITLE', 'Title', '©nam'])
            if not title:
                # Utiliser le nom de fichier sans extension comme fallback
                title = os.path.splitext(os.path.basename(file_path))[0]
            tags['title'] = self.sanitize_folder_name(title)
            
            # Année
            year = get_tag_value(audio, ['TDRC', 'DATE', 'YEAR', 'Year', '©day'])
            if year and len(year) >= 4:
                try:
                    tags['year'] = str(int(year[:4]))
                except:
                    tags['year'] = ""
            else:
                tags['year'] = ""
            
            # Numéro de piste
            track = get_tag_value(audio, ['TRCK', 'TRACKNUMBER', 'Track', 'trkn'])
            if track:
                # Extraire juste le numéro (pas le total)
                track_num = track.split('/')[0] if '/' in track else track
                try:
                    tags['track'] = int(track_num)
                except:
                    tags['track'] = 0
            else:
                tags['track'] = 0
                
            return tags
            
        except Exception as e:
            self.logger.warning(f"Erreur lecture tags pour {file_path}: {e}")
            return None
    
    def get_acoustid_fingerprint(self, file_path):
        """Obtient l'empreinte AcoustID d'un fichier audio"""
        if not ACOUSTID_AVAILABLE:
            return None
            
        try:
            # Générer l'empreinte acoustique
            duration, fingerprint = acoustid.fingerprint_file(file_path)
            return {'duration': duration, 'fingerprint': fingerprint}
        except Exception as e:
            self.logger.warning(f"Erreur AcoustID pour {file_path}: {e}")
            return None
    
    def search_acoustid(self, file_path):
        """Recherche les métadonnées via AcoustID + MusicBrainz"""
        if not ACOUSTID_AVAILABLE:
            return None
            
        try:
            fingerprint_data = self.get_acoustid_fingerprint(file_path)
            if not fingerprint_data:
                return None
            
            # Recherche sur AcoustID
            results = acoustid.match(self.acoustid_api_key, 
                                   fingerprint_data['fingerprint'], 
                                   fingerprint_data['duration'])
            
            for score, recording_id, title, artist in results:
                if score > 0.8:  # Seuil de confiance
                    return {
                        'artist': self.sanitize_folder_name(artist) if artist else "Unknown Artist",
                        'title': self.sanitize_folder_name(title) if title else "Unknown Title",
                        'score': score,
                        'source': 'AcoustID'
                    }
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur recherche AcoustID pour {file_path}: {e}")
            return None
    
    def search_lastfm(self, artist=None, title=None, filename=None):
        """Recherche les métadonnées via Last.fm"""
        if not LASTFM_AVAILABLE:
            return None
            
        try:
            # Si pas d'artiste/titre, essayer d'extraire du nom de fichier
            if not artist or not title:
                if filename:
                    # Patterns courants : "Artist - Title" ou "Title - Artist"
                    basename = os.path.splitext(os.path.basename(filename))[0]
                    
                    # Nettoyer le nom de fichier
                    basename = re.sub(r'\d+\s*-\s*', '', basename)  # Supprimer numéro de piste
                    basename = re.sub(r'\[.*?\]|\(.*?\)', '', basename)  # Supprimer tags entre []()
                    
                    if ' - ' in basename:
                        parts = basename.split(' - ', 1)
                        artist = artist or parts[0].strip()
                        title = title or parts[1].strip()
                    else:
                        title = title or basename.strip()
                        
            if not artist or not title:
                return None
            
            # Recherche sur Last.fm
            network = pylast.LastFMNetwork(api_key=self.lastfm_api_key, 
                                         api_secret=self.lastfm_api_secret)
            
            track = network.get_track(artist, title)
            track_info = track.get_correction()
            
            if track_info:
                album_name = None
                year = None
                
                # Essayer de récupérer l'album
                try:
                    album = track.get_album()
                    if album:
                        album_name = album.get_name()
                        # Essayer de récupérer l'année de sortie
                        try:
                            release_date = album.get_wiki_published_date()
                            if release_date:
                                year = str(release_date.year)
                        except:
                            pass
                except:
                    pass
                
                return {
                    'artist': self.sanitize_folder_name(track_info.get_artist().get_name()),
                    'title': self.sanitize_folder_name(track_info.get_name()),
                    'album': self.sanitize_folder_name(album_name) if album_name else "Unknown Album",
                    'year': year or "",
                    'source': 'Last.fm'
                }
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur recherche Last.fm pour {artist} - {title}: {e}")
            return None
    
    def get_enhanced_tags(self, file_path):
        """Obtient les tags avec enrichissement en ligne si nécessaire"""
        # D'abord, essayer les tags existants
        tags = self.get_audio_tags(file_path)
        
        if not self.online_mode:
            return tags
        
        # Si tags incomplets et mode en ligne activé, enrichir
        needs_enrichment = (not tags or 
                           tags.get('artist') == 'Unknown Artist' or
                           tags.get('title') == 'Unknown' or
                           tags.get('album') == 'Unknown Album')
        
        if needs_enrichment:
            print(f"   🌐 Recherche en ligne pour: {os.path.basename(file_path)}")
            
            enriched_tags = None
            
            # 1. Essayer AcoustID d'abord (plus précis)
            if ACOUSTID_AVAILABLE:
                print(f"   🎵 Tentative AcoustID...")
                time.sleep(0.5)  # Rate limiting
                acoustid_result = self.search_acoustid(file_path)
                if acoustid_result:
                    enriched_tags = acoustid_result
                    print(f"   {self.COLOR_GREEN}✅ AcoustID: {acoustid_result['artist']} - {acoustid_result['title']}{self.COLOR_RESET}")
            
            # 2. Si AcoustID échoue, essayer Last.fm
            if not enriched_tags and LASTFM_AVAILABLE:
                print(f"   📡 Tentative Last.fm...")
                time.sleep(0.5)  # Rate limiting
                lastfm_result = self.search_lastfm(
                    artist=tags.get('artist') if tags else None,
                    title=tags.get('title') if tags else None,
                    filename=file_path
                )
                if lastfm_result:
                    enriched_tags = lastfm_result
                    print(f"   {self.COLOR_GREEN}✅ Last.fm: {lastfm_result['artist']} - {lastfm_result['title']}{self.COLOR_RESET}")
            
            # 3. Fusionner les tags enrichis avec les existants
            if enriched_tags:
                if tags:
                    # Garder les bonnes valeurs existantes, remplacer les mauvaises
                    if tags['artist'] == 'Unknown Artist' or not tags['artist']:
                        tags['artist'] = enriched_tags.get('artist', 'Unknown Artist')
                    if tags['title'] == 'Unknown' or not tags['title']:
                        tags['title'] = enriched_tags.get('title', 'Unknown')
                    if tags['album'] == 'Unknown Album' or not tags['album']:
                        tags['album'] = enriched_tags.get('album', 'Unknown Album')
                    if not tags['year']:
                        tags['year'] = enriched_tags.get('year', '')
                else:
                    # Créer de nouveaux tags
                    tags = {
                        'artist': enriched_tags.get('artist', 'Unknown Artist'),
                        'title': enriched_tags.get('title', 'Unknown'),
                        'album': enriched_tags.get('album', 'Unknown Album'),
                        'year': enriched_tags.get('year', ''),
                        'track': 0
                    }
                
                self.enriched_files.append({
                    'file': file_path,
                    'source': enriched_tags.get('source', 'Online'),
                    'tags': enriched_tags
                })
                print(f"   {self.COLOR_GREEN}🎯 Tags enrichis!{self.COLOR_RESET}")
            else:
                print(f"   {self.COLOR_RED}❌ Aucun résultat en ligne{self.COLOR_RESET}")
        
        return tags
    
    def organize_file(self, file_path, dry_run=True):
        """Organise un fichier selon la structure Lidarr avec enrichissement optionnel"""
        try:
            # Utiliser les tags enrichis si mode en ligne activé
            tags = self.get_enhanced_tags(file_path) if self.online_mode else self.get_audio_tags(file_path)
            
            if not tags:
                self.logger.warning(f"Tags non lisibles pour {file_path}")
                return False
            
            # Construire le chemin de destination Lidarr
            artist = tags['artist']
            album = tags['album']
            title = tags['title']
            year = tags['year']
            track = tags['track']
            
            # Structure Lidarr : Artist/Album (Year)/Title.ext
            if year:
                album_folder = f"{album} ({year})"
            else:
                album_folder = album
                
            dest_dir = os.path.join(self.dest_dir, artist, album_folder)
            
            # Nom du fichier final - structure Lidarr simple
            file_ext = os.path.splitext(file_path)[1]
            if track > 0:
                filename = f"{track:02d} - {title}{file_ext}"
            else:
                filename = f"{title}{file_ext}"
            
            dest_path = os.path.join(dest_dir, filename)
            
            # Éviter d'écraser des fichiers existants
            counter = 1
            original_dest_path = dest_path
            while os.path.exists(dest_path) and os.path.abspath(dest_path) != os.path.abspath(file_path):
                name, ext = os.path.splitext(original_dest_path)
                dest_path = f"{name} ({counter}){ext}"
                counter += 1
            
            if dry_run:
                print(f"📁 {os.path.basename(file_path)} → {artist}/{album_folder}/{filename}")
                return True
            else:
                # Créer les dossiers
                os.makedirs(dest_dir, exist_ok=True)
                
                # Déplacer le fichier
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    shutil.move(file_path, dest_path)
                    self.organized_files.append({
                        'original': file_path,
                        'destination': dest_path,
                        'artist': artist,
                        'album': album,
                        'title': title
                    })
                    print(f"{self.COLOR_GREEN}✅ Organisé: {os.path.basename(file_path)} → {artist}/{album_folder}/{self.COLOR_RESET}")
                    return True
                else:
                    print(f"{self.COLOR_BLUE}📍 Déjà au bon endroit: {os.path.basename(file_path)}{self.COLOR_RESET}")
                    return True
                    
        except Exception as e:
            error_msg = f"Erreur organisation pour {file_path}: {e}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def save_deletion_report(self, suspect_files, deleted_files):
        """Sauvegarde un rapport des fichiers supprimés"""
        try:
            report_filename = f"deletion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'music_directory': self.music_dir,
                'thresholds': {
                    'min_file_size_mb': self.min_file_size_mb,
                    'min_duration_seconds': self.min_duration_seconds,
                    'min_bitrate_kbps': self.min_bitrate_kbps
                },
                'suspect_files': suspect_files,
                'deleted_files': deleted_files,
                'total_deleted': len(deleted_files),
                'errors': self.errors
            }
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            print(f"{self.COLOR_BLUE}📄 Rapport sauvegardé: {report_filename}{self.COLOR_RESET}")
            self.logger.info(f"Rapport sauvegardé: {report_filename}")
            
        except Exception as e:
            error_msg = f"Erreur lors de la sauvegarde du rapport: {e}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
    
    def scan_and_clean(self, dry_run=True):
        """Scanne et nettoie OU organise le répertoire selon le mode choisi"""
        if self.organize_mode:
            return self.organize_files(dry_run)
        else:
            return self.clean_files(dry_run)
    
    def organize_files(self, dry_run=True):
        """Mode organisation : organise les fichiers selon la structure Lidarr"""
        print(f"🎵 ORGANISATION POUR LIDARR")
        print(f"📂 Source: {self.music_dir}")
        print(f"📁 Destination: {self.dest_dir}")
        print(f"📁 Structure: Artist/Album (Year)/[00 - ]Title.ext")
        print(f"📁 Mode: {'SIMULATION' if dry_run else 'ORGANISATION RÉELLE'}")
        print("=" * 60)
        
        # Vérifier l'accès au répertoire
        if not os.path.exists(self.music_dir):
            error_msg = f"Répertoire source inexistant: {self.music_dir}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
            
        if not os.access(self.music_dir, os.R_OK):
            error_msg = f"Répertoire source non accessible: {self.music_dir}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
        
        # Créer le dossier de destination si nécessaire
        if not dry_run:
            os.makedirs(self.dest_dir, exist_ok=True)
        
        # Collecter les fichiers audio
        audio_files = []
        try:
            for root, dirs, files in os.walk(self.music_dir):
                # Ignorer les dossiers cachés
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.lower().endswith(self.audio_extensions) and not file.startswith('.'):
                        audio_files.append(os.path.join(root, file))
        except Exception as e:
            error_msg = f"Erreur lors du parcours: {e}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
        
        print(f"📄 {len(audio_files)} fichiers audio trouvés")
        
        if not audio_files:
            print("ℹ️  Aucun fichier audio trouvé")
            return []
        
        organized_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(audio_files, 1):
            progress = (i / len(audio_files)) * 100
            print(f"\n[{i}/{len(audio_files)} - {progress:.1f}%] {os.path.basename(file_path)}")
            
            if self.organize_file(file_path, dry_run):
                organized_count += 1
            else:
                failed_count += 1
        
        # Résumé organisation
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ ORGANISATION LIDARR")
        print(f"📄 Fichiers traités: {len(audio_files)}")
        print(f"✅ Fichiers organisés: {organized_count}")
        print(f"{self.COLOR_RED}❌ Échecs: {failed_count}{self.COLOR_RESET}")
        
        if self.online_mode and self.enriched_files:
            print(f"🌐 Fichiers enrichis en ligne: {len(self.enriched_files)}")
            
        if not dry_run and self.organized_files:
            print(f"\n📁 STRUCTURE LIDARR CRÉÉE:")
            artists = {}
            for f in self.organized_files:
                artist = f['artist']
                if artist not in artists:
                    artists[artist] = set()
                artists[artist].add(f['album'])
            
            for artist, albums in artists.items():
                print(f"   📁 {artist}/ ({len(albums)} album{'s' if len(albums) > 1 else ''})")
                for album in sorted(albums):
                    print(f"      📁 {album}/")
            
            print(f"\n🎯 Compatible avec Lidarr, Plex et autres serveurs médias")
            
        # Afficher détails des enrichissements
        if self.online_mode and self.enriched_files and not dry_run:
            print(f"\n🌐 DÉTAILS ENRICHISSEMENTS:")
            for item in self.enriched_files:
                print(f"   📁 {os.path.basename(item['file'])}")
                print(f"      🔍 Source: {item['source']}")
                tags = item['tags']
                print(f"      🎵 {tags.get('artist', 'N/A')} - {tags.get('title', 'N/A')}")
                if tags.get('album'):
                    print(f"      💿 Album: {tags['album']}")
                print()
        
        return self.organized_files if not dry_run else []
    
    def clean_files(self, dry_run=True):
        """Mode nettoyage : nettoie les fichiers suspects"""
        print(f"🧹 NETTOYAGE DES FICHIERS SUSPECTS")
        print(f"📂 Répertoire: {self.music_dir}")
        print(f"📁 Mode: {'SIMULATION' if dry_run else 'SUPPRESSION RÉELLE'}")
        print("=" * 60)
        
        # Vérifier l'accès au répertoire
        if not os.path.exists(self.music_dir):
            error_msg = f"Répertoire inexistant: {self.music_dir}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
            
        if not os.access(self.music_dir, os.R_OK):
            error_msg = f"Répertoire non accessible en lecture: {self.music_dir}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
        
        # Collecter les fichiers audio
        audio_files = []
        try:
            for root, dirs, files in os.walk(self.music_dir):
                # Ignorer les dossiers cachés et système
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    if file.lower().endswith(self.audio_extensions) and not file.startswith('.'):
                        audio_files.append(os.path.join(root, file))
        except PermissionError as e:
            error_msg = f"Permission refusée lors du parcours: {e}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
        except Exception as e:
            error_msg = f"Erreur lors du parcours: {e}"
            print(f"{self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
            self.logger.error(error_msg)
            return []
        
        print(f"📄 {len(audio_files)} fichiers audio trouvés")
        self.logger.info(f"Fichiers audio trouvés: {len(audio_files)}")
        
        if not audio_files:
            print("ℹ️  Aucun fichier audio trouvé")
            return []
        
        suspect_files = []
        
        for i, file_path in enumerate(audio_files, 1):
            # Affichage du progrès
            progress = (i / len(audio_files)) * 100
            print(f"\n[{i}/{len(audio_files)} - {progress:.1f}%] {os.path.basename(file_path)}")
            
            file_info = self.get_file_info(file_path)
            if not file_info:
                continue
            
            self.processed_files += 1
            
            # Afficher infos
            print(f"   📏 {self.format_duration(file_info['duration'])}")
            print(f"   💾 {file_info['file_size_mb']:.2f} MB")
            if file_info['bitrate'] > 0:
                print(f"   🎵 {file_info['bitrate']} kbps")
            
            # Vérifier si suspect
            reasons = self.is_file_suspect(file_info)
            
            if reasons:
                print(f"   {self.COLOR_RED}❌ FICHIER SUSPECT:{self.COLOR_RESET}")
                for reason in reasons:
                    print(f"      - {reason}")
                
                suspect_files.append({
                    'info': file_info,
                    'reasons': reasons
                })
                self.logger.warning(f"Fichier suspect: {file_path} - {', '.join(reasons)}")
            else:
                print(f"   {self.COLOR_GREEN}✅ OK{self.COLOR_RESET}")
        
        # Résumé
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ")
        print(f"📄 Fichiers analysés: {self.processed_files}")
        print(f"⚠️  Fichiers suspects: {len(suspect_files)}")
        
        if self.renamed_files:
            print(f"📝 Fichiers renommés: {len(self.renamed_files)}")
        
        if self.errors:
            print(f"{self.COLOR_RED}❌ Erreurs rencontrées: {len(self.errors)}{self.COLOR_RESET}")
        
        if self.renamed_files:
            print(f"\n📝 FICHIERS RENOMMÉS:")
            for rename_info in self.renamed_files:
                print(f"   {rename_info['original']} -> {rename_info['new']}")
        
        if suspect_files:
            total_size = sum(f['info']['file_size_mb'] for f in suspect_files)
            print(f"💾 Espace à libérer: {total_size:.2f} MB")
            
            print(f"\n🗑️  FICHIERS SUSPECTS:")
            for item in suspect_files:
                file_info = item['info']
                print(f"\n📄 {file_info['filename']}")
                print(f"   📍 {file_info['file_path']}")
                print(f"   💾 {file_info['file_size_mb']:.2f} MB - 📏 {self.format_duration(file_info['duration'])}")
                for reason in item['reasons']:
                    print(f"   {self.COLOR_RED}❌ {reason}{self.COLOR_RESET}")
            
            if not dry_run:
                # Suppression réelle
                print(f"\n🗑️  SUPPRESSION EN COURS...")
                deleted_count = 0
                
                for item in suspect_files:
                    file_path = item['info']['file_path']
                    try:
                        # Vérifier une dernière fois que le fichier existe
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            self.deleted_files.append(file_path)
                            deleted_count += 1
                            print(f"   {self.COLOR_GREEN}✅ Supprimé: {os.path.basename(file_path)}{self.COLOR_RESET}")
                            self.logger.info(f"Fichier supprimé: {file_path}")
                        else:
                            print(f"   {self.COLOR_YELLOW}⚠️  Fichier déjà supprimé: {os.path.basename(file_path)}{self.COLOR_RESET}")
                    except PermissionError as e:
                        error_msg = f"Permission refusée pour supprimer {file_path}: {e}"
                        print(f"   {self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
                        self.logger.error(error_msg)
                        self.errors.append(error_msg)
                    except Exception as e:
                        error_msg = f"Erreur lors de la suppression de {file_path}: {e}"
                        print(f"   {self.COLOR_RED}❌ {error_msg}{self.COLOR_RESET}")
                        self.logger.error(error_msg)
                        self.errors.append(error_msg)
                
                print(f"\n{self.COLOR_GREEN}✅ {deleted_count} fichiers supprimés sur {len(suspect_files)} suspects!{self.COLOR_RESET}")
                
                # Sauvegarder le rapport
                self.save_deletion_report(suspect_files, self.deleted_files)
        
        else:
            print(f"\n{self.COLOR_GREEN}✅ Aucun fichier suspect détecté!{self.COLOR_RESET}")
            self.logger.info("Aucun fichier suspect détecté")
        
        return suspect_files

def main():
    """Fonction principale avec choix du mode"""
    print("🎵 GESTIONNAIRE AUDIO RAPIDE LIDARR")
    print("Nettoyage et organisation compatible Lidarr/Plex")
    print("=" * 60)
    
    # Afficher l'état des dépendances en ligne
    online_available = []
    if ACOUSTID_AVAILABLE:
        online_available.append("AcoustID")
    if LASTFM_AVAILABLE:
        online_available.append("Last.fm")
    
    if online_available:
        print(f"🌐 Recherche en ligne disponible: {', '.join(online_available)}")
    else:
        print("📴 Mode hors ligne uniquement (pas de dépendances pour recherche en ligne)")
    print()
    
    # Choix du mode
    print("CHOISISSEZ LE MODE :")
    print("1. 🧹 Nettoyer uniquement (supprime les fichiers audio suspects)")
    print("2. 📁 Organiser uniquement (structure Artist/Album (Année), hors ligne)")
    if online_available:
        print("3. 🌐 Organiser uniquement (structure Artist/Album (Année), enrichissement tags en ligne)")
        print("4. 🔧 Nettoyer puis organiser (hors ligne)")
        print("5. 🔧 Nettoyer puis organiser (enrichissement tags en ligne)")
        max_choice = '5'
    else:
        print("3. 🔧 Nettoyer puis organiser (hors ligne)")
        max_choice = '3'
    
    while True:
        choice = input(f"\nVotre choix (1-{max_choice}): ").strip()
        if choice in ['1', '2', '3', '4', '5'] and int(choice) <= int(max_choice):
            break
        print(f"\033[31m❌ Choix invalide. Tapez 1 à {max_choice}.\033[0m")
    
    # Déterminer le mode en ligne
    if online_available:
        online_mode = choice in ['3', '5'] if max_choice == '5' else False
        organize_mode = choice in ['2', '3', '4', '5'] if max_choice == '5' else choice in ['2', '3']
        clean_mode = choice in ['1', '4', '5'] if max_choice == '5' else choice in ['1', '3']
        combined_mode = choice in ['4', '5'] if max_choice == '5' else choice == '3'
    else:
        online_mode = False
        organize_mode = choice in ['2', '3']
        clean_mode = choice in ['1', '3']
        combined_mode = choice == '3'
    
    # Dossier source
    default_dir = "/mnt/mybook/itunes/Music"
    print(f"\n📂 Dossier source par défaut: {default_dir}")
    custom_dir = input("Appuyez sur Entrée ou tapez un autre chemin: ").strip()
    music_dir = custom_dir if custom_dir else default_dir
    
    if not os.path.exists(music_dir):
        print(f"\033[31m❌ Dossier inexistant: {music_dir}\033[0m")
        return
    
    # Dossier destination pour organisation Lidarr
    dest_dir = None
    if organize_mode:
        default_dest = "/mnt/mybook/Musiques/Organisé_Lidarr"
        print(f"\n📁 Dossier destination par défaut: {default_dest}")
        custom_dest = input("Appuyez sur Entrée ou tapez un autre chemin: ").strip()
        dest_dir = custom_dest if custom_dest else default_dest
    
    # Affichage du mode sélectionné
    if online_mode:
        print(f"\n🌐 MODE EN LIGNE ACTIVÉ")
        if online_available:
            print(f"   Recherche: {' + '.join(online_available)}")
            print(f"   ⚡ Plus lent mais tags enrichis pour fichiers sans métadonnées")
    
    # Mode nettoyage seul : suppression directe sans simulation ni confirmation
    if clean_mode and not combined_mode:
        cleaner = SimpleMusicCleaner(music_dir, organize_mode=False, online_mode=False)
        print(f"\n⚙️  SEUILS DE DÉTECTION:")
        print(f"📏 Taille minimum: {cleaner.min_file_size_mb} MB")
        print(f"⏱️  Durée minimum: {cleaner.min_duration_seconds} secondes")
        print(f"🎵 Bitrate minimum: {cleaner.min_bitrate_kbps} kbps")
        print(f"\n🗑️  SUPPRESSION DIRECTE DES FICHIERS SUSPECTS...")
        suspect_files = cleaner.scan_and_clean(dry_run=False)
        if suspect_files:
            print(f"\n✅ {len(suspect_files)} fichiers suspects supprimés.")
        else:
            print("✅ Aucun fichier suspect détecté!")
    
    # Mode organisation seul
    elif organize_mode and not combined_mode:
        cleaner = SimpleMusicCleaner(music_dir, organize_mode=True, dest_dir=dest_dir, online_mode=online_mode)
        
        mode_text = "AVEC RECHERCHE EN LIGNE" if online_mode else "HORS LIGNE"
        print(f"\n🔍 SIMULATION ORGANISATION LIDARR {mode_text}")
        print(f"Structure: Artist/Album (Year)/[00 - ]Title.ext")
        if online_mode:
            print("⚠️  La recherche en ligne peut prendre du temps...")
        input("Appuyez sur Entrée pour voir le plan d'organisation...")
        cleaner.scan_and_clean(dry_run=True)
        
        confirm = input(f"\nProcéder à l'organisation Lidarr ? (O/n): ").strip().lower()
        
        if confirm in ['', 'o', 'oui', 'y', 'yes']:
            print(f"\n📁 ORGANISATION LIDARR EN COURS...")
            if online_mode:
                print("🌐 Recherche en ligne activée - patience...")
            input("Appuyez sur Entrée pour commencer...")
            cleaner.scan_and_clean(dry_run=False)
            print(f"\n✅ Organisation Lidarr terminée dans: {dest_dir}")
        else:
            print("\033[31m❌ Annulé\033[0m")
    
    # Mode combiné (nettoyage + organisation) : suppression directe et organisation sans confirmation
    elif combined_mode:
        print(f"\n🔄 MODE COMBINÉ : Nettoyage puis Organisation")
        mode_text = "avec recherche en ligne" if online_mode else "hors ligne"
        print(f"Organisation {mode_text}")
        # Étape 1: Nettoyage direct
        print(f"\n--- ÉTAPE 1: NETTOYAGE ---")
        cleaner = SimpleMusicCleaner(music_dir, organize_mode=False, online_mode=False)
        print(f"\n⚙️  SEUILS DE DÉTECTION:")
        print(f"📏 Taille minimum: {cleaner.min_file_size_mb} MB")
        print(f"⏱️  Durée minimum: {cleaner.min_duration_seconds} secondes")
        print(f"🎵 Bitrate minimum: {cleaner.min_bitrate_kbps} kbps")
        print(f"\n🗑️  SUPPRESSION DIRECTE DES FICHIERS SUSPECTS...")
        suspect_files = cleaner.scan_and_clean(dry_run=False)
        if suspect_files:
            print(f"\n✅ {len(suspect_files)} fichiers suspects supprimés.")
        else:
            print("✅ Aucun fichier suspect, passage à l'organisation")
        # Étape 2: Organisation directe
        print(f"\n--- ÉTAPE 2: ORGANISATION LIDARR ---")
        organizer = SimpleMusicCleaner(music_dir, organize_mode=True, dest_dir=dest_dir, online_mode=online_mode)
        if online_mode:
            print("🌐 Mode en ligne - recherche des tags manquants")
        print(f"\n📁 ORGANISATION LIDARR EN COURS...")
        organizer.scan_and_clean(dry_run=False)
        print(f"\n✅ Workflow terminé!")
        print(f"📁 Fichiers organisés (structure Lidarr) dans: {dest_dir}")
    
    print(f"\n🏁 Terminé!")

if __name__ == "__main__":
    main()
