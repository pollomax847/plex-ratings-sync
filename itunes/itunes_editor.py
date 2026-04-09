#!/usr/bin/env python3
"""
Outil de modification de bibliothèque iTunes
Permet de faire des modifications en lot sur la bibliothèque iTunes
"""

import xml.etree.ElementTree as ET
import os
import sys
import shutil
from datetime import datetime
import argparse
import re

class iTunesEditor:
    def __init__(self, library_path):
        self.library_path = library_path
        self.tree = None
        self.root = None
        self.tracks_dict = None
        self.modifications_count = 0
    
    def load_library(self):
        """Charge la bibliothèque iTunes"""
        try:
            print(f"📚 Chargement de {self.library_path}...")
            self.tree = ET.parse(self.library_path)
            self.root = self.tree.getroot()
            self._find_tracks_dict()
            print(f"✅ Bibliothèque chargée avec succès ({self._count_tracks()} pistes)")
            return True
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return False
    
    def _find_tracks_dict(self):
        """Trouve le dictionnaire des pistes"""
        if self.root is None:
            return
        
        main_dict = self.root.find('dict')
        if main_dict is None:
            return
        
        current_key = None
        
        for child in main_dict:
            if child.tag == 'key':
                current_key = child.text
            elif child.tag == 'dict' and current_key == 'Tracks':
                self.tracks_dict = child
                break
    
    def _count_tracks(self):
        """Compte le nombre de pistes"""
        if self.tracks_dict is None:
            return 0
        return len([child for child in self.tracks_dict if child.tag == 'dict'])
    
    def create_backup(self):
        """Crée une sauvegarde"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.library_path}.backup_{timestamp}"
        shutil.copy2(self.library_path, backup_path)
        print(f"💾 Sauvegarde créée : {backup_path}")
        return backup_path
    
    def search_and_replace_in_field(self, field_name, search_pattern, replacement, use_regex=False):
        """Recherche et remplace dans un champ spécifique"""
        print(f"🔍 Recherche dans le champ '{field_name}' : '{search_pattern}' -> '{replacement}'")
        
        if self.tracks_dict is None:
            print("❌ Dictionnaire des pistes non trouvé")
            return 0
        
        modifications = 0
        current_track_dict = None
        
        for child in self.tracks_dict:
            if child.tag == 'dict':
                current_track_dict = child
                modifications += self._modify_track_field(current_track_dict, field_name, search_pattern, replacement, use_regex)
        
        self.modifications_count += modifications
        print(f"✅ {modifications} modifications effectuées dans '{field_name}'")
        return modifications
    
    def _modify_track_field(self, track_dict, field_name, search_pattern, replacement, use_regex):
        """Modifie un champ dans une piste"""
        current_key = None
        modifications = 0
        
        for child in track_dict:
            if child.tag == 'key':
                current_key = child.text
            elif current_key == field_name and child.tag == 'string':
                old_value = child.text or ""
                
                if use_regex:
                    new_value = re.sub(search_pattern, replacement, old_value)
                else:
                    new_value = old_value.replace(search_pattern, replacement)
                
                if new_value != old_value:
                    child.text = new_value
                    modifications += 1
        
        return modifications
    
    def update_file_paths(self, old_path, new_path):
        """Met à jour les chemins de fichiers"""
        return self.search_and_replace_in_field('Location', old_path, new_path)
    
    def fix_encoding_issues(self):
        """Corrige les problèmes d'encodage courants"""
        fixes = [
            ('Ã¡', 'á'),  # á mal encodé
            ('Ã©', 'é'),  # é mal encodé
            ('Ã«', 'ë'),  # ë mal encodé
            ('Ã¨', 'è'),  # è mal encodé
            ('Ã ', 'à'),  # à mal encodé
            ('Ã§', 'ç'),  # ç mal encodé
            ('Ã´', 'ô'),  # ô mal encodé
            ('Ãª', 'ê'),  # ê mal encodé
            ('Ã®', 'î'),  # î mal encodé
            ('Ã¯', 'ï'),  # ï mal encodé
            ('Ã¼', 'ü'),  # ü mal encodé
            ('Ã¶', 'ö'),  # ö mal encodé
        ]
        
        total_fixes = 0
        for old, new in fixes:
            for field in ['Name', 'Artist', 'Album', 'Album Artist', 'Genre']:
                total_fixes += self.search_and_replace_in_field(field, old, new)
        
        print(f"🔧 {total_fixes} corrections d'encodage effectuées")
        return total_fixes
    
    def normalize_artist_names(self):
        """Normalise les noms d'artistes (supprime espaces multiples, etc.)"""
        modifications = 0
        
        # Supprimer les espaces multiples
        modifications += self.search_and_replace_in_field('Artist', r'\s+', ' ', use_regex=True)
        modifications += self.search_and_replace_in_field('Album Artist', r'\s+', ' ', use_regex=True)
        
        # Supprimer les espaces en début/fin (plus complexe, nécessite une approche différente)
        modifications += self._trim_field_spaces('Artist')
        modifications += self._trim_field_spaces('Album Artist')
        
        print(f"📝 {modifications} normalisations d'artistes effectuées")
        return modifications
    
    def _trim_field_spaces(self, field_name):
        """Supprime les espaces en début et fin de champ"""
        if self.tracks_dict is None:
            return 0
        
        modifications = 0
        
        for track_dict in self.tracks_dict.findall('dict'):
            current_key = None
            
            for child in track_dict:
                if child.tag == 'key':
                    current_key = child.text
                elif current_key == field_name and child.tag == 'string':
                    old_value = child.text or ""
                    new_value = old_value.strip()
                    
                    if new_value != old_value:
                        child.text = new_value
                        modifications += 1
        
        return modifications
    
    def save_library(self, output_path=None):
        """Sauvegarde la bibliothèque"""
        if self.tree is None:
            print("❌ Aucune bibliothèque à sauvegarder")
            return False
            
        if output_path is None:
            output_path = self.library_path
        
        try:
            # Configurer l'indentation pour un XML lisible
            ET.indent(self.tree, space="  ", level=0)
            self.tree.write(output_path, encoding='utf-8', xml_declaration=True)
            print(f"💾 Bibliothèque sauvegardée : {output_path}")
            print(f"📊 Total des modifications : {self.modifications_count}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {e}")
            return False
    
    def preview_changes(self, field_name, search_pattern, max_results=10):
        """Prévisualise les changements sans les appliquer"""
        print(f"👀 Prévisualisation des changements dans '{field_name}' avec '{search_pattern}':")
        
        if self.tracks_dict is None:
            return
        
        count = 0
        for track_dict in self.tracks_dict.findall('dict'):
            if count >= max_results:
                break
                
            current_key = None
            track_info = {}
            
            # Collecter les infos de la piste
            for child in track_dict:
                if child.tag == 'key':
                    current_key = child.text
                elif current_key in ['Name', 'Artist', 'Album', field_name] and child.tag == 'string':
                    track_info[current_key] = child.text or ""
            
            # Vérifier si le champ contient le pattern
            if field_name in track_info and search_pattern in track_info[field_name]:
                name = track_info.get('Name', 'Sans nom')
                artist = track_info.get('Artist', 'Artiste inconnu')
                current_value = track_info[field_name]
                print(f"  • {name} - {artist}")
                print(f"    {field_name}: '{current_value}'")
                count += 1
        
        if count == 0:
            print("  Aucune correspondance trouvée")
        elif count >= max_results:
            print(f"  ... (affichage limité à {max_results} résultats)")

def main():
    parser = argparse.ArgumentParser(description='Éditeur de bibliothèque iTunes')
    parser.add_argument('library_path', help='Chemin vers iTunes Music Library.xml')
    parser.add_argument('--backup', action='store_true', help='Créer une sauvegarde avant modification')
    parser.add_argument('--preview', action='store_true', help='Prévisualiser les changements sans les appliquer')
    parser.add_argument('--output', help='Fichier de sortie (par défaut: remplace l\'original)')
    
    # Actions
    parser.add_argument('--replace', nargs=3, metavar=('FIELD', 'SEARCH', 'REPLACE'), 
                       help='Remplacer du texte dans un champ')
    parser.add_argument('--regex-replace', nargs=3, metavar=('FIELD', 'PATTERN', 'REPLACE'), 
                       help='Remplacer avec regex dans un champ')
    parser.add_argument('--fix-encoding', action='store_true', help='Corriger les problèmes d\'encodage')
    parser.add_argument('--normalize-artists', action='store_true', help='Normaliser les noms d\'artistes')
    parser.add_argument('--update-paths', nargs=2, metavar=('OLD_PATH', 'NEW_PATH'), 
                       help='Mettre à jour les chemins de fichiers')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.library_path):
        print(f"❌ Fichier non trouvé : {args.library_path}")
        return 1
    
    editor = iTunesEditor(args.library_path)
    
    if not editor.load_library():
        return 1
    
    if args.backup:
        editor.create_backup()
    
    # Actions de prévisualisation
    if args.preview:
        if args.replace:
            editor.preview_changes(args.replace[0], args.replace[1])
        return 0
    
    # Actions de modification
    modifications_made = False
    
    if args.replace:
        field, search, replace = args.replace
        editor.search_and_replace_in_field(field, search, replace)
        modifications_made = True
    
    if args.regex_replace:
        field, pattern, replace = args.regex_replace
        editor.search_and_replace_in_field(field, pattern, replace, use_regex=True)
        modifications_made = True
    
    if args.fix_encoding:
        editor.fix_encoding_issues()
        modifications_made = True
    
    if args.normalize_artists:
        editor.normalize_artist_names()
        modifications_made = True
    
    if args.update_paths:
        old_path, new_path = args.update_paths
        editor.update_file_paths(old_path, new_path)
        modifications_made = True
    
    if modifications_made:
        editor.save_library(args.output)
        
        # Copier vers l'emplacement original si demandé
        if args.output is None:
            original_path = "/mnt/mybook/Musiques/iTunes/iTunes Music Library.xml"
            if os.path.exists(original_path):
                response = input(f"Voulez-vous copier le fichier modifié vers {original_path} ? (o/N): ")
                if response.lower() in ['o', 'oui', 'y', 'yes']:
                    shutil.copy2(args.library_path, original_path)
                    print(f"✅ Fichier copié vers {original_path}")
    else:
        print("ℹ️  Aucune modification spécifiée. Utilisez --help pour voir les options.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())