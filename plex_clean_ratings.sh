#!/bin/bash
# Script pour nettoyer automatiquement les ratings des fichiers inexistants dans Plex
# Supprime les ratings des fichiers qui ont été supprimés du disque

SCRIPT_DIR="$(dirname "$0")"
LOG_DIR="$HOME/logs/plex_ratings"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/clean_ratings_$TIMESTAMP.log"

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

log "${BLUE}🧹 Nettoyage automatique des ratings Plex${NC}"
log "=================================================================="
log ""
log "Suppression des ratings des fichiers inexistants"
log ""

# Trouver la base de données Plex
log "${CYAN}🔍 Recherche de la base de données Plex...${NC}"
PLEX_DB=$(find /var/snap/plexmediaserver -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)

if [ -z "$PLEX_DB" ]; then
    PLEX_DB=$(find ~/.config/Plex\ Media\ Server -name "com.plexapp.plugins.library.db" 2>/dev/null | head -1)
fi

if [ -z "$PLEX_DB" ] || [ ! -f "$PLEX_DB" ]; then
    log "${RED}❌ Base de données Plex non trouvée${NC}"
    exit 1
fi

log "${GREEN}✅ Base Plex trouvée${NC}"

# Arrêter Plex temporairement
log "${YELLOW}🛑 Arrêt temporaire de Plex...${NC}"
sudo snap stop plexmediaserver

# Script Python pour nettoyer les ratings
export PLEX_DB
sudo -E python3 << 'PYTHON_EOF'
import sqlite3
import os
import sys

def clean_orphaned_ratings():
    """Supprime les ratings des fichiers qui n'existent plus"""
    try:
        conn = sqlite3.connect(os.environ['PLEX_DB'])
        cursor = conn.cursor()
        
        # Trouver tous les fichiers avec ratings
        cursor.execute("""
            SELECT mp.file, mis.rating, mi.title, mis.id as setting_id
            FROM media_parts mp
            JOIN media_items media ON mp.media_item_id = media.id
            JOIN metadata_items mi ON media.metadata_item_id = mi.id
            JOIN metadata_item_settings mis ON mis.guid = mi.guid
            WHERE mis.rating IS NOT NULL
        """)
        
        ratings = cursor.fetchall()
        cleaned = 0
        total = len(ratings)
        
        print(f"📊 Analyse de {total} fichiers avec ratings...")
        
        for file_path, rating, title, setting_id in ratings:
            if not os.path.exists(file_path):
                # Supprimer le rating
                cursor.execute("DELETE FROM metadata_item_settings WHERE id = ?", (setting_id,))
                print(f"🗑️ Rating supprimé pour fichier inexistant: {os.path.basename(file_path)} (était {rating}⭐)")
                cleaned += 1
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ Nettoyage terminé: {cleaned} ratings supprimés")
        return cleaned
        
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        return 0

# Exécuter le nettoyage
cleaned = clean_orphaned_ratings()
PYTHON_EOF

RESULT=$?

# Redémarrer Plex
log "${GREEN}🔄 Redémarrage de Plex...${NC}"
sudo snap start plexmediaserver
log "${GREEN}✅ Plex redémarré${NC}"

if [ $RESULT -eq 0 ]; then
    log "${GREEN}✅ Nettoyage terminé avec succès${NC}"
else
    log "${RED}❌ Erreur lors du nettoyage${NC}"
fi

log "${BLUE}📁 Logs: $LOG_FILE${NC}"

exit $RESULT
