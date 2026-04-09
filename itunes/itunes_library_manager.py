#!/usr/bin/env python3
"""
Gestionnaire de bibliothèque iTunes - Outil pour modifier la bibliothèque iTunes XML
"""

import xml.etree.ElementTree as ET
import sys
import os
import shutil
from datetime import datetime
import argparse

class iTunesLibraryManager:
    def __init__(self, library_path):
        self.library_path = library_path
        self.backup_path = None
        self.tree = None
        self.root = None
    
    def load_library(self):
        """Charge la bibliothèque iTunes XML"""
        try:
            print(f"Chargement de la bibliothèque : {self.library_path}")
            self.tree = ET.parse(self.library_path)
            self.root = self.tree.getroot()
            print("✓ Bibliothèque chargée avec succès")
            return True
        except ET.ParseError as e:
            print(f"✗ Erreur de parsing XML : {e}")
            return False
        except FileNotFoundError:
            print(f"✗ Fichier non trouvé : {self.library_path}")
            return False
    
    def create_backup(self):
        """Crée une sauvegarde de la bibliothèque"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = f"{self.library_path}.backup_{timestamp}"
        shutil.copy2(self.library_path, self.backup_path)
        print(f"✓ Sauvegarde créée : {self.backup_path}")
    
    def get_library_stats(self):
        """Affiche les statistiques de la bibliothèque"""
        if not self.root:
            print("✗ Bibliothèque non chargée")
            return
        
        # Trouver le dictionnaire principal
        main_dict = None
        for child in self.root:
            if child.tag == 'dict':
                main_dict = child
                break
        
        if not main_dict:
            print("✗ Structure XML invalide")
            return
        
        # Chercher les informations de base
        stats = {}
        current_key = None
        
        for child in main_dict:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag in ['integer', 'string', 'date']:
                if current_key in ['Library Persistent ID', 'Music Folder', 'Major Version', 'Minor Version']:
                    stats[current_key] = child.text
        
        # Compter les pistes
        tracks_dict = None
        for child in main_dict:
            if child.tag == 'dict' and current_key == 'Tracks':
                tracks_dict = child
                break
            elif child.tag == 'key':
                current_key = child.text
        
        track_count = 0
        if tracks_dict:
            track_count = len([child for child in tracks_dict if child.tag == 'dict'])
        
        print("\n=== STATISTIQUES DE LA BIBLIOTHÈQUE ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        print(f"Nombre de pistes: {track_count}")
    
    def find_tracks_by_criteria(self, criteria):
        """Trouve les pistes selon des critères"""
        if not self.root:
            print("✗ Bibliothèque non chargée")
            return []
        
        matching_tracks = []
        
        # Naviguer vers le dictionnaire des pistes
        tracks_dict = self._find_tracks_dict()
        if not tracks_dict:
            return []
        
        # Parcourir chaque piste
        current_track_id = None
        current_track_data = {}
        
        for child in tracks_dict:
            if child.tag == 'key':
                if current_track_id and current_track_data:
                    # Vérifier si la piste correspond aux critères
                    if self._track_matches_criteria(current_track_data, criteria):
                        matching_tracks.append({
                            'id': current_track_id,
                            'data': current_track_data.copy()
                        })
                
                current_track_id = child.text
                current_track_data = {}
            
            elif child.tag == 'dict':
                # Parser les données de la piste
                current_track_data = self._parse_track_dict(child)
        
        # Vérifier la dernière piste
        if current_track_id and current_track_data:
            if self._track_matches_criteria(current_track_data, criteria):
                matching_tracks.append({
                    'id': current_track_id,
                    'data': current_track_data.copy()
                })
        
        return matching_tracks
    
    def _find_tracks_dict(self):
        """Trouve le dictionnaire contenant les pistes"""
        main_dict = None
        for child in self.root:
            if child.tag == 'dict':
                main_dict = child
                break
        
        if not main_dict:
            return None
        
        current_key = None
        for child in main_dict:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'dict' and current_key == 'Tracks':
                return child
        
        return None
    
    def _parse_track_dict(self, track_dict):
        """Parse les données d'une piste"""
        track_data = {}
        current_key = None
        
        for child in track_dict:
            if child.tag == 'key':
                current_key = child.text
            elif current_key and child.tag in ['string', 'integer', 'date', 'true', 'false']:
                if child.tag in ['true', 'false']:
                    track_data[current_key] = child.tag == 'true'
                else:
                    track_data[current_key] = child.text
        
        return track_data
    
    def _track_matches_criteria(self, track_data, criteria):
        """Vérifie si une piste correspond aux critères"""
        for key, value in criteria.items():
            if key not in track_data:
                return False
            
            track_value = track_data[key]
            if isinstance(value, str):
                if value.lower() not in str(track_value).lower():
                    return False
            else:
                if track_value != value:
                    return False
        
        return True
    
    def save_library(self, output_path=None):
        """Sauvegarde la bibliothèque modifiée"""
        if not self.tree:
            print("✗ Aucune bibliothèque à sauvegarder")
            return False
        
        save_path = output_path or self.library_path
        
        try:
            self.tree.write(save_path, encoding='utf-8', xml_declaration=True)
            print(f"✓ Bibliothèque sauvegardée : {save_path}")
            return True
        except Exception as e:
            print(f"✗ Erreur lors de la sauvegarde : {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Gestionnaire de bibliothèque iTunes')
    parser.add_argument('library_path', help='Chemin vers le fichier iTunes Music Library.xml')
    parser.add_argument('--stats', action='store_true', help='Afficher les statistiques')
    parser.add_argument('--search', nargs=2, metavar=('KEY', 'VALUE'), help='Rechercher des pistes')
    parser.add_argument('--backup', action='store_true', help='Créer une sauvegarde')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.library_path):
        print(f"✗ Fichier non trouvé : {args.library_path}")
        return 1
    
    manager = iTunesLibraryManager(args.library_path)
    
    if not manager.load_library():
        return 1
    
    if args.backup:
        manager.create_backup()
    
    if args.stats:
        manager.get_library_stats()
    
    if args.search:
        key, value = args.search
        criteria = {key: value}
        tracks = manager.find_tracks_by_criteria(criteria)
        
        print(f"\n=== RÉSULTATS DE RECHERCHE ({len(tracks)} pistes) ===")
        for track in tracks[:10]:  # Limiter à 10 résultats
            data = track['data']
            name = data.get('Name', 'Sans nom')
            artist = data.get('Artist', 'Artiste inconnu')
            album = data.get('Album', 'Album inconnu')
            print(f"• {name} - {artist} ({album})")
        
        if len(tracks) > 10:
            print(f"... et {len(tracks) - 10} autres pistes")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())