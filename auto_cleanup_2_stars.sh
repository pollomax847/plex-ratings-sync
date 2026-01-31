#!/bin/bash
# Script automatique pour:
# 1. Détecter les queues SongRec complétées
# 2. Vérifier que les fichiers 2 étoiles ont été renommés
# 3. Enlever automatiquement les ratings 2 étoiles

SCRIPT_DIR="$(dirname "$0")"
LOG_DIR="$HOME/logs/plex_ratings"
SONGREC_QUEUE_DIR="$HOME/songrec_queue"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/auto_cleanup_2_stars_$TIMESTAMP.log"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "${BLUE}🎵 Nettoyage automatique des ratings 1 et 2 étoiles${NC}"
log "=================================================================="
log ""
log "Processus:"
log "  1. Détecter les queues SongRec complétées"
log "  2. Vérifier que les fichiers ont été renommés"
log "  3. Enlever les ratings 1 et 2 étoiles"
log ""

# Vérifier que le répertoire songrec_queue existe
if [ ! -d "$SONGREC_QUEUE_DIR" ]; then
    log "${YELLOW}⚠️  Aucune queue SongRec trouvée${NC}"
    exit 0
fi

# Lister les queues
QUEUES=$(ls -t "$SONGREC_QUEUE_DIR" 2>/dev/null)

if [ -z "$QUEUES" ]; then
    log "${YELLOW}⚠️  Aucune queue SongRec à traiter${NC}"
    exit 0
fi

log "${CYAN}📁 Queues SongRec trouvées:${NC}"
echo "$QUEUES" | while read queue; do
    log "  - $queue"
done
log ""

# Traiter chaque queue
TOTAL_PROCESSED=0
TOTAL_FAILED=0

for QUEUE_NAME in $QUEUES; do
    QUEUE_PATH="$SONGREC_QUEUE_DIR/$QUEUE_NAME"
    
    log "${BLUE}🔄 Traitement de la queue: $QUEUE_NAME${NC}"
    
    # Vérifier que c'est un répertoire
    if [ ! -d "$QUEUE_PATH" ]; then
        continue
    fi
    
    # Vérifier qu'il y a un log de traitement
    SONGREC_LOG="$QUEUE_PATH/songrec_processing.log"
    if [ ! -f "$SONGREC_LOG" ]; then
        log "${YELLOW}  ⚠️  Pas de log songrec trouvé, queue ignorée${NC}"
        continue
    fi
    
    # Vérifier que le traitement est terminé (chercher "Traitement terminé")
    if ! grep -q "Traitement terminé" "$SONGREC_LOG"; then
        log "${YELLOW}  ⏳ Queue en cours de traitement, ignorée${NC}"
        continue
    fi
    
    # Compter les succès
    SUCCESS_COUNT=$(grep -c "✅ Succès" "$SONGREC_LOG" 2>/dev/null)
    SUCCESS_COUNT=${SUCCESS_COUNT:-0}
    
    if [ "$SUCCESS_COUNT" -eq 0 ]; then
        log "${YELLOW}  ⚠️  Aucun fichier renommé avec succès${NC}"
        continue
    fi
    
    log "${GREEN}  ✅ Queue complétée avec $SUCCESS_COUNT fichier(s) renommé(s)${NC}"
    
    # Lire le fichier JSON pour obtenir les chemins des fichiers renommés
    FILES_JSON="$QUEUE_PATH/files_details.json"
    
    if [ ! -f "$FILES_JSON" ]; then
        log "${YELLOW}  ⚠️  Fichier files_details.json non trouvé${NC}"
        continue
    fi
    
    log "${CYAN}  🔍 Vérification des fichiers renommés...${NC}"
    
    # Pour chaque fichier dans la queue, vérifier qu'il existe toujours
    FILES_TO_SCAN="$QUEUE_PATH/files_to_scan.txt"
    if [ -f "$FILES_TO_SCAN" ]; then
        FILES_EXIST=0
        FILES_NOT_FOUND=0
        
        while IFS= read -r file_path; do
            if [ -f "$file_path" ]; then
                FILES_EXIST=$((FILES_EXIST + 1))
                log "    ✓ Fichier trouvé: $(basename "$file_path")"
            else
                FILES_NOT_FOUND=$((FILES_NOT_FOUND + 1))
                log "    ❌ Fichier non trouvé: $file_path"
            fi
        done < "$FILES_TO_SCAN"
        
        if [ "$FILES_NOT_FOUND" -gt 0 ]; then
            log "${YELLOW}  ⚠️  $FILES_NOT_FOUND fichier(s) non trouvé(s) - queue peut être incomplète${NC}"
        fi
    fi
    
    # Maintenant, enlever les ratings 2 étoiles
    log "${BLUE}  🔄 Enlèvement des ratings 2 étoiles...${NC}"
    
    # Vérifier que le script existe
    if [ ! -f "$SCRIPT_DIR/clear_ratings_from_files.sh" ]; then
        log "${RED}  ❌ Script clear_ratings_from_files.sh non trouvé${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        continue
    fi
    
    # Exécuter le script de suppression des ratings
    OUTPUT=$(sudo $SCRIPT_DIR/clear_ratings_from_files.sh 2 2>&1)
    RESULT=$?
    
    if [ $RESULT -eq 0 ]; then
        log "${GREEN}  ✅ Ratings 2 étoiles enlevés avec succès${NC}"
        
        # Supprimer aussi les ratings 1 étoile
        OUTPUT1=$(sudo $SCRIPT_DIR/clear_ratings_from_files.sh 1 2>&1)
        RESULT1=$?
        if [ $RESULT1 -eq 0 ]; then
            log "${GREEN}  ✅ Ratings 1 étoile enlevés avec succès${NC}"
        else
            log "${YELLOW}  ⚠️ Erreur lors de l'enlèvement des ratings 1 étoile${NC}"
            log "  Détail: $OUTPUT1"
        fi
        
        # Marquer la queue comme traitée (renommer ou ajouter un flag)
        touch "$QUEUE_PATH/.processed"
        log "${GREEN}  ✅ Queue marquée comme traitée${NC}"
        
        # Supprimer les fichiers de log traités pour nettoyer
        if [ -f "$SONGREC_LOG" ]; then
            rm -f "$SONGREC_LOG"
            log "${BLUE}  🗑️ Log SongRec supprimé${NC}"
        fi
        
        TOTAL_PROCESSED=$((TOTAL_PROCESSED + 1))
    else
        log "${RED}  ❌ Erreur lors de l'enlèvement des ratings${NC}"
        log "  Détail: $OUTPUT"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi
    
    log ""
done

# Résumé final
log "${BLUE}================================================================${NC}"
log "${YELLOW}📊 RÉSUMÉ DU NETTOYAGE AUTOMATIQUE:${NC}"
log "   ✅ Queues traitées: $TOTAL_PROCESSED"
log "   ❌ Erreurs: $TOTAL_FAILED"
log ""

if [ "$TOTAL_PROCESSED" -gt 0 ]; then
    log "${GREEN}✅ Nettoyage automatique réussi!${NC}"
    log ""
    log "Les fichiers 2 étoiles ont été:"
    log "  1. Renommés par SongRec"
    log "  2. Leurs ratings ont été enlevés"
    log "  3. Ils sont maintenant des fichiers normaux"
    log ""
    log "Les fichiers 1 étoile ont été:"
    log "  1. Leurs ratings ont été enlevés"
    log "  2. Les fichiers ont été SUPPRIMÉS physiquement"
else
    log "${YELLOW}⚠️  Aucune queue à traiter ou erreur détectée${NC}"
fi

log ""
log "${BLUE}📁 Logs: $LOG_FILE${NC}"

exit 0
