#!/bin/bash
# Script pour analyser et gérer les ratings d'albums interactif

SCRIPT_DIR="$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%H:%M:%S')] $1"
}

# Fonction pour afficher les albums par rating
show_albums_by_rating() {
    local rating="$1"
    local temp_dir="/tmp/plex_album_analysis_$$"
    mkdir -p "$temp_dir"
    
    log "${BLUE}📊 Analyse des albums avec $rating étoile(s)...${NC}"
    
    # Lancer l'analyse
    if /home/paulceline/bin/audio/.venv/bin/python "$SCRIPT_DIR/album_ratings_manager.py" \
        '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db' \
        "$temp_dir" > /dev/null 2>&1; then
        
        # Afficher les albums selon le rating
        case "$rating" in
            "1")
                if [ -f "$temp_dir/albums_1_star.json" ]; then
                    album_count=$(jq length "$temp_dir/albums_1_star.json")
                    if [ "$album_count" -gt 0 ]; then
                        log "${RED}🗑️ $album_count album(s) avec 1 étoile (à supprimer):${NC}"
                        jq -r '.[] | "  📀 \(.artist_name) - \(.album_title) (\(.track_count) pistes)"' "$temp_dir/albums_1_star.json"
                        
                        echo ""
                        log "${YELLOW}📁 Fichiers qui seront supprimés:${NC}"
                        jq -r '.[] | .files[]' "$temp_dir/albums_1_star.json" | head -10
                        local total_files=$(jq -r '.[] | .files[]' "$temp_dir/albums_1_star.json" | wc -l)
                        if [ "$total_files" -gt 10 ]; then
                            log "   ... et $(($total_files - 10)) autres fichiers"
                        fi
                    else
                        log "${GREEN}✅ Aucun album avec 1 étoile${NC}"
                    fi
                fi
                ;;
            "2")
                if [ -f "$temp_dir/albums_2_star.json" ]; then
                    album_count=$(jq length "$temp_dir/albums_2_star.json")
                    if [ "$album_count" -gt 0 ]; then
                        log "${YELLOW}🔍 $album_count album(s) avec 2 étoiles (songrec-rename):${NC}"
                        jq -r '.[] | "  📀 \(.artist_name) - \(.album_title) (\(.track_count) pistes)"' "$temp_dir/albums_2_star.json"
                        
                        echo ""
                        log "${BLUE}📁 Fichiers pour songrec-rename:${NC}"
                        jq -r '.[] | .files[]' "$temp_dir/albums_2_star.json" | head -10
                        local total_files=$(jq -r '.[] | .files[]' "$temp_dir/albums_2_star.json" | wc -l)
                        if [ "$total_files" -gt 10 ]; then
                            log "   ... et $(($total_files - 10)) autres fichiers"
                        fi
                    else
                        log "${GREEN}✅ Aucun album avec 2 étoiles${NC}"
                    fi
                fi
                ;;
            "all")
                log "${PURPLE}📊 Résumé complet des ratings d'albums:${NC}"
                if [ -f "$temp_dir/ratings_stats.json" ]; then
                    local albums_1=$(jq -r '.albums_1_star' "$temp_dir/ratings_stats.json")
                    local albums_2=$(jq -r '.albums_2_star' "$temp_dir/ratings_stats.json")
                    local albums_sync=$(jq -r '.albums_sync_rating' "$temp_dir/ratings_stats.json")
                    local files_1=$(jq -r '.files_1_star_total' "$temp_dir/ratings_stats.json")
                    local files_2=$(jq -r '.files_2_star_total' "$temp_dir/ratings_stats.json")
                    
                    echo ""
                    log "${RED}🗑️  Albums à supprimer (1⭐): $albums_1${NC}"
                    log "${YELLOW}🔍 Albums pour songrec (2⭐): $albums_2${NC}"
                    log "${GREEN}🎵 Albums à synchroniser (3-5⭐): $albums_sync${NC}"
                    echo ""
                    log "${CYAN}📁 Total fichiers 1⭐: $files_1${NC}"
                    log "${CYAN}📁 Total fichiers 2⭐: $files_2${NC}"
                fi
                ;;
        esac
    else
        log "${RED}❌ Erreur lors de l'analyse des albums${NC}"
    fi
    
    # Nettoyer
    rm -rf "$temp_dir"
}

# Fonction pour afficher le menu interactif
show_menu() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           🎵 GESTION ALBUMS PLEX 🎵           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Choisissez une action:${NC}"
    echo ""
    echo -e "  ${RED}1)${NC} Voir albums avec 1 étoile (suppression)"
    echo -e "  ${YELLOW}2)${NC} Voir albums avec 2 étoiles (songrec-rename)"
    echo -e "  ${PURPLE}3)${NC} Résumé complet des ratings"
    echo -e "  ${BLUE}4)${NC} Lancer le workflow mensuel complet"
    echo -e "  ${GREEN}5)${NC} Test de l'analyse (dry-run)"
    echo -e "  ${CYAN}0)${NC} Quitter"
    echo ""
    echo -n -e "${BLUE}Votre choix: ${NC}"
}

# Fonction principale
main() {
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                clear
                show_albums_by_rating "1"
                echo ""
                read -p "Appuyez sur Entrée pour continuer..."
                ;;
            2)
                clear
                show_albums_by_rating "2"
                echo ""
                read -p "Appuyez sur Entrée pour continuer..."
                ;;
            3)
                clear
                show_albums_by_rating "all"
                echo ""
                read -p "Appuyez sur Entrée pour continuer..."
                ;;
            4)
                clear
                log "${BLUE}🚀 Lancement du workflow mensuel avec gestion d'albums...${NC}"
                echo ""
                read -p "Confirmer le lancement ? (y/N): " confirm
                if [[ $confirm =~ ^[Yy]$ ]]; then
                    # Notification de début de workflow manuel
                    "$SCRIPT_DIR/plex_notifications.sh" critical_error "Manuel" "Workflow lancé manuellement depuis l'interface"
                    "$SCRIPT_DIR/plex_monthly_workflow.sh"
                fi
                echo ""
                read -p "Appuyez sur Entrée pour continuer..."
                ;;
            5)
                clear
                log "${YELLOW}🧪 Test de l'analyse (aucune modification)...${NC}"
                show_albums_by_rating "all"
                echo ""
                read -p "Appuyez sur Entrée pour continuer..."
                ;;
            0)
                log "${GREEN}Au revoir ! 👋${NC}"
                break
                ;;
            *)
                echo ""
                log "${RED}❌ Choix invalide. Réessayez.${NC}"
                sleep 1
                ;;
        esac
    done
}

# Lancer le script
if [ "${1:-}" = "--direct" ]; then
    # Mode direct pour appel depuis d'autres scripts
    show_albums_by_rating "${2:-all}"
else
    # Mode interactif
    main
fi