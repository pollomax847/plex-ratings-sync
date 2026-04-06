#!/bin/bash
# Script d'automatisation des playlists PlexAmp
# Génère des playlists intelligentes basées sur les ratings et métadonnées

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/logs/plexamp_playlists"
PLEX_DB="/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"

# Créer les répertoires nécessaires
mkdir -p "$LOG_DIR"

# Fonction de log
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/auto_playlists.log"
}

# Vérifier les prérequis
check_requirements() {
    log "${BLUE}🔍 Vérification des prérequis...${NC}"
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        log "${RED}❌ Python3 non trouvé${NC}"
        return 1
    fi
    
    # Vérifier la base Plex
    if [ ! -f "$PLEX_DB" ]; then
        log "${YELLOW}⚠️ Base Plex non trouvée: $PLEX_DB${NC}"
        log "   Vérifiez que Plex Media Server est installé et configuré"
        return 1
    fi
    
    # Vérifier le script Python
    if [ ! -f "$SCRIPT_DIR/auto_playlists_plexamp.py" ]; then
        log "${RED}❌ Script Python non trouvé${NC}"
        return 1
    fi
    
    log "${GREEN}✅ Prérequis vérifiés${NC}"
    return 0
}

# Créer les playlists automatiques
create_playlists() {
    local mode="$1"  # "create" ou "dry-run"
    
    if [ "$mode" = "dry-run" ]; then
        log "${YELLOW}📋 Mode simulation - aperçu des playlists${NC}"
        python3 "$SCRIPT_DIR/auto_playlists_plexamp.py" --plex-db "$PLEX_DB" --dry-run --verbose
    else
        log "${GREEN}🎵 Génération des playlists PlexAmp${NC}"
        python3 "$SCRIPT_DIR/auto_playlists_plexamp.py" --plex-db "$PLEX_DB" --verbose
    fi
}

# Nettoyer les anciennes playlists automatiques
cleanup_old_playlists() {
    log "${BLUE}🧹 Nettoyage des anciennes playlists automatiques${NC}"
    
    # Script Python pour supprimer les playlists automatiques existantes
    python3 << 'EOF'
import sqlite3
import sys

PLEX_DB = "/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"

try:
    with sqlite3.connect(PLEX_DB) as conn:
        conn.create_collation('icu_root', lambda a, b: (a > b) - (a < b))
        cursor = conn.cursor()
        
        # Trouver les playlists automatiques (préfixe [Auto])
        cursor.execute("""
            SELECT id, title FROM metadata_items 
            WHERE metadata_type = 15 AND title LIKE '[Auto] %'
        """)
        
        playlists = cursor.fetchall()
        deleted_count = 0
        
        for playlist_id, title in playlists:
            cursor.execute("DELETE FROM play_queue_generators WHERE playlist_id = ?", (playlist_id,))
            cursor.execute("DELETE FROM metadata_items WHERE id = ?", (playlist_id,))
            print(f"🗑️ Supprimée: {title}")
            deleted_count += 1
        
        conn.commit()
        print(f"✅ {deleted_count} anciennes playlists supprimées")
        
except Exception as e:
    print(f"❌ Erreur nettoyage: {e}")
    sys.exit(1)
EOF
}

# Menu principal
main_menu() {
    echo ""
    echo -e "${BLUE}🎵 GÉNÉRATEUR DE PLAYLISTS PLEXAMP${NC}"
    echo "====================================="
    echo ""
    echo "1. 📋 Aperçu des playlists (simulation)"
    echo "2. 🎵 Créer toutes les playlists"
    echo "3. 🧹 Nettoyer les anciennes playlists"
    echo "4. 🔄 Nettoyer + Recréer toutes les playlists"
    echo "5. ❌ Quitter"
    echo ""
    read -p "Votre choix (1-5): " choice
    
    case $choice in
        1)
            create_playlists "dry-run"
            ;;
        2)
            create_playlists "create"
            ;;
        3)
            cleanup_old_playlists
            ;;
        4)
            log "${BLUE}🔄 Nettoyage + Recréation complète${NC}"
            cleanup_old_playlists
            sleep 2
            create_playlists "create"
            ;;
        5)
            log "${GREEN}👋 Au revoir !${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Choix invalide${NC}"
            main_menu
            ;;
    esac
}

# Traitement des arguments en ligne de commande
case "${1:-}" in
    "--preview"|"-p")
        check_requirements && create_playlists "dry-run"
        ;;
    "--create"|"-c")
        check_requirements && create_playlists "create"
        ;;
    "--clean"|"--cleanup")
        cleanup_old_playlists
        ;;
    "--refresh"|"-r")
        check_requirements && cleanup_old_playlists && create_playlists "create"
        ;;
    "--help"|"-h")
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  -p, --preview     Aperçu des playlists (simulation)"
        echo "  -c, --create      Créer toutes les playlists"
        echo "  --clean           Nettoyer les anciennes playlists"
        echo "  -r, --refresh     Nettoyer + recréer toutes les playlists"
        echo "  -h, --help        Afficher cette aide"
        echo ""
        echo "Sans option: mode interactif"
        ;;
    "")
        # Mode interactif
        check_requirements
        if [ $? -eq 0 ]; then
            main_menu
        else
            log "${RED}❌ Prérequis non satisfaits${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${RED}❌ Option inconnue: $1${NC}"
        echo "Utilisez --help pour voir les options disponibles"
        exit 1
        ;;
esac