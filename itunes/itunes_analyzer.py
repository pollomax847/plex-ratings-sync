#!/usr/bin/env python3
"""
iTunes XML Library Manager - Version robuste
Gestionnaire robuste pour les bibliothèques iTunes XML
"""

import xml.etree.ElementTree as ET
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
import re
from collections import defaultdict
import urllib.parse

class iTunesLibraryRobust:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.tree = None
        self.root = None
        self.tracks = {}
        self.playlists = {}
        self.stats = {}
        
    def load_library(self):
        """Charge la bibliothèque iTunes de manière robuste"""
        print(f"📚 Chargement de {self.xml_file}...")
        try:
            # Lecture du fichier avec gestion d'encodage
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse XML
            self.tree = ET.fromstring(content)
            
            # Trouver le dict principal
            main_dict = self.tree.find('dict')
            if main_dict is None:
                raise Exception("Structure iTunes XML invalide")
            
            self._parse_tracks_robust(main_dict)
            self._parse_playlists_robust(main_dict)
            self._calculate_stats()
            
            print(f"✅ Bibliothèque chargée : {len(self.tracks)} pistes, {len(self.playlists)} playlists")
            return True
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            return False
    
    def _parse_tracks_robust(self, main_dict):
        """Parse les pistes de manière robuste"""
        print("🔍 Parsing des pistes...")
        
        # Trouver la section Tracks
        elements = list(main_dict)
        tracks_found = False
        
        for i, elem in enumerate(elements):
            if elem.tag == 'key' and elem.text == 'Tracks':
                if i + 1 < len(elements) and elements[i + 1].tag == 'dict':
                    tracks_dict = elements[i + 1]
                    tracks_found = True
                    break
        
        if not tracks_found:
            print("⚠️  Section Tracks non trouvée")
            return
        
        # Parser chaque piste
        track_elements = list(tracks_dict)
        current_track_id = None
        
        for i in range(0, len(track_elements), 2):
            if i + 1 >= len(track_elements):
                break
                
            key_elem = track_elements[i]
            value_elem = track_elements[i + 1]
            
            if key_elem.tag == 'key' and value_elem.tag == 'dict':
                track_id = key_elem.text
                track_data = self._parse_dict_robust(value_elem)
                self.tracks[track_id] = track_data
        
        print(f"✅ {len(self.tracks)} pistes parsées")
    
    def _parse_playlists_robust(self, main_dict):
        """Parse les playlists de manière robuste"""
        print("🔍 Parsing des playlists...")
        
        # Trouver la section Playlists
        elements = list(main_dict)
        playlists_found = False
        
        for i, elem in enumerate(elements):
            if elem.tag == 'key' and elem.text == 'Playlists':
                if i + 1 < len(elements) and elements[i + 1].tag == 'array':
                    playlists_array = elements[i + 1]
                    playlists_found = True
                    break
        
        if not playlists_found:
            print("⚠️  Section Playlists non trouvée")
            return
        
        # Parser chaque playlist
        for playlist_dict in playlists_array.findall('dict'):
            playlist_data = self._parse_dict_robust(playlist_dict)
            if 'Name' in playlist_data:
                self.playlists[playlist_data['Name']] = playlist_data
        
        print(f"✅ {len(self.playlists)} playlists parsées")
    
    def _parse_dict_robust(self, dict_elem):
        """Parse un dictionnaire XML de manière robuste"""
        data = {}
        elements = list(dict_elem)
        
        for i in range(0, len(elements), 2):
            if i + 1 >= len(elements):
                break
                
            key_elem = elements[i]
            value_elem = elements[i + 1]
            
            if key_elem.tag != 'key':
                continue
                
            key = key_elem.text
            if key is None:
                continue
            
            # Parser la valeur selon son type
            if value_elem.tag == 'string':
                data[key] = value_elem.text or ''
            elif value_elem.tag == 'integer':
                try:
                    data[key] = int(value_elem.text) if value_elem.text else 0
                except ValueError:
                    data[key] = 0
            elif value_elem.tag == 'true':
                data[key] = True
            elif value_elem.tag == 'false':
                data[key] = False
            elif value_elem.tag == 'date':
                data[key] = value_elem.text or ''
            elif value_elem.tag == 'array':
                # Pour les playlists (Track IDs)
                if key == 'Playlist Items':
                    track_ids = []
                    for item_dict in value_elem.findall('dict'):
                        item_data = self._parse_dict_robust(item_dict)
                        if 'Track ID' in item_data:
                            track_ids.append(str(item_data['Track ID']))
                    data['Track IDs'] = track_ids
        
        return data
    
    def _calculate_stats(self):
        """Calcule les statistiques de la bibliothèque"""
        print("📊 Calcul des statistiques...")
        
        self.stats = {
            'total_tracks': len(self.tracks),
            'total_playlists': len(self.playlists),
            'file_formats': defaultdict(int),
            'missing_files': 0,
            'total_size': 0,
            'total_time': 0,
            'artists': set(),
            'albums': set(),
            'years': defaultdict(int),
            'genres': defaultdict(int),
            'locations': defaultdict(int)
        }
        
        for track_id, track in self.tracks.items():
            # Format de fichier
            if 'Kind' in track:
                kind = track['Kind']
                self.stats['file_formats'][kind] += 1
            
            # Taille et durée
            if 'Size' in track and isinstance(track['Size'], int):
                self.stats['total_size'] += track['Size']
            
            if 'Total Time' in track and isinstance(track['Total Time'], int):
                self.stats['total_time'] += track['Total Time']
            
            # Métadonnées
            if 'Artist' in track and track['Artist']:
                self.stats['artists'].add(track['Artist'])
            
            if 'Album' in track and track['Album']:
                self.stats['albums'].add(track['Album'])
            
            if 'Year' in track and isinstance(track['Year'], int):
                self.stats['years'][track['Year']] += 1
            
            if 'Genre' in track and track['Genre']:
                self.stats['genres'][track['Genre']] += 1
            
            # Localisation des fichiers
            if 'Location' in track:
                location = track['Location']
                # Extraire le chemin de base
                if location.startswith('file://'):
                    decoded_path = urllib.parse.unquote(location)
                    # Trouver le préfixe du chemin
                    if 'Musiques/' in decoded_path:
                        prefix = decoded_path.split('Musiques/')[0] + 'Musiques/'
                        self.stats['locations'][prefix] += 1
                    
                    # Vérifier si le fichier existe
                    file_path = decoded_path.replace('file://', '')
                    if not os.path.exists(file_path):
                        self.stats['missing_files'] += 1
            else:
                self.stats['missing_files'] += 1
        
        # Conversion des sets en nombres
        self.stats['total_artists'] = len(self.stats['artists'])
        self.stats['total_albums'] = len(self.stats['albums'])
    
    def show_stats(self):
        """Affiche les statistiques de base"""
        print("\n" + "="*50)
        print("📊 STATISTIQUES DE LA BIBLIOTHÈQUE")
        print("="*50)
        print(f"🎵 Pistes totales      : {self.stats['total_tracks']:,}")
        print(f"📁 Playlists          : {self.stats['total_playlists']:,}")
        print(f"🎤 Artistes uniques   : {self.stats['total_artists']:,}")
        print(f"💿 Albums uniques     : {self.stats['total_albums']:,}")
        print(f"❌ Fichiers manquants : {self.stats['missing_files']:,}")
        
        # Taille et durée
        if self.stats['total_size'] > 0:
            total_gb = self.stats['total_size'] / (1024**3)
            print(f"💾 Taille totale      : {total_gb:.2f} GB")
        
        if self.stats['total_time'] > 0:
            total_hours = self.stats['total_time'] / (1000 * 3600)
            print(f"⏰ Durée totale       : {total_hours:.1f} heures")
    
    def show_locations(self):
        """Affiche les emplacements de fichiers"""
        print("\n📍 EMPLACEMENTS DES FICHIERS")
        print("-" * 40)
        
        for location, count in sorted(self.stats['locations'].items(), 
                                    key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{count:6,} ({percentage:5.1f}%) : {location}")
    
    def show_formats(self):
        """Affiche les formats de fichiers"""
        print("\n🎵 FORMATS DE FICHIERS")
        print("-" * 40)
        
        for format_name, count in sorted(self.stats['file_formats'].items(), 
                                       key=lambda x: x[1], reverse=True)[:15]:
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{count:6,} ({percentage:5.1f}%) : {format_name}")
    
    def show_genres(self):
        """Affiche les genres musicaux"""
        print("\n🎭 GENRES MUSICAUX (Top 15)")
        print("-" * 40)
        
        for genre, count in sorted(self.stats['genres'].items(), 
                                 key=lambda x: x[1], reverse=True)[:15]:
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{count:6,} ({percentage:5.1f}%) : {genre}")
    
    def show_years(self):
        """Affiche la distribution par années"""
        print("\n📅 DISTRIBUTION PAR ANNÉES (Top 15)")
        print("-" * 40)
        
        valid_years = {year: count for year, count in self.stats['years'].items() 
                      if 1900 <= year <= datetime.now().year}
        
        for year, count in sorted(valid_years.items(), 
                                key=lambda x: x[1], reverse=True)[:15]:
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{count:6,} ({percentage:5.1f}%) : {year}")
    
    def find_path_patterns(self):
        """Analyse les patterns de chemins pour proposer des mises à jour"""
        print("\n🔍 ANALYSE DES CHEMINS DE FICHIERS")
        print("-" * 50)
        
        path_patterns = defaultdict(int)
        sample_paths = []
        
        for track_id, track in self.tracks.items():
            if 'Location' in track:
                location = track['Location']
                if location.startswith('file://'):
                    decoded_path = urllib.parse.unquote(location)
                    
                    # Extraire les patterns courants
                    if 'E:/' in decoded_path:
                        path_patterns['E:/'] += 1
                        if len(sample_paths) < 3:
                            sample_paths.append(decoded_path)
                    elif '/mnt/' in decoded_path:
                        path_patterns['/mnt/'] += 1
                    elif 'C:/' in decoded_path:
                        path_patterns['C:/'] += 1
        
        print("Patterns détectés :")
        for pattern, count in sorted(path_patterns.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"  {pattern:10} : {count:6,} pistes ({percentage:5.1f}%)")
        
        if sample_paths:
            print(f"\nExemples de chemins trouvés :")
            for path in sample_paths:
                print(f"  {path}")
        
        # Suggestions de mise à jour
        print(f"\n💡 SUGGESTIONS DE MISE À JOUR")
        print("-" * 40)
        
        if path_patterns.get('E:/', 0) > 0:
            print(f"✅ Détecté {path_patterns['E:/']} pistes avec 'E:/'")
            print(f"   Suggestion : --update-paths 'file://E:/' 'file:///mnt/mybook/'")
        
        if self.stats['missing_files'] > 0:
            print(f"⚠️  {self.stats['missing_files']} fichiers manquants détectés")
            print(f"   Suggestion : --remove-missing pour nettoyer")

def main():
    parser = argparse.ArgumentParser(description='Gestionnaire robuste de bibliothèque iTunes XML')
    parser.add_argument('xml_file', nargs='?', default='iTunes Music Library.xml',
                       help='Fichier XML de la bibliothèque iTunes')
    parser.add_argument('--stats', action='store_true',
                       help='Afficher les statistiques de base')
    parser.add_argument('--detailed', action='store_true',
                       help='Afficher les statistiques détaillées')
    parser.add_argument('--locations', action='store_true',
                       help='Afficher les emplacements de fichiers')
    parser.add_argument('--formats', action='store_true',
                       help='Afficher les formats de fichiers')
    parser.add_argument('--genres', action='store_true',
                       help='Afficher les genres musicaux')
    parser.add_argument('--years', action='store_true',
                       help='Afficher la distribution par années')
    parser.add_argument('--paths', action='store_true',
                       help='Analyser les patterns de chemins')
    parser.add_argument('--all', action='store_true',
                       help='Afficher toutes les informations')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.xml_file):
        print(f"❌ Fichier non trouvé : {args.xml_file}")
        print(f"💡 Vérifiez que le fichier existe ou copiez-le depuis /mnt/mybook/Musiques/")
        sys.exit(1)
    
    # Charger la bibliothèque
    library = iTunesLibraryRobust(args.xml_file)
    if not library.load_library():
        sys.exit(1)
    
    # Affichage des informations demandées
    if args.stats or args.all or not any([args.detailed, args.locations, args.formats, args.genres, args.years, args.paths]):
        library.show_stats()
    
    if args.detailed or args.all:
        library.show_formats()
        library.show_genres()
        library.show_years()
    
    if args.locations or args.all:
        library.show_locations()
    
    if args.formats or args.all:
        library.show_formats()
    
    if args.genres or args.all:
        library.show_genres()
    
    if args.years or args.all:
        library.show_years()
    
    if args.paths or args.all:
        library.find_path_patterns()

if __name__ == "__main__":
    main()