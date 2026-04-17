#!/usr/bin/env python3
"""
iTunes Path Diagnostic - Diagnostic précis des chemins
"""

import re
import urllib.parse
from collections import defaultdict

def analyze_paths_detailed(xml_file):
    """Analyse détaillée des chemins dans le fichier XML"""
    
    print("🔍 DIAGNOSTIC DÉTAILLÉ DES CHEMINS")
    print("="*50)
    
    patterns = defaultdict(int)
    examples = defaultdict(list)
    file_status = {"exists": 0, "missing": 0}
    
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Trouver toutes les URLs dans les balises <string>
        location_pattern = r'<string>(file://[^<]+)</string>'
        matches = re.findall(location_pattern, content)
        
        print(f"📊 Trouvé {len(matches)} chemins de fichiers")
        
        for url in matches[:1000]:  # Limiter à 1000 pour l'analyse
            # Décoder l'URL
            decoded_url = urllib.parse.unquote(url)
            
            # Analyser les patterns
            if url.startswith('file://localhost/'):
                patterns['file://localhost/'] += 1
                if len(examples['file://localhost/']) < 3:
                    examples['file://localhost/'].append(url[:100])
            
            elif url.startswith('file:///mnt/'):
                patterns['file:///mnt/'] += 1
                if len(examples['file:///mnt/']) < 3:
                    examples['file:///mnt/'].append(url[:100])
            
            elif url.startswith('file://E:/'):
                patterns['file://E:/'] += 1
                if len(examples['file://E:/']) < 3:
                    examples['file://E:/'].append(url[:100])
            
            elif url.startswith('file:///E:/'):
                patterns['file:///E:/'] += 1
                if len(examples['file:///E:/']) < 3:
                    examples['file:///E:/'].append(url[:100])
            
            else:
                # Autres patterns
                prefix = url[:20] + "..."
                patterns[f"Autre: {prefix}"] += 1
                if len(examples[f"Autre: {prefix}"]) < 2:
                    examples[f"Autre: {prefix}"].append(url[:100])
            
            # Vérifier si le fichier existe
            if url.startswith('file://'):
                file_path = decoded_url.replace('file://localhost', '').replace('file://', '')
                import os
                if os.path.exists(file_path):
                    file_status["exists"] += 1
                else:
                    file_status["missing"] += 1
        
        # Afficher les résultats
        print(f"\n📈 PATTERNS DÉTECTÉS")
        print("-" * 40)
        
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(matches)) * 100 if matches else 0
            print(f"{pattern:25} : {count:6,} ({percentage:5.1f}%)")
            
            if pattern in examples and examples[pattern]:
                print(f"   Exemple: {examples[pattern][0]}")
        
        print(f"\n📁 STATUT DES FICHIERS")
        print("-" * 40)
        total_checked = file_status["exists"] + file_status["missing"]
        if total_checked > 0:
            exists_pct = (file_status["exists"] / total_checked) * 100
            missing_pct = (file_status["missing"] / total_checked) * 100
            print(f"✅ Fichiers existants : {file_status['exists']:,} ({exists_pct:.1f}%)")
            print(f"❌ Fichiers manquants : {file_status['missing']:,} ({missing_pct:.1f}%)")
        
        # Proposer des corrections
        print(f"\n💡 CORRECTIONS SUGGÉRÉES")
        print("-" * 40)
        
        if patterns['file://localhost/mnt/'] > 0:
            print(f"✅ Pattern détecté: 'file://localhost/mnt/'")
            print(f"   Pas de correction nécessaire - chemins Linux corrects")
        
        if patterns['file://localhost/'] > patterns['file://localhost/mnt/']:
            other_localhost = patterns['file://localhost/'] - patterns['file://localhost/mnt/']
            if other_localhost > 0:
                print(f"⚠️  {other_localhost} chemins 'file://localhost/' non-mnt détectés")
                print(f"   Exemple: {examples['file://localhost/'][0] if examples['file://localhost/'] else 'N/A'}")
        
        if file_status["missing"] > file_status["exists"]:
            print(f"⚠️  Plus de fichiers manquants que existants")
            print(f"   Vérifiez que /mnt/MyBook/ est bien monté")
        
        return patterns, examples, file_status
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None, None, None

def suggest_fixes(patterns, examples):
    """Suggère des corrections basées sur l'analyse"""
    
    print(f"\n🔧 ACTIONS RECOMMANDÉES")
    print("-" * 40)
    
    if not patterns:
        print("❌ Aucune donnée à analyser")
        return
    
    # Si tout est déjà en localhost/mnt, pas de correction nécessaire
    localhost_mnt = patterns.get('file://localhost/mnt/', 0)
    total = sum(patterns.values())
    
    if localhost_mnt > total * 0.9:  # Plus de 90% sont déjà corrects
        print("✅ Vos chemins sont déjà majoritairement corrects !")
        print("   Format: file://localhost/mnt/MyBook/...")
        print("   Aucune correction nécessaire")
    else:
        print("🔄 Corrections possibles:")
        
        for pattern, count in patterns.items():
            if count > 0 and 'localhost/mnt' not in pattern:
                print(f"   {pattern} → file://localhost/mnt/MyBook/")

def main():
    xml_file = "iTunes Music Library.xml"
    
    import os
    if not os.path.exists(xml_file):
        print(f"❌ Fichier non trouvé: {xml_file}")
        return
    
    patterns, examples, file_status = analyze_paths_detailed(xml_file)
    
    if patterns:
        suggest_fixes(patterns, examples)
        
        # Vérifier le montage
        print(f"\n🗂️  VÉRIFICATION DU MONTAGE")
        print("-" * 40)
        
        mount_point = "/mnt/MyBook/"
        if os.path.exists(mount_point):
            print(f"✅ {mount_point} existe")
            
            music_dir = "/mnt/MyBook/Musiques/"
            if os.path.exists(music_dir):
                print(f"✅ {music_dir} accessible")
                
                # Compter quelques fichiers
                try:
                    import subprocess
                    result = subprocess.run(['find', music_dir, '-name', '*.m4a', '-o', '-name', '*.mp3'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        file_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                        print(f"✅ Trouvé ~{file_count} fichiers audio")
                    else:
                        print("⚠️  Impossible de compter les fichiers")
                except:
                    print("⚠️  Impossible de scanner les fichiers")
            else:
                print(f"❌ {music_dir} non accessible")
        else:
            print(f"❌ {mount_point} non monté")
            print("💡 Vérifiez que votre disque externe est monté")

if __name__ == "__main__":
    main()