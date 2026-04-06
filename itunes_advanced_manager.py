#!/usr/bin/env python3
"""
iTunes XML Library Advanced Manager
Gestionnaire avancé pour les bibliothèques iTunes XML
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

class iTunesLibraryAdvanced:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.tree = None
        self.root = None
        self.tracks = {}
        self.playlists = {}
        self.stats = {}
        
    def load_library(self):
        """Charge la bibliothèque iTunes"""
        print(f"📚 Chargement de {self.xml_file}...")
        try:
            self.tree = ET.parse(self.xml_file)
            self.root = self.tree.getroot()
            self._parse_tracks()
            self._parse_playlists()
            self._calculate_stats()
            print(f"✅ Bibliothèque chargée : {len(self.tracks)} pistes, {len(self.playlists)} playlists")
            return True
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            return False
    
    def _parse_tracks(self):
        """Parse les pistes de la bibliothèque"""
        tracks_dict = self.root.find('.//key[text()="Tracks"]/../dict')
        if tracks_dict is None:
            return
        
        current_track = {}
        current_key = None
        
        for element in tracks_dict:
            if element.tag == 'key':
                if current_track and current_key:
                    track_id = current_key
                    self.tracks[track_id] = current_track
                current_track = {}
                current_key = element.text
            elif element.tag == 'dict':
                # Parse track details
                track_data = {}
                keys = element.findall('key')
                values = element.findall('*[position() mod 2 = 0]')
                
                for i, key in enumerate(keys):
                    if i < len(values):
                        value = values[i]
                        if value.tag == 'string':
                            track_data[key.text] = value.text
                        elif value.tag == 'integer':
                            track_data[key.text] = int(value.text) if value.text else 0
                        elif value.tag == 'date':
                            track_data[key.text] = value.text
                        elif value.tag == 'true':
                            track_data[key.text] = True
                        elif value.tag == 'false':
                            track_data[key.text] = False
                
                current_track = track_data
    
    def _parse_playlists(self):
        """Parse les playlists"""
        playlists_array = self.root.find('.//key[text()="Playlists"]/../array')
        if playlists_array is None:
            return
        
        for playlist_dict in playlists_array.findall('dict'):
            playlist_data = {}
            keys = playlist_dict.findall('key')
            values = playlist_dict.findall('*[position() mod 2 = 0]')
            
            for i, key in enumerate(keys):
                if i < len(values):
                    value = values[i]
                    if value.tag == 'string':
                        playlist_data[key.text] = value.text
                    elif value.tag == 'integer':
                        playlist_data[key.text] = int(value.text) if value.text else 0
                    elif value.tag == 'array':
                        # Track IDs dans la playlist
                        track_ids = []
                        for track_dict in value.findall('dict'):
                            track_id_elem = track_dict.find('key[text()="Track ID"]/../integer')
                            if track_id_elem is not None:
                                track_ids.append(track_id_elem.text)
                        playlist_data['Track IDs'] = track_ids
            
            if 'Name' in playlist_data:
                self.playlists[playlist_data['Name']] = playlist_data
    
    def _calculate_stats(self):
        """Calcule les statistiques de la bibliothèque"""
        self.stats = {
            'total_tracks': len(self.tracks),
            'total_playlists': len(self.playlists),
            'file_formats': defaultdict(int),
            'missing_files': 0,
            'duplicate_files': 0,
            'total_size': 0,
            'total_time': 0,
            'artists': set(),
            'albums': set(),
            'years': defaultdict(int),
            'genres': defaultdict(int)
        }
        
        file_locations = defaultdict(int)
        
        for track_id, track in self.tracks.items():
            # Format de fichier
            if 'Kind' in track:
                kind = track['Kind']
                if 'audio file' in kind.lower():
                    format_match = re.search(r'(\w+) audio file', kind)
                    if format_match:
                        self.stats['file_formats'][format_match.group(1)] += 1
            
            # Fichiers manquants
            if 'Location' in track:
                location = track['Location']
                if location.startswith('file://'):
                    file_path = location.replace('file://', '').replace('%20', ' ')
                    if not os.path.exists(file_path):
                        self.stats['missing_files'] += 1
                file_locations[location] += 1
            else:
                self.stats['missing_files'] += 1
            
            # Taille totale
            if 'Size' in track:
                self.stats['total_size'] += track['Size']
            
            # Durée totale
            if 'Total Time' in track:
                self.stats['total_time'] += track['Total Time']
            
            # Artistes et albums
            if 'Artist' in track:
                self.stats['artists'].add(track['Artist'])
            if 'Album' in track:
                self.stats['albums'].add(track['Album'])
            
            # Années
            if 'Year' in track:
                self.stats['years'][track['Year']] += 1
            
            # Genres
            if 'Genre' in track:
                self.stats['genres'][track['Genre']] += 1
        
        # Doublons
        self.stats['duplicate_files'] = sum(1 for count in file_locations.values() if count > 1)
        
        # Conversion en entiers pour les sets
        self.stats['total_artists'] = len(self.stats['artists'])
        self.stats['total_albums'] = len(self.stats['albums'])
    
    def update_file_paths(self, old_path, new_path, dry_run=False):
        """Met à jour les chemins de fichiers"""
        updated_count = 0
        
        print(f"🔄 Mise à jour des chemins : {old_path} → {new_path}")
        
        for track_id, track in self.tracks.items():
            if 'Location' in track:
                location = track['Location']
                if old_path in location:
                    new_location = location.replace(old_path, new_path)
                    if not dry_run:
                        track['Location'] = new_location
                    updated_count += 1
                    if updated_count <= 5:  # Afficher les 5 premiers exemples
                        print(f"  📁 {location} → {new_location}")
        
        if updated_count > 5:
            print(f"  ... et {updated_count - 5} autres")
        
        print(f"✅ {updated_count} pistes mises à jour" + (" (simulation)" if dry_run else ""))
        return updated_count
    
    def fix_missing_metadata(self, dry_run=False):
        """Corrige les métadonnées manquantes"""
        fixes = {
            'missing_artist': 0,
            'missing_album': 0,
            'missing_genre': 0,
            'invalid_year': 0
        }
        
        for track_id, track in self.tracks.items():
            # Artiste manquant
            if 'Artist' not in track or not track['Artist']:
                if not dry_run:
                    track['Artist'] = 'Artiste Inconnu'
                fixes['missing_artist'] += 1
            
            # Album manquant
            if 'Album' not in track or not track['Album']:
                if not dry_run:
                    track['Album'] = 'Album Inconnu'
                fixes['missing_album'] += 1
            
            # Genre manquant
            if 'Genre' not in track or not track['Genre']:
                if not dry_run:
                    track['Genre'] = 'Non classé'
                fixes['missing_genre'] += 1
            
            # Année invalide
            if 'Year' in track:
                year = track['Year']
                if year < 1900 or year > datetime.now().year:
                    if not dry_run:
                        del track['Year']
                    fixes['invalid_year'] += 1
        
        for fix_type, count in fixes.items():
            if count > 0:
                print(f"🔧 {fix_type.replace('_', ' ').title()}: {count} corrections" + (" (simulation)" if dry_run else ""))
        
        return fixes
    
    def remove_missing_files(self, dry_run=False):
        """Supprime les références aux fichiers manquants"""
        removed_count = 0
        tracks_to_remove = []
        
        for track_id, track in self.tracks.items():
            if 'Location' in track:
                location = track['Location']
                if location.startswith('file://'):
                    file_path = location.replace('file://', '').replace('%20', ' ')
                    if not os.path.exists(file_path):
                        tracks_to_remove.append(track_id)
                        removed_count += 1
                        if removed_count <= 5:
                            print(f"  ❌ Fichier manquant : {file_path}")
            else:
                tracks_to_remove.append(track_id)
                removed_count += 1
        
        if not dry_run:
            for track_id in tracks_to_remove:
                del self.tracks[track_id]
        
        if removed_count > 5:
            print(f"  ... et {removed_count - 5} autres")
        
        print(f"🗑️  {removed_count} pistes supprimées" + (" (simulation)" if dry_run else ""))
        return removed_count
    
    def save_library(self, output_file=None):
        """Sauvegarde la bibliothèque modifiée"""
        if output_file is None:
            output_file = self.xml_file
        
        print(f"💾 Sauvegarde vers {output_file}...")
        
        # Reconstruction du XML
        self._rebuild_xml()
        
        try:
            self.tree.write(output_file, encoding='utf-8', xml_declaration=True)
            print(f"✅ Bibliothèque sauvegardée")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {e}")
            return False
    
    def _rebuild_xml(self):
        """Reconstruit le XML à partir des données en mémoire"""
        # Cette méthode est complexe car elle doit reconstruire
        # tout le XML iTunes. Pour simplifier, on modifie directement
        # les éléments existants.
        
        tracks_dict = self.root.find('.//key[text()="Tracks"]/../dict')
        if tracks_dict is not None:
            # Nettoyer les anciennes données
            tracks_dict.clear()
            
            # Reconstruire avec les nouvelles données
            for track_id, track_data in self.tracks.items():
                # Ajouter la clé de l'ID
                key_elem = ET.SubElement(tracks_dict, 'key')
                key_elem.text = track_id
                
                # Ajouter le dictionnaire de la piste
                track_dict = ET.SubElement(tracks_dict, 'dict')
                
                for key, value in track_data.items():
                    key_elem = ET.SubElement(track_dict, 'key')
                    key_elem.text = key
                    
                    if isinstance(value, str):
                        val_elem = ET.SubElement(track_dict, 'string')
                        val_elem.text = value
                    elif isinstance(value, int):
                        val_elem = ET.SubElement(track_dict, 'integer')
                        val_elem.text = str(value)
                    elif isinstance(value, bool):
                        val_elem = ET.SubElement(track_dict, 'true' if value else 'false')
    
    def show_detailed_stats(self):
        """Affiche des statistiques détaillées"""
        print("\n" + "="*60)
        print("📊 STATISTIQUES DÉTAILLÉES DE LA BIBLIOTHÈQUE")
        print("="*60)
        
        # Statistiques générales
        print(f"🎵 Pistes totales      : {self.stats['total_tracks']:,}")
        print(f"📁 Playlists          : {self.stats['total_playlists']:,}")
        print(f"🎤 Artistes uniques   : {self.stats['total_artists']:,}")
        print(f"💿 Albums uniques     : {self.stats['total_albums']:,}")
        print(f"❌ Fichiers manquants : {self.stats['missing_files']:,}")
        print(f"🔄 Fichiers dupliqués : {self.stats['duplicate_files']:,}")
        
        # Taille et durée
        total_gb = self.stats['total_size'] / (1024**3)
        total_hours = self.stats['total_time'] / (1000 * 3600)
        print(f"💾 Taille totale      : {total_gb:.2f} GB")
        print(f"⏰ Durée totale       : {total_hours:.1f} heures")
        
        # Top formats
        print(f"\n🎵 TOP FORMATS DE FICHIERS")
        print("-" * 30)
        for format_name, count in sorted(self.stats['file_formats'].items(), 
                                       key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{format_name:15} : {count:6,} ({percentage:5.1f}%)")
        
        # Top genres
        print(f"\n🎭 TOP GENRES")
        print("-" * 30)
        for genre, count in sorted(self.stats['genres'].items(), 
                                 key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / self.stats['total_tracks']) * 100
            print(f"{genre[:20]:20} : {count:6,} ({percentage:5.1f}%)")
        
        # Distribution par années
        print(f"\n📅 DISTRIBUTION PAR ANNÉES (Top 10)")
        print("-" * 35)
        for year, count in sorted(self.stats['years'].items(), 
                                key=lambda x: x[1], reverse=True)[:10]:
            if year and year > 0:
                percentage = (count / self.stats['total_tracks']) * 100
                print(f"{year:4} : {count:6,} ({percentage:5.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Gestionnaire avancé de bibliothèque iTunes XML')
    parser.add_argument('xml_file', nargs='?', default='iTunes Music Library.xml',
                       help='Fichier XML de la bibliothèque iTunes')
    parser.add_argument('--update-paths', nargs=2, metavar=('OLD', 'NEW'),
                       help='Mettre à jour les chemins de fichiers')
    parser.add_argument('--fix-metadata', action='store_true',
                       help='Corriger les métadonnées manquantes')
    parser.add_argument('--remove-missing', action='store_true',
                       help='Supprimer les références aux fichiers manquants')
    parser.add_argument('--stats', action='store_true',
                       help='Afficher les statistiques détaillées')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulation (ne modifie pas le fichier)')
    parser.add_argument('--output', '-o', metavar='FILE',
                       help='Fichier de sortie (par défaut : remplace l\'original)')
    parser.add_argument('--backup', action='store_true', default=True,
                       help='Créer une sauvegarde avant modification')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.xml_file):
        print(f"❌ Fichier non trouvé : {args.xml_file}")
        sys.exit(1)
    
    # Créer une sauvegarde
    if args.backup and not args.dry_run:
        backup_file = f"{args.xml_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(args.xml_file, backup_file)
        print(f"💾 Sauvegarde créée : {backup_file}")
    
    # Charger la bibliothèque
    library = iTunesLibraryAdvanced(args.xml_file)
    if not library.load_library():
        sys.exit(1)
    
    # Actions demandées
    modified = False
    
    if args.stats:
        library.show_detailed_stats()
    
    if args.update_paths:
        old_path, new_path = args.update_paths
        count = library.update_file_paths(old_path, new_path, args.dry_run)
        if count > 0:
            modified = True
    
    if args.fix_metadata:
        fixes = library.fix_missing_metadata(args.dry_run)
        if any(fixes.values()):
            modified = True
    
    if args.remove_missing:
        count = library.remove_missing_files(args.dry_run)
        if count > 0:
            modified = True
    
    # Sauvegarder si modifié
    if modified and not args.dry_run:
        output_file = args.output or args.xml_file
        library.save_library(output_file)
    elif args.dry_run and modified:
        print("\n🔍 Mode simulation activé - aucune modification sauvegardée")
    
    if not any([args.update_paths, args.fix_metadata, args.remove_missing, args.stats]):
        print("ℹ️  Aucune action spécifiée. Utilisez --help pour voir les options.")

if __name__ == "__main__":
    main()