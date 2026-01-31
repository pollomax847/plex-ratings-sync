#!/bin/bash
# Script pour nettoyer les anciens logs Plex
# Garde seulement les logs des 30 derniers jours

SCRIPT_DIR="$(dirname "$0")"
LOG_DIR="$HOME/logs/plex_ratings"
DAILY_LOG_DIR="$HOME/logs/plex_daily"
BACKUP_DIR="$HOME/plex_backup"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "${BLUE}🧹 Nettoyage des anciens logs Plex${NC}"
log "======================================"

# Nombre de jours à garder
KEEP_DAYS=${1:-30}  # Par défaut 30 jours, ou passé en argument
log "📅 Conservation des logs des $KEEP_DAYS derniers jours"

# Fonction pour nettoyer un répertoire
cleanup_logs() {
    local dir="$1"
    local dir_name="$2"

    if [ ! -d "$dir" ]; then
        log "${YELLOW}⚠️  Répertoire $dir_name non trouvé${NC}"
        return
    fi

    log "${CYAN}🔍 Nettoyage de $dir_name...${NC}"

    # Compter les fichiers avant
    local count_before=$(find "$dir" -name "*.log" | wc -l)

    # Supprimer les fichiers plus vieux que KEEP_DAYS jours
    find "$dir" -name "*.log" -type f -mtime +$KEEP_DAYS -exec rm -f {} \; 2>/dev/null

    # Compter les fichiers après
    local count_after=$(find "$dir" -name "*.log" | wc -l)
    local deleted=$((count_before - count_after))

    if [ $deleted -gt 0 ]; then
        log "${GREEN}✅ $deleted ancien(s) log(s) supprimé(s) dans $dir_name${NC}"
    else
        log "${BLUE}ℹ️  Aucun ancien log à supprimer dans $dir_name${NC}"
    fi
}

# Nettoyer les différents répertoires de logs
cleanup_logs "$LOG_DIR" "plex_ratings"
cleanup_logs "$DAILY_LOG_DIR" "plex_daily"

# Nettoyer les logs éparpillés dans le home
log "${CYAN}🔍 Nettoyage des logs éparpillés dans $HOME...${NC}"
HOME_LOG_COUNT_BEFORE=$(find "$HOME" -maxdepth 1 -name "*.log" -type f | wc -l)
find "$HOME" -maxdepth 1 -name "*.log" -type f -mtime +$KEEP_DAYS -delete 2>/dev/null
HOME_LOG_COUNT_AFTER=$(find "$HOME" -maxdepth 1 -name "*.log" -type f | wc -l)
HOME_LOG_DELETED=$((HOME_LOG_COUNT_BEFORE - HOME_LOG_COUNT_AFTER))

if [ $HOME_LOG_DELETED -gt 0 ]; then
    log "${GREEN}✅ $HOME_LOG_DELETED ancien(s) log(s) supprimé(s) du home${NC}"
else
    log "${BLUE}ℹ️  Aucun ancien log dans le home${NC}"
fi

# Nettoyer les anciennes queues SongRec traitées
if [ -d "$HOME/songrec_queue" ]; then
    log "${CYAN}🔍 Nettoyage des anciennes queues SongRec...${NC}"
    QUEUE_COUNT_BEFORE=$(find "$HOME/songrec_queue" -name ".processed" -type f | wc -l)
    
    # Supprimer les queues traitées de plus de 7 jours
    find "$HOME/songrec_queue" -name ".processed" -type f -mtime +7 -exec dirname {} \; | xargs -r rm -rf
    
    QUEUE_COUNT_AFTER=$(find "$HOME/songrec_queue" -name ".processed" -type f | wc -l)
    QUEUE_DELETED=$((QUEUE_COUNT_BEFORE - QUEUE_COUNT_AFTER))
    
    if [ $QUEUE_DELETED -gt 0 ]; then
        log "${GREEN}✅ $QUEUE_DELETED ancienne(s) queue(s) SongRec supprimée(s)${NC}"
    else
        log "${BLUE}ℹ️  Aucune ancienne queue SongRec à supprimer${NC}"
    fi
fi

# Nettoyer les anciennes sauvegardes (garder seulement les 10 plus récentes)
if [ -d "$BACKUP_DIR" ]; then
    log "${CYAN}🔍 Nettoyage des anciennes sauvegardes...${NC}"

    local backup_count_before=$(find "$BACKUP_DIR" -name "ratings_*" | wc -l)

    # Garder seulement les 10 sauvegardes les plus récentes
    find "$BACKUP_DIR" -name "ratings_*" -type d -printf '%T@ %p\n' | sort -n | head -n -10 | cut -d' ' -f2- | xargs -r rm -rf

    local backup_count_after=$(find "$BACKUP_DIR" -name "ratings_*" | wc -l)
    local backup_deleted=$((backup_count_before - backup_count_after))

    if [ $backup_deleted -gt 0 ]; then
        log "${GREEN}✅ $backup_deleted ancienne(s) sauvegarde(s) supprimée(s)${NC}"
    else
        log "${BLUE}ℹ️  Aucune ancienne sauvegarde à supprimer${NC}"
    fi
fi

log ""
log "${GREEN}✅ Nettoyage des anciens logs terminé !${NC}"
log "${BLUE}📁 Logs conservés : $KEEP_DAYS jours${NC}"
log "${BLUE}💾 Sauvegardes conservées : 10 plus récentes${NC}"