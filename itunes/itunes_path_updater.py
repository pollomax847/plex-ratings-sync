#!/usr/bin/env python3
"""
iTunes Path Updater - Mise à jour spécialisée des chemins
Corrige les chemins de fichiers dans votre bibliothèque iTunes
"""

import xml.etree.ElementTree as ET
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
import urllib.parse
import re

class iTunesPathUpdater:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.modifications = 0
        
    def create_backup(self):
        """Crée une sauvegarde du fichier original"""
        backup_file = f"{self.xml_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(self.xml_file, backup_file)
        print(f"💾 Sauvegarde créée : {backup_file}")
        return backup_file
    
    def update_paths_simple(self, old_pattern, new_pattern, dry_run=False):
        """Mise à jour simple des chemins par remplacement de texte"""
        print(f"🔄 Mise à jour des chemins...")
        print(f"   Ancien : {old_pattern}")
        print(f"   Nouveau: {new_pattern}")
        
        if not dry_run:
            # Lire le fichier
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compter les remplacements
            original_content = content
            content = content.replace(old_pattern, new_pattern)
            
            # Calculer le nombre de modifications
            self.modifications = original_content.count(old_pattern)
            
            # Sauvegarder
            with open(self.xml_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Mode simulation - juste compter
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.modifications = content.count(old_pattern)
        
        print(f"✅ {self.modifications} remplacements effectués" + (" (simulation)" if dry_run else ""))
        return self.modifications
    
    def analyze_paths(self):
        """Analyse les chemins existants pour proposer des corrections"""
        print("🔍 Analyse des chemins existants...")
        
        patterns = {
            'file://E:/': 0,
            'file://C:/': 0,
            'file:///mnt/': 0,
            'file://localhost/E:/': 0,
            'E:/Musiques/': 0,
            'C:/Musiques/': 0,
        }
        
        examples = {pattern: [] for pattern in patterns}
        
        try:
            with open(self.xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in patterns:
                count = content.count(pattern)
                patterns[pattern] = count
                
                # Trouver quelques exemples
                if count > 0:
                    lines = content.split('\n')
                    for line in lines:
                        if pattern in line and len(examples[pattern]) < 3:
                            # Extraire juste l'URL
                            match = re.search(r'<string>(file://[^<]+)</string>', line)
                            if match:
                                examples[pattern].append(match.group(1))
        
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse : {e}")
            return None
        
        return patterns, examples
    
    def suggest_updates(self):
        """Propose des mises à jour automatiques"""
        analysis = self.analyze_paths()
        if not analysis:
            return
        
        patterns, examples = analysis
        
        print("\n📊 ANALYSE DES CHEMINS")
        print("-" * 40)
        
        for pattern, count in patterns.items():
            if count > 0:
                print(f"{pattern:25} : {count:6,} occurrences")
                if examples[pattern]:
                    print(f"   Exemple: {examples[pattern][0]}")
        
        print("\n💡 SUGGESTIONS DE CORRECTION")
        print("-" * 40)
        
        # Suggestions basées sur l'analyse
        if patterns['file://E:/'] > 0:
            print(f"✅ Trouvé {patterns['file://E:/']} chemins 'file://E:/'")
            print(f"   → Commande : python3 {sys.argv[0]} --update 'file://E:/' 'file:///mnt/MyBook/'")
        
        if patterns['file://localhost/E:/'] > 0:
            print(f"✅ Trouvé {patterns['file://localhost/E:/']} chemins 'file://localhost/E:/'")
            print(f"   → Commande : python3 {sys.argv[0]} --update 'file://localhost/E:/' 'file:///mnt/MyBook/'")
        
        if patterns['E:/Musiques/'] > 0:
            print(f"✅ Trouvé {patterns['E:/Musiques/']} chemins 'E:/Musiques/'")
            print(f"   → Commande : python3 {sys.argv[0]} --update 'E:/Musiques/' '/mnt/MyBook/Musiques/'")
        
        # Corrections communes
        common_fixes = [
            ("file://E:/Musiques/", "file:///mnt/MyBook/Musiques/"),
            ("file://localhost/E:/Musiques/", "file:///mnt/MyBook/Musiques/"),
            ("E:/Musiques/", "/mnt/MyBook/Musiques/"),
            ("file://C:/Musiques/", "file:///mnt/MyBook/Musiques/"),
        ]
        
        print(f"\n🔧 CORRECTIONS COMMUNES POSSIBLES")
        print("-" * 40)
        for old, new in common_fixes:
            count = patterns.get(old, 0)
            if count == 0:
                # Chercher des variations
                with open(self.xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                count = content.count(old)
            
            if count > 0:
                print(f"📁 {old} → {new}")
                print(f"   Affecterait {count} entrées")
    
    def interactive_update(self):
        """Mode interactif pour les mises à jour"""
        print("\n🔧 MODE INTERACTIF - MISE À JOUR DES CHEMINS")
        print("=" * 50)
        
        # Analyser d'abord
        self.suggest_updates()
        
        print(f"\n" + "=" * 50)
        print("Choisissez une option :")
        print("1. Correction automatique E: → /mnt/MyBook/")
        print("2. Correction personnalisée")
        print("3. Simulation seulement")
        print("0. Annuler")
        
        choice = input("\nVotre choix (0-3): ").strip()
        
        if choice == '0':
            print("👋 Annulé")
            return
        
        elif choice == '1':
            print("\n🚀 Correction automatique...")
            
            # Créer une sauvegarde
            self.create_backup()
            
            # Corrections automatiques
            corrections = [
                ("file://E:/", "file:///mnt/MyBook/"),
                ("file://localhost/E:/", "file:///mnt/MyBook/"),
                ("E:/Musiques/", "/mnt/MyBook/Musiques/"),
            ]
            
            total_changes = 0
            for old, new in corrections:
                changes = self.update_paths_simple(old, new, dry_run=False)
                total_changes += changes
            
            print(f"✅ Correction terminée : {total_changes} modifications au total")
        
        elif choice == '2':
            old_pattern = input("Ancien pattern à remplacer : ").strip()
            new_pattern = input("Nouveau pattern : ").strip()
            
            if old_pattern and new_pattern:
                # Simulation d'abord
                print("\n🔍 Simulation...")
                count = self.update_paths_simple(old_pattern, new_pattern, dry_run=True)
                
                if count > 0:
                    confirm = input(f"\n⚠️  {count} modifications seront effectuées. Continuer ? (o/N): ")
                    if confirm.lower() in ['o', 'oui', 'y', 'yes']:
                        self.create_backup()
                        self.update_paths_simple(old_pattern, new_pattern, dry_run=False)
                        print("✅ Mise à jour terminée")
                    else:
                        print("👋 Annulé")
                else:
                    print("ℹ️  Aucune modification nécessaire")
            else:
                print("❌ Patterns invalides")
        
        elif choice == '3':
            print("\n🔍 MODE SIMULATION")
            old_pattern = input("Pattern à rechercher : ").strip()
            new_pattern = input("Pattern de remplacement : ").strip()
            
            if old_pattern and new_pattern:
                self.update_paths_simple(old_pattern, new_pattern, dry_run=True)
            else:
                print("❌ Patterns invalides")

def main():
    parser = argparse.ArgumentParser(description='Mise à jour des chemins iTunes')
    parser.add_argument('xml_file', nargs='?', default='iTunes Music Library.xml',
                       help='Fichier XML de la bibliothèque iTunes')
    parser.add_argument('--analyze', action='store_true',
                       help='Analyser les chemins existants')
    parser.add_argument('--update', nargs=2, metavar=('OLD', 'NEW'),
                       help='Mettre à jour les chemins (ancien nouveau)')
    parser.add_argument('--auto-fix', action='store_true',
                       help='Correction automatique E: → /mnt/MyBook/')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Mode interactif')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulation (ne modifie pas le fichier)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Ne pas créer de sauvegarde')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.xml_file):
        print(f"❌ Fichier non trouvé : {args.xml_file}")
        sys.exit(1)
    
    updater = iTunesPathUpdater(args.xml_file)
    
    if args.analyze:
        updater.suggest_updates()
    
    elif args.update:
        old_pattern, new_pattern = args.update
        if not args.no_backup and not args.dry_run:
            updater.create_backup()
        updater.update_paths_simple(old_pattern, new_pattern, args.dry_run)
    
    elif args.auto_fix:
        if not args.no_backup and not args.dry_run:
            updater.create_backup()
        
        corrections = [
            ("file://E:/", "file:///mnt/MyBook/"),
            ("file://localhost/E:/", "file:///mnt/MyBook/"),
            ("E:/Musiques/", "/mnt/MyBook/Musiques/"),
        ]
        
        total_changes = 0
        for old, new in corrections:
            changes = updater.update_paths_simple(old, new, args.dry_run)
            total_changes += changes
        
        print(f"✅ Correction automatique : {total_changes} modifications" + (" (simulation)" if args.dry_run else ""))
    
    elif args.interactive:
        updater.interactive_update()
    
    else:
        print("ℹ️  Aucune action spécifiée. Utilisez --help pour voir les options ou --interactive pour le mode interactif.")

if __name__ == "__main__":
    main()