#!/usr/bin/env python3
"""
iTunes Library Complete Manager
Gestionnaire complet pour votre bibliothèque iTunes
"""

import os
import sys
import subprocess
from pathlib import Path

class iTunesCompleteManager:
    def __init__(self):
        self.xml_file = "iTunes Music Library.xml"
        self.tools = {
            'analyzer': 'itunes_analyzer.py',
            'updater': 'itunes_path_updater.py',
            'original_manager': 'itunes_library_manager.py'
        }
    
    def check_files(self):
        """Vérifie la présence des fichiers nécessaires"""
        missing = []
        
        if not os.path.exists(self.xml_file):
            missing.append(f"📁 {self.xml_file} - Bibliothèque iTunes XML")
        
        for tool_name, tool_file in self.tools.items():
            if not os.path.exists(tool_file):
                missing.append(f"🔧 {tool_file} - {tool_name}")
        
        return missing
    
    def run_tool(self, tool, args=[]):
        """Exécute un outil avec les arguments donnés"""
        if tool not in self.tools:
            print(f"❌ Outil inconnu : {tool}")
            return False
        
        tool_file = self.tools[tool]
        if not os.path.exists(tool_file):
            print(f"❌ Fichier manquant : {tool_file}")
            return False
        
        cmd = ['python3', tool_file] + args
        try:
            result = subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'exécution : {e}")
            return False
    
    def copy_from_source(self):
        """Copie la bibliothèque depuis la source"""
        source_path = "/mnt/mybook/Musiques/iTunes/iTunes Music Library.xml"
        
        if os.path.exists(source_path):
            print(f"📥 Copie depuis {source_path}...")
            try:
                import shutil
                shutil.copy2(source_path, self.xml_file)
                print(f"✅ Bibliothèque copiée")
                return True
            except Exception as e:
                print(f"❌ Erreur lors de la copie : {e}")
                return False
        else:
            print(f"❌ Fichier source non trouvé : {source_path}")
            return False
    
    def copy_to_destination(self):
        """Copie la bibliothèque vers la destination"""
        dest_path = "/mnt/mybook/Musiques/iTunes/iTunes Music Library.xml"
        
        if not os.path.exists(self.xml_file):
            print(f"❌ Fichier local non trouvé : {self.xml_file}")
            return False
        
        try:
            import shutil
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(self.xml_file, dest_path)
            print(f"✅ Bibliothèque copiée vers {dest_path}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la copie : {e}")
            return False
    
    def show_menu(self):
        """Affiche le menu principal"""
        print("\n" + "="*60)
        print("🎵 GESTIONNAIRE COMPLET DE BIBLIOTHÈQUE ITUNES")
        print("="*60)
        print("📊 ANALYSE")
        print("  1. Statistiques de base")
        print("  2. Statistiques détaillées")
        print("  3. Analyser les chemins de fichiers")
        print("")
        print("🔧 MODIFICATIONS")
        print("  4. Corriger les chemins (mode interactif)")
        print("  5. Correction automatique E: → /mnt/mybook/")
        print("  6. Gestionnaire avancé (interface complète)")
        print("")
        print("📁 GESTION DES FICHIERS")
        print("  7. Copier depuis la source (/mnt/mybook/Musiques/)")
        print("  8. Copier vers la destination (/mnt/mybook/Musiques/)")
        print("  9. Vérifier les fichiers")
        print("")
        print("📋 WORKFLOWS COMPLETS")
        print("  10. Workflow complet : Analyser → Corriger → Sauvegarder")
        print("  11. Mise à jour rapide depuis la source")
        print("")
        print("0. Quitter")
        print("="*60)
    
    def workflow_complete(self):
        """Workflow complet d'analyse et correction"""
        print("\n🚀 WORKFLOW COMPLET")
        print("="*40)
        
        # 1. Vérifications
        print("1️⃣ Vérification des fichiers...")
        missing = self.check_files()
        if missing:
            print("❌ Fichiers manquants :")
            for item in missing:
                print(f"  {item}")
            
            if self.xml_file + " - Bibliothèque iTunes XML" in [item.split(" - ")[-1] for item in missing]:
                print("\n📥 Tentative de copie depuis la source...")
                if not self.copy_from_source():
                    return False
        
        # 2. Analyse
        print("\n2️⃣ Analyse de la bibliothèque...")
        if not self.run_tool('analyzer', ['--stats']):
            return False
        
        # 3. Analyse des chemins
        print("\n3️⃣ Analyse des chemins...")
        if not self.run_tool('updater', ['--analyze']):
            return False
        
        # 4. Proposition de correction
        print("\n4️⃣ Voulez-vous corriger les chemins automatiquement ?")
        choice = input("Corriger automatiquement ? (o/N): ").strip().lower()
        
        if choice in ['o', 'oui', 'y', 'yes']:
            print("\n🔧 Correction automatique...")
            if not self.run_tool('updater', ['--auto-fix']):
                return False
        
        # 5. Statistiques finales
        print("\n5️⃣ Statistiques après correction...")
        if not self.run_tool('analyzer', ['--stats']):
            return False
        
        # 6. Sauvegarde
        print("\n6️⃣ Voulez-vous sauvegarder vers la destination ?")
        choice = input("Sauvegarder vers /mnt/mybook/Musiques/ ? (o/N): ").strip().lower()
        
        if choice in ['o', 'oui', 'y', 'yes']:
            self.copy_to_destination()
        
        print("\n✅ Workflow terminé !")
        return True
    
    def quick_update(self):
        """Mise à jour rapide depuis la source"""
        print("\n⚡ MISE À JOUR RAPIDE")
        print("="*30)
        
        # 1. Copier depuis la source
        print("1️⃣ Copie depuis la source...")
        if not self.copy_from_source():
            return False
        
        # 2. Correction automatique
        print("\n2️⃣ Correction automatique des chemins...")
        if not self.run_tool('updater', ['--auto-fix']):
            return False
        
        # 3. Statistiques
        print("\n3️⃣ Statistiques...")
        if not self.run_tool('analyzer', ['--stats']):
            return False
        
        print("\n✅ Mise à jour rapide terminée !")
        return True
    
    def main_loop(self):
        """Boucle principale du programme"""
        while True:
            self.show_menu()
            choice = input("\nVotre choix (0-11): ").strip()
            
            if choice == '0':
                print("👋 Au revoir !")
                break
            
            elif choice == '1':
                self.run_tool('analyzer', ['--stats'])
            
            elif choice == '2':
                self.run_tool('analyzer', ['--all'])
            
            elif choice == '3':
                self.run_tool('updater', ['--analyze'])
            
            elif choice == '4':
                self.run_tool('updater', ['--interactive'])
            
            elif choice == '5':
                self.run_tool('updater', ['--auto-fix'])
            
            elif choice == '6':
                self.run_tool('original_manager')
            
            elif choice == '7':
                self.copy_from_source()
            
            elif choice == '8':
                self.copy_to_destination()
            
            elif choice == '9':
                missing = self.check_files()
                if missing:
                    print("❌ Fichiers manquants :")
                    for item in missing:
                        print(f"  {item}")
                else:
                    print("✅ Tous les fichiers sont présents")
            
            elif choice == '10':
                self.workflow_complete()
            
            elif choice == '11':
                self.quick_update()
            
            else:
                print("❌ Choix invalide")
            
            input("\nAppuyez sur Entrée pour continuer...")

def main():
    print("🎵 Gestionnaire Complet de Bibliothèque iTunes")
    print("Conçu pour gérer votre bibliothèque iTunes sur Linux")
    
    manager = iTunesCompleteManager()
    manager.main_loop()

if __name__ == "__main__":
    main()