#!/usr/bin/env python3
"""
Script automatisé pour mettre à jour la bibliothèque iTunes
Corrige les chemins Windows vers Linux et autres problèmes courants
"""

import os
import sys
import subprocess
from datetime import datetime

class iTunesUpdater:
    def __init__(self):
        self.script_dir = "/home/paulceline/Documents/Projets/Modif xml itunes"
        self.library_file = "iTunes Music Library.xml"
        self.editor_script = "itunes_editor.py"
        self.original_path = "/mnt/mybook/Musiques/iTunes/iTunes Music Library.xml"
    
    def run_command(self, cmd):
        """Exécute une commande et retourne le résultat"""
        try:
            result = subprocess.run(cmd, shell=True, cwd=self.script_dir, 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Erreur : {result.stderr}")
                return False
            print(result.stdout)
            return True
        except Exception as e:
            print(f"❌ Erreur d'exécution : {e}")
            return False
    
    def update_library_paths(self):
        """Met à jour tous les chemins de la bibliothèque"""
        print("🔄 Mise à jour de la bibliothèque iTunes...")
        print("=" * 50)
        
        # 1. Créer une sauvegarde
        print("1️⃣ Création d'une sauvegarde...")
        cmd = f'python3 {self.editor_script} "{self.library_file}" --backup'
        if not self.run_command(cmd):
            return False
        
        # 2. Corriger les chemins Windows vers Linux
        print("\n2️⃣ Correction des chemins de fichiers...")
        cmd = f'python3 {self.editor_script} "{self.library_file}" --update-paths "file://localhost/E:/Musiques/" "file://localhost/mnt/mybook/Musiques/"'
        if not self.run_command(cmd):
            return False
        
        # 3. Corriger les problèmes d'encodage
        print("\n3️⃣ Correction des problèmes d'encodage...")
        cmd = f'python3 {self.editor_script} "{self.library_file}" --fix-encoding'
        if not self.run_command(cmd):
            return False
        
        # 4. Normaliser les artistes
        print("\n4️⃣ Normalisation des noms d'artistes...")
        cmd = f'python3 {self.editor_script} "{self.library_file}" --normalize-artists'
        if not self.run_command(cmd):
            return False
        
        print("\n✅ Mise à jour terminée!")
        return True
    
    def copy_to_original(self):
        """Copie le fichier modifié vers l'emplacement original"""
        if not os.path.exists(self.original_path):
            print(f"⚠️  Emplacement original non trouvé : {self.original_path}")
            return False
        
        print(f"\n📋 Copie vers l'emplacement original...")
        source = os.path.join(self.script_dir, self.library_file)
        
        # Créer une sauvegarde de l'original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_original = f"{self.original_path}.backup_original_{timestamp}"
        
        try:
            # Sauvegarder l'original
            subprocess.run(f'cp "{self.original_path}" "{backup_original}"', shell=True, check=True)
            print(f"💾 Sauvegarde originale : {backup_original}")
            
            # Copier le fichier modifié
            subprocess.run(f'cp "{source}" "{self.original_path}"', shell=True, check=True)
            print(f"✅ Fichier copié vers {self.original_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de la copie : {e}")
            return False
    
    def show_stats(self):
        """Affiche les statistiques de la bibliothèque"""
        print("\n📊 Statistiques de la bibliothèque mise à jour:")
        cmd = f'python3 itunes_library_manager.py "{self.library_file}" --stats'
        self.run_command(cmd)
    
    def interactive_menu(self):
        """Menu interactif pour l'utilisateur"""
        print("🎵 GESTIONNAIRE DE BIBLIOTHÈQUE ITUNES")
        print("=" * 40)
        print("1. Mettre à jour la bibliothèque (chemins + corrections)")
        print("2. Afficher les statistiques")
        print("3. Copier vers l'emplacement original")
        print("4. Tout faire automatiquement")
        print("0. Quitter")
        
        while True:
            try:
                choice = input("\nVotre choix (0-4): ").strip()
                
                if choice == "0":
                    print("👋 Au revoir!")
                    break
                elif choice == "1":
                    self.update_library_paths()
                elif choice == "2":
                    self.show_stats()
                elif choice == "3":
                    self.copy_to_original()
                elif choice == "4":
                    if self.update_library_paths():
                        response = input("\nCopier vers l'emplacement original? (o/N): ")
                        if response.lower() in ['o', 'oui', 'y', 'yes']:
                            self.copy_to_original()
                        self.show_stats()
                else:
                    print("❌ Choix invalide. Essayez encore.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Arrêt demandé par l'utilisateur.")
                break
            except Exception as e:
                print(f"❌ Erreur : {e}")

def main():
    updater = iTunesUpdater()
    
    # Vérifier que nous sommes dans le bon répertoire
    if not os.path.exists(updater.library_file):
        print(f"❌ Fichier non trouvé : {updater.library_file}")
        print(f"Veuillez exécuter ce script depuis : {updater.script_dir}")
        return 1
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Mode automatique
        print("🤖 Mode automatique activé")
        if updater.update_library_paths():
            updater.copy_to_original()
            updater.show_stats()
    else:
        # Mode interactif
        updater.interactive_menu()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())