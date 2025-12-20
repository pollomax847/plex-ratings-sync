#!/bin/bash
# Script pour ENLEVER LES ÉTOILES des fichiers audio dans Plex
# Les fichiers sont CONSERVÉS, seules les étoiles (ratings) sont enlevées
# Utilisation: ./clear_ratings_from_files.sh [rating_number]

SCRIPT_DIR="$(dirname "$0")"
LOG_DIR="$HOME/logs/plex_ratings"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/clear_ratings_$TIMESTAMP.log"

# Paramètres
RATING=${1:-2}  # Par défaut: 2 étoiles

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

log "${BLUE}🎵 Script pour ENLEVER LES ÉTOILES des fichiers audio${NC}"
log "=================================================================="
log ""
log "✅ Les fichiers seront CONSERVÉS"
log "✅ Seules les étoiles (ratings) seront ENLEVÉES"
log ""

# Trouver la base de données Plex
log "${CYAN}🔍 Recherche de la base de données Plex...${NC}"
PLEX_DB=$(find /var/snap/plexmediaserver -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)

# Si pas trouvée, chercher dans les emplacements courants
if [ -z "$PLEX_DB" ]; then
    PLEX_DB=$(find ~/.config/Plex\ Media\ Server -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)
fi

if [ -z "$PLEX_DB" ] || [ ! -f "$PLEX_DB" ]; then
    log "${RED}❌ Base de données Plex non trouvée${NC}"
    log ""
    log "Emplacements vérifiés:"
    log "  - /var/snap/plexmediaserver/"
    log "  - ~/.config/Plex Media Server/"
    exit 1
fi

log "${GREEN}✅ Base Plex trouvée: $PLEX_DB${NC}"
log ""

# Arrêter Plex temporairement pour accéder à la base de données
log "${YELLOW}🛑 Arrêt temporaire de Plex pour accès à la base...${NC}"
sudo snap stop plexmediaserver
sleep 5

# Créer une sauvegarde de la base de données
BACKUP_DIR="$HOME/plex_backup/ratings_$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp "$PLEX_DB" "$BACKUP_DIR/com.plexapp.plugins.library.db.bak"
log "${GREEN}✅ Sauvegarde créée: $BACKUP_DIR${NC}"
log ""

# Afficher le nombre de fichiers avec ce rating
log "${CYAN}📊 Analyse des fichiers avec $RATING étoile(s)...${NC}"
export PLEX_DB RATING
COUNT=$(python3 << 'PYTHON_END'
import sqlite3
import sys
import os

try:
    db_path = os.environ['PLEX_DB']
    rating = float(os.environ['RATING'])
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Chercher les fichiers avec ce rating dans metadata_item_settings
    cursor.execute("""
        SELECT COUNT(*) FROM metadata_item_settings 
        WHERE rating = ?
    """, (rating,))
    
    count = cursor.fetchone()[0]
    print(count)
    conn.close()
except Exception as e:
    print(f"Erreur: {e}", file=sys.stderr)
    print("0")
PYTHON_END
)

log "📊 Nombre de fichiers avec $RATING étoile(s): ${COUNT}"
log ""

if [ "$COUNT" -eq 0 ]; then
    log "${YELLOW}⚠️  Aucun fichier trouvé avec $RATING étoile(s)${NC}"
    log ""
    exit 0
fi

# Enlever les ratings
log "${BLUE}🔄 Enlèvement des ratings...${NC}"
export PLEX_DB RATING
python3 << 'PYTHON_END'
import sqlite3
import sys
import os
from datetime import datetime

try:
    db_path = os.environ['PLEX_DB']
    rating = float(os.environ['RATING'])
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Trouver les fichiers avec ce rating
    cursor.execute("""
        SELECT mis.id, mi.title FROM metadata_item_settings mis 
        JOIN metadata_items mi ON mis.guid = mi.guid 
        WHERE mis.rating = ?
    """, (rating,))
    
    files = cursor.fetchall()
    
    # Enlever les ratings (mettre à NULL)
    cursor.execute("""
        UPDATE metadata_item_settings 
        SET rating = NULL, updated_at = ?
        WHERE rating = ?
    """, (datetime.now().timestamp(), rating))
    
    conn.commit()
    
    print(f"✅ {cursor.rowcount} fichier(s) mis à jour")
    
    # Afficher les fichiers modifiés
    for file_id, title in files:
        print(f"   ✓ {title}")
    
    conn.close()
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Erreur: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_END

RESULT=$?

log ""
if [ $RESULT -eq 0 ]; then
    log "${GREEN}✅ Ratings $RATING étoile(s) enlevés avec succès!${NC}"
    log ""
    log "${YELLOW}📝 Résumé:${NC}"
    log "   ✓ $COUNT fichier(s) modifié(s)"
    log "   ✓ Les fichiers sont CONSERVÉS"
    log "   ✓ Les étoiles sont ENLEVÉES"
    log "   ✓ Les fichiers sont maintenant sans rating"
    log ""
else
    log "${RED}❌ Erreur lors de l'enlèvement des ratings${NC}"
fi

# Redémarrer Plex
log "${GREEN}🔄 Redémarrage de Plex...${NC}"
sudo snap start plexmediaserver
log "${GREEN}✅ Plex redémarré${NC}"

log ""
log "${BLUE}📁 Logs sauvegardés: $LOG_FILE${NC}"
log "${BLUE}💾 Sauvegarde: $BACKUP_DIR${NC}"

exit $RESULT
