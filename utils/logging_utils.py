#!/usr/bin/env python3
"""
Module de logging partagé pour tous les scripts audio
Gère les logs dans un dossier spécifique avec rotation automatique
"""

import os
import sys
import logging
import json
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta
import glob

class AudioLogger:
    """Classe pour gérer le logging centralisé des scripts audio."""
    
    def __init__(self, script_name, log_dir="logs", retention_days=30):
        self.script_name = script_name
        self.log_dir = Path(__file__).parent / log_dir
        self.retention_days = retention_days
        self.logger = None
        self.setup_logging()
    
    def setup_logging(self):
        """Configure le logging avec rotation automatique."""
        # Créer le dossier de logs
        self.log_dir.mkdir(exist_ok=True)
        
        # Configuration du logger
        self.logger = logging.getLogger(self.script_name)
        self.logger.setLevel(logging.INFO)
        
        # Éviter les doublons de handlers
        if self.logger.handlers:
            return
        
        # Formatter pour les logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler pour fichier avec rotation quotidienne
        log_file = self.log_dir / f"{self.script_name}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',  # Rotation tous les jours à minuit
            interval=1,
            backupCount=self.retention_days  # Garder les logs pendant X jours
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Handler pour console (moins verbeux)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        """Retourne le logger configuré."""
        return self.logger
    
    def save_json_report(self, data, filename):
        """Sauvegarde un rapport JSON dans le dossier de logs."""
        report_path = self.log_dir / filename
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"📄 Rapport JSON sauvegardé: {report_path}")
            return report_path
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la sauvegarde du rapport JSON {filename}: {e}")
            return None
    
    def cleanup_old_logs(self):
        """Nettoie les anciens fichiers de log et rapports."""
        if not self.log_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Nettoyer les logs rotated
        log_pattern = str(self.log_dir / f"{self.script_name}.log.*")
        log_files = glob.glob(log_pattern)
        
        for log_file in log_files:
            try:
                # Extraire la date du nom de fichier
                file_date_str = log_file.split('.')[-1]
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                
                if file_date < cutoff_date:
                    os.remove(log_file)
                    self.logger.info(f"🗑️ Log ancien supprimé: {log_file}")
            except (ValueError, IndexError):
                # Si on ne peut pas parser la date, supprimer quand même les très vieux fichiers
                file_stat = os.stat(log_file)
                file_age_days = (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                if file_age_days > self.retention_days:
                    os.remove(log_file)
                    self.logger.info(f"🗑️ Log très ancien supprimé: {log_file}")
        
        # Nettoyer les rapports JSON anciens
        json_pattern = str(self.log_dir / "*.json")
        json_files = glob.glob(json_pattern)
        
        for json_file in json_files:
            try:
                file_stat = os.stat(json_file)
                file_age_days = (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                if file_age_days > self.retention_days:
                    os.remove(json_file)
                    self.logger.info(f"🗑️ Rapport JSON ancien supprimé: {json_file}")
            except Exception as e:
                self.logger.warning(f"Erreur lors du nettoyage de {json_file}: {e}")

# Fonction utilitaire pour créer un logger rapidement
def get_audio_logger(script_name, log_dir="logs", retention_days=30):
    """Fonction utilitaire pour obtenir un logger audio configuré."""
    audio_logger = AudioLogger(script_name, log_dir, retention_days)
    return audio_logger.get_logger()

# Fonction pour nettoyer tous les logs anciens
def cleanup_all_logs(log_dir="logs", retention_days=30):
    """Nettoie tous les anciens logs et rapports dans le dossier de logs."""
    log_path = Path(__file__).parent / log_dir
    if not log_path.exists():
        return
    
    logger = logging.getLogger("cleanup")
    
    # Nettoyer tous les fichiers .log.* (rotated logs)
    log_pattern = str(log_path / "*.log.*")
    log_files = glob.glob(log_pattern)
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    for log_file in log_files:
        try:
            file_date_str = log_file.split('.')[-1]
            file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
            
            if file_date < cutoff_date:
                os.remove(log_file)
                print(f"🗑️ Log ancien supprimé: {log_file}")
        except (ValueError, IndexError):
            file_stat = os.stat(log_file)
            file_age_days = (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
            if file_age_days > retention_days:
                os.remove(log_file)
                print(f"🗑️ Log très ancien supprimé: {log_file}")
    
    # Nettoyer tous les rapports JSON anciens
    json_pattern = str(log_path / "*.json")
    json_files = glob.glob(json_pattern)
    
    for json_file in json_files:
        try:
            file_stat = os.stat(json_file)
            file_age_days = (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
            if file_age_days > retention_days:
                os.remove(json_file)
                print(f"🗑️ Rapport JSON ancien supprimé: {json_file}")
        except Exception as e:
            print(f"Erreur lors du nettoyage de {json_file}: {e}")

if __name__ == "__main__":
    # Script de nettoyage standalone
    import argparse
    
    parser = argparse.ArgumentParser(description="Nettoyer les anciens logs et rapports")
    parser.add_argument("--log-dir", default="logs", help="Dossier des logs (défaut: logs)")
    parser.add_argument("--retention-days", type=int, default=30, help="Nombre de jours à garder (défaut: 30)")
    
    args = parser.parse_args()
    cleanup_all_logs(args.log_dir, args.retention_days)
    print("✅ Nettoyage terminé")
