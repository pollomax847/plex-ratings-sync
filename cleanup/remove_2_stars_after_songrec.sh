#!/bin/bash
# Script pour ENLEVER LES RATINGS 2 ÉTOILES des fichiers audio
# (Après renommage SongRec réussi - les fichiers restent, seulement les étoiles sont supprimées)

SCRIPT_DIR="$(dirname "$0")"
LOG_DIR="$HOME/logs/plex_ratings"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/remove_2_stars_$TIMESTAMP.log"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "${BLUE}🎵 Suppression des RATINGS 2 étoiles (fichiers conservés)${NC}"
log "=================================================================="
log ""

# Trouver la base de données Plex
PLEX_DB=$(find /var/snap/plexmediaserver -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)

# Si pas trouvée, chercher dans les emplacements courants
if [ -z "$PLEX_DB" ]; then
    PLEX_DB=$(find ~/.config/Plex\ Media\ Server -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)
fi

if [ -z "$PLEX_DB" ] || [ ! -f "$PLEX_DB" ]; then
    log "${RED}❌ Base de données Plex non trouvée${NC}"
    exit 1
fi

log "${GREEN}✅ Base Plex trouvée: $PLEX_DB${NC}"
log ""

# Lancer le script Python pour ENLEVER les ratings 2 étoiles (pas supprimer les fichiers)
log "${BLUE}🔄 Enlèvement des ratings 2 étoiles...${NC}"
python3 "$SCRIPT_DIR/plex_ratings_sync.py" \
    --plex-db "$PLEX_DB" \
    --rating 2 \
    --delete \
    2>&1 | tee -a "$LOG_FILE"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    log "${GREEN}✅ Ratings 2 étoiles enlevés avec succès!${NC}"
    log ""
    log "${YELLOW}📝 Résumé:${NC}"
    log "   ✓ Les fichiers avec 2 étoiles ont été CONSERVÉS"
    log "   ✓ Les ratings 2 étoiles ont été ENLEVÉES"
    log "   ✓ Les fichiers sont maintenant traités comme des fichiers normaux"
else
    log "${RED}❌ Erreur lors de l'enlèvement des ratings${NC}"
fi

log ""
log "${BLUE}Logs sauvegardés: $LOG_FILE${NC}"

exit $RESULT
