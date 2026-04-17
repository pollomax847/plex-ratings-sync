#!/usr/bin/env python3
"""
iTunes Alternatives Installer - Solutions légales pour Linux
"""

import subprocess
import os
import sys
import json
from pathlib import Path

class AlternativesInstaller:
    def __init__(self):
        self.alternatives = {
            'cider': {
                'name': 'Cider - Client Apple Music natif',
                'type': 'appimage',
                'url': 'https://github.com/ciderapp/Cider/releases',
                'description': 'Client Apple Music moderne avec interface native',
                'requires_subscription': True
            },
            'apple_music_web': {
                'name': 'Apple Music Web',
                'type': 'webapp',
                'url': 'https://music.apple.com',
                'description': 'Version web officielle d\'Apple Music',
                'requires_subscription': True
            },
            'strawberry': {
                'name': 'Strawberry Music Player',
                'type': 'package',
                'install_cmd': 'sudo apt install strawberry',
                'description': 'Lecteur audio qui peut lire les bibliothèques iTunes',
                'requires_subscription': False
            },
            'clementine': {
                'name': 'Clementine Music Player',
                'type': 'package',
                'install_cmd': 'sudo apt install clementine',
                'description': 'Fork d\'Amarok, supporte les formats iTunes',
                'requires_subscription': False
            }
        }
    
    def check_system_requirements(self):
        """Vérifie les prérequis système"""
        print("🔍 Vérification des prérequis système...")
        
        requirements = {
            'python3': 'python3 --version',
            'curl': 'curl --version',
            'wget': 'wget --version',
            'flatpak': 'flatpak --version'
        }
        
        available = {}
        for tool, cmd in requirements.items():
            try:
                result = subprocess.run(cmd.split(), 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                available[tool] = result.returncode == 0
            except:
                available[tool] = False
        
        return available
    
    def install_cider(self):
        """Installe Cider via Flatpak ou AppImage"""
        print("🍎 Installation de Cider...")
        
        # Tentative via Flatpak (plus simple)
        try:
            print("Tentative d'installation via Flatpak...")
            subprocess.run([
                'flatpak', 'install', 'flathub', 
                'sh.cider.Cider', '-y'
            ], check=True)
            print("✅ Cider installé via Flatpak")
            return True
        except:
            print("⚠️  Flatpak échoué, tentative avec AppImage...")
        
        # Instructions pour AppImage
        print("""
📦 Pour installer Cider manuellement :

1. Téléchargez la dernière version depuis :
   https://github.com/ciderapp/Cider/releases

2. Téléchargez le fichier .AppImage

3. Rendez-le exécutable :
   chmod +x Cider-*.AppImage

4. Lancez-le :
   ./Cider-*.AppImage
""")
        return False
    
    def install_local_players(self):
        """Installe des lecteurs audio locaux"""
        players = ['strawberry', 'clementine', 'audacious']
        
        for player in players:
            try:
                print(f"📻 Installation de {player}...")
                subprocess.run([
                    'sudo', 'apt', 'update'
                ], check=True, capture_output=True)
                
                subprocess.run([
                    'sudo', 'apt', 'install', '-y', player
                ], check=True)
                
                print(f"✅ {player} installé avec succès")
            except subprocess.CalledProcessError:
                print(f"❌ Échec de l'installation de {player}")
    
    def setup_browser_shortcuts(self):
        """Crée des raccourcis pour les services web"""
        shortcuts = {
            'Apple Music': 'https://music.apple.com',
            'YouTube Music': 'https://music.youtube.com',
            'Spotify Web': 'https://open.spotify.com'
        }
        
        desktop_dir = Path.home() / 'Desktop'
        applications_dir = Path.home() / '.local/share/applications'
        applications_dir.mkdir(parents=True, exist_ok=True)
        
        for name, url in shortcuts.items():
            desktop_file = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment=Accès à {name}
Exec=xdg-open {url}
Icon=multimedia-audio-player
Categories=AudioVideo;Audio;Player;
"""
            
            # Fichier .desktop
            desktop_path = applications_dir / f"{name.lower().replace(' ', '-')}.desktop"
            with open(desktop_path, 'w') as f:
                f.write(desktop_file)
            
            os.chmod(desktop_path, 0o755)
            print(f"✅ Raccourci créé pour {name}")
    
    def create_itunes_sync_guide(self):
        """Crée un guide de synchronisation iTunes"""
        guide = """# 🔄 Guide de synchronisation iTunes sur Linux

## Méthode 1 : VirtualBox + Windows + iTunes

### Installation
1. Installez VirtualBox :
   ```bash
   sudo apt install virtualbox virtualbox-ext-pack
   ```

2. Créez une VM Windows 10/11

3. Installez iTunes dans la VM

4. Configurez le partage de dossiers pour accéder à `/mnt/MyBook/Musiques/`

### Synchronisation
1. Démarrez la VM
2. Ouvrez iTunes
3. Importez la bibliothèque depuis le dossier partagé
4. Synchronisez avec iTunes Match/Apple Music

## Méthode 2 : Wine + iTunes (limité)

### Installation
```bash
sudo apt install wine winetricks
winetricks corefonts vcrun2019
```

⚠️ **Note** : iTunes fonctionne mal sous Wine, non recommandé.

## Méthode 3 : Dual Boot Windows

Si vous avez besoin d'un accès régulier à iTunes, considérez un dual boot.

## Méthode 4 : Serveur iTunes distant

Configurez iTunes sur un autre ordinateur et accédez via partage réseau.

## Scripts de synchronisation

Utilisez nos scripts Python pour :
- Mettre à jour les chemins de fichiers
- Corriger les métadonnées
- Exporter vers d'autres formats
"""
        
        with open('itunes_sync_guide.md', 'w', encoding='utf-8') as f:
            f.write(guide)
        
        print("📖 Guide de synchronisation créé : itunes_sync_guide.md")
    
    def main_menu(self):
        """Menu principal"""
        while True:
            print("\n" + "="*50)
            print("🎵 INSTALLATEUR D'ALTERNATIVES ITUNES")
            print("="*50)
            print("1. Installer Cider (Apple Music client)")
            print("2. Installer lecteurs audio locaux")
            print("3. Créer raccourcis services web")
            print("4. Créer guide de synchronisation")
            print("5. Vérifier prérequis système")
            print("6. Tout installer")
            print("0. Quitter")
            
            choice = input("\nVotre choix (0-6): ").strip()
            
            if choice == '0':
                print("👋 Au revoir !")
                break
            elif choice == '1':
                self.install_cider()
            elif choice == '2':
                self.install_local_players()
            elif choice == '3':
                self.setup_browser_shortcuts()
            elif choice == '4':
                self.create_itunes_sync_guide()
            elif choice == '5':
                reqs = self.check_system_requirements()
                for tool, available in reqs.items():
                    status = "✅" if available else "❌"
                    print(f"{status} {tool}")
            elif choice == '6':
                print("🚀 Installation complète...")
                self.check_system_requirements()
                self.install_cider()
                self.install_local_players()
                self.setup_browser_shortcuts()
                self.create_itunes_sync_guide()
                print("✅ Installation terminée !")
            else:
                print("❌ Choix invalide")

if __name__ == "__main__":
    installer = AlternativesInstaller()
    installer.main_menu()