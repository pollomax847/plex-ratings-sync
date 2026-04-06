#!/usr/bin/env python3
"""
iTunes Path Fixer - Correction spécifique pour votre cas
Supprime le '/Music/' des chemins iTunes
"""

import os
import shutil
from datetime import datetime
import urllib.parse

def fix_music_paths(xml_file, dry_run=False):
    """Corrige les chemins en supprimant /Music/ superflu"""
    
    print("🔧 CORRECTION DES CHEMINS ITUNES")
    print("="*50)
    
    # Pattern à corriger
    old_pattern = "/mnt/mybook/Musiques/Music/"
    new_pattern = "/mnt/mybook/Musiques/"
    
    print(f"Correction à effectuer :")
    print(f"  Ancien: ...{old_pattern}...")
    print(f"  Nouveau: ...{new_pattern}...")
    
    if not dry_run:
        # Créer une sauvegarde
        backup_file = f"{xml_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(xml_file, backup_file)
        print(f"💾 Sauvegarde créée: {backup_file}")
    
    # Lire et modifier le fichier
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compter les occurrences
        original_count = content.count(old_pattern)
        print(f"📊 Trouvé {original_count} occurrences à corriger")
        
        if original_count == 0:
            print("ℹ️  Aucune correction nécessaire")
            return 0
        
        # Effectuer le remplacement
        if not dry_run:
            new_content = content.replace(old_pattern, new_pattern)
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ {original_count} chemins corrigés")
        else:
            print(f"🔍 Mode simulation: {original_count} chemins seraient corrigés")
        
        return original_count
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 0

def verify_fixes(xml_file, sample_size=10):
    """Vérifie que les corrections fonctionnent"""
    
    print(f"\n🔍 VÉRIFICATION DES CORRECTIONS")
    print("="*40)
    
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Chercher des exemples de chemins
        import re
        pattern = r'<string>(file://localhost/mnt/mybook/Musiques/[^<]+)</string>'
        matches = re.findall(pattern, content)
        
        if not matches:
            print("❌ Aucun chemin trouvé")
            return
        
        print(f"📊 Trouvé {len(matches)} chemins corrigés")
        
        # Vérifier quelques exemples
        verified = 0
        for i, url in enumerate(matches[:sample_size]):
            decoded = urllib.parse.unquote(url)
            file_path = decoded.replace('file://localhost', '')
            
            exists = os.path.exists(file_path)
            if exists:
                verified += 1
            
            status = "✅" if exists else "❌"
            print(f"{status} {file_path[:80]}{'...' if len(file_path) > 80 else ''}")
        
        success_rate = (verified / min(sample_size, len(matches))) * 100
        print(f"\n📈 Taux de succès: {verified}/{min(sample_size, len(matches))} ({success_rate:.1f}%)")
        
        if success_rate > 50:
            print("✅ Correction réussie !")
        else:
            print("⚠️  Correction partielle - vérifiez les chemins")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

def main():
    xml_file = "iTunes Music Library.xml"
    
    if not os.path.exists(xml_file):
        print(f"❌ Fichier non trouvé: {xml_file}")
        return
    
    print("🎵 CORRECTEUR DE CHEMINS ITUNES SPÉCIALISÉ")
    print("="*50)
    print("Ce script corrige le problème spécifique détecté:")
    print("- Vos fichiers sont dans /mnt/mybook/Musiques/")
    print("- Mais iTunes cherche dans /mnt/mybook/Musiques/Music/")
    print("- Solution: supprimer le '/Music/' superflu")
    
    # Demander confirmation
    choice = input(f"\n🔧 Effectuer la correction ? (o/N): ").strip().lower()
    
    if choice in ['o', 'oui', 'y', 'yes']:
        print(f"\n1️⃣ Correction en cours...")
        count = fix_music_paths(xml_file, dry_run=False)
        
        if count > 0:
            print(f"\n2️⃣ Vérification des résultats...")
            verify_fixes(xml_file)
            
            print(f"\n🎉 CORRECTION TERMINÉE !")
            print(f"✅ {count} chemins corrigés")
            print(f"💡 Testez maintenant vos outils d'analyse pour voir les résultats")
        else:
            print(f"ℹ️  Aucune correction effectuée")
    else:
        print("🔍 Mode simulation:")
        fix_music_paths(xml_file, dry_run=True)

if __name__ == "__main__":
    main()