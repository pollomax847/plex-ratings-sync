#!/usr/bin/env python3
"""
Script pour détecter les fichiers audio sans correspondance entre deux bibliothèques
Avec vérification par fingerprint songrec-rename et déplacement des orphelins
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from logging_utils import get_audio_logger, cleanup_all_logs

def get_audio_files(directory):
    """Récupère tous les fichiers audio dans un répertoire de manière récursive."""
    audio_extensions = {'.mp3', '.flac', '.m4a', '.ogg', '.wma', '.wav', '.aac'}
    audio_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in audio_extensions:
                full_path = os.path.join(root, file)
                # Chemin relatif par rapport au répertoire racine
                rel_path = os.path.relpath(full_path, directory)
                audio_files.append((rel_path.lower(), full_path))  # (rel_path_lower, full_path)
    return audio_files

def get_songrec_fingerprint(file_path):
    """Utilise songrec-rename pour obtenir le fingerprint audio d'un fichier."""
    try:
        result = subprocess.run([
            "songrec-rename", "--fingerprint", file_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        fingerprint = result.stdout.strip()
        return fingerprint if fingerprint else None
    except Exception as e:
        logger = logging.getLogger()
        logger.warning(f"songrec-rename failed for {file_path}: {e}")
        return None

def build_fingerprint_cache(files, name=""):
    """Construit un cache de fingerprints pour accélérer la recherche."""
    logger = logging.getLogger()
    logger.info(f"🔨 Construction du cache de fingerprints pour {name}...")
    cache = {}
    total = len(files)
    for idx, (rel_path, full_path) in enumerate(files, 1):
        if idx % 100 == 0:
            logger.info(f"   Progression: {idx}/{total} fichiers analysés...")
        fp = get_songrec_fingerprint(full_path)
        if fp:
            cache[fp] = full_path
    logger.info(f"   ✅ Cache créé: {len(cache)} fingerprints uniques")
    return cache

def scan_target_for_fingerprint_match(target_cache, fingerprint):
    """Cherche un fichier dans le cache avec le même fingerprint."""
    return target_cache.get(fingerprint)

def move_to_orphans_dir(file_path, orphans_dir, source_dir, dry_run=False):
    """Déplace un fichier vers le dossier des orphelins."""
    logger = logging.getLogger()
    if dry_run:
        rel_path = os.path.relpath(file_path, source_dir)
        dest_path = os.path.join(orphans_dir, rel_path)
        logger.info(f"   📁 [DRY-RUN] Serait déplacé vers: {dest_path}")
        return
    
    if not os.path.exists(orphans_dir):
        os.makedirs(orphans_dir)
    
    # Conserver la structure relative
    rel_path = os.path.relpath(file_path, source_dir)
    dest_path = os.path.join(orphans_dir, rel_path)
    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    shutil.move(file_path, dest_path)
    logger.info(f"   📁 Déplacé vers: {dest_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Détecter et déplacer les fichiers audio orphelins")
    parser.add_argument("source_dir", help="Dossier source à analyser")
    parser.add_argument("target_dir", help="Dossier cible de référence")
    parser.add_argument("orphans_dir", help="Dossier où déplacer les orphelins")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation (pas de déplacement)")
    parser.add_argument("--log-dir", default="logs", help="Dossier pour les logs (défaut: logs)")
    parser.add_argument("--retention-days", type=int, default=30, help="Nombre de jours à garder les logs (défaut: 30)")
    
    args = parser.parse_args()
    
    # Configuration du logging avec le module partagé
    logger = get_audio_logger("detect_missing_audio", args.log_dir, args.retention_days)
    cleanup_all_logs(args.log_dir, args.retention_days)
    
    source_dir = args.source_dir
    target_dir = args.target_dir
    orphans_dir = args.orphans_dir
    dry_run = args.dry_run
    
    logger.info(f"🚀 Démarrage de la détection d'orphelins audio")
    logger.info(f"   Source: {source_dir}")
    logger.info(f"   Cible: {target_dir}")
    logger.info(f"   Orphelins: {orphans_dir}")
    logger.info(f"   Mode: {'Simulation' if dry_run else 'Déplacement réel'}")
    
    if not os.path.exists(source_dir):
        logger.error(f"❌ Dossier source inexistant: {source_dir}")
        sys.exit(1)
    
    if not os.path.exists(target_dir):
        logger.error(f"❌ Dossier cible inexistant: {target_dir}")
        sys.exit(1)
    
    logger.info(f"🔍 Analyse des fichiers audio dans {source_dir}...")
    source_files = get_audio_files(source_dir)
    logger.info(f"   Trouvé {len(source_files)} fichiers audio dans la source")
    
    logger.info(f"🔍 Analyse des fichiers audio dans {target_dir}...")
    target_files = get_audio_files(target_dir)
    logger.info(f"   Trouvé {len(target_files)} fichiers audio dans la cible")
    
    # Créer des sets pour la comparaison rapide
    source_rel_paths = {rel.lower() for rel, full in source_files}
    target_rel_paths = {rel.lower() for rel, full in target_files}
    
    # Fichiers présents dans source mais pas dans cible par nom
    missing_by_name = source_rel_paths - target_rel_paths
    logger.info(f"\n🔍 {len(missing_by_name)} fichiers sans correspondance par nom")
    
    if not missing_by_name:
        logger.info(f"\n✅ Tous les fichiers ont une correspondance par nom!")
        return
    
    # Construire le cache de fingerprints pour la cible
    target_cache = build_fingerprint_cache(target_files, "cible")
    
    # Pour chaque fichier manquant, essayer le fingerprint
    truly_missing = []
    for idx, rel_path_lower in enumerate(missing_by_name, 1):
        # Trouver le full_path correspondant
        full_path = next(full for rel, full in source_files if rel.lower() == rel_path_lower)
        
        logger.info(f"🔎 [{idx}/{len(missing_by_name)}] Vérification: {os.path.basename(full_path)}")
        fp = get_songrec_fingerprint(full_path)
        if fp:
            match = scan_target_for_fingerprint_match(target_cache, fp)
            if match:
                logger.info(f"   ✅ Correspondance trouvée par fingerprint: {os.path.basename(match)}")
                continue  # Pas orphelin
            else:
                logger.info(f"   ❌ Pas de correspondance par fingerprint")
        else:
            logger.warning(f"   ⚠ Impossible d'obtenir le fingerprint")
        
        truly_missing.append(full_path)
    
    if truly_missing:
        action = "Simulation" if dry_run else "Déplacement"
        logger.info(f"\n📁 {action} de {len(truly_missing)} fichiers orphelins vers {orphans_dir}...")
        for file_path in truly_missing:
            move_to_orphans_dir(file_path, orphans_dir, source_dir, dry_run)
        if not dry_run:
            logger.info(f"\n✅ Terminé! {len(truly_missing)} fichiers déplacés.")
        else:
            logger.info(f"\n✅ Simulation terminée! {len(truly_missing)} fichiers seraient déplacés.")
    else:
        logger.info(f"\n✅ Aucun fichier orphelin trouvé.")

if __name__ == "__main__":
    main()
