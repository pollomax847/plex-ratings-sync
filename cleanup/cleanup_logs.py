#!/usr/bin/env python3
"""
Script de nettoyage automatique des logs et rapports anciens
À ajouter dans une crontab pour un nettoyage régulier
"""

import sys
from pathlib import Path

# Ajouter le répertoire courant au path pour importer logging_utils
sys.path.insert(0, str(Path(__file__).parent))

from logging_utils import cleanup_all_logs

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Nettoyer les anciens logs et rapports")
    parser.add_argument("--log-dir", default="logs", help="Dossier des logs à nettoyer")
    parser.add_argument("--retention-days", type=int, default=30, help="Nombre de jours à garder")
    
    args = parser.parse_args()
    
    print(f"🧹 Nettoyage des logs dans {args.log_dir} (rétention: {args.retention_days} jours)")
    cleanup_all_logs(args.log_dir, args.retention_days)
    print("✅ Nettoyage terminé")

if __name__ == "__main__":
    main()
