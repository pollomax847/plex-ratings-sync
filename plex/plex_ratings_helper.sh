#!/bin/bash
# Script d'aide pour la synchronisation des ratings Plex
# Facilite la découverte de la base de données Plex et l'utilisation du script principal

script_dir="$(dirname "$0")"
sync_script="$script_dir/plex_ratings_sync.py"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 Assistant de synchronisation Plex Ratings${NC}"
echo "================================================="
echo

# Vérifier que Python et les dépendances sont installés
check_dependencies() {
    echo "🔍 Vérification des dépendances..."
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 non trouvé${NC}"
        exit 1
    fi
    
    # Vérifier sqlite3 (normalement inclus avec Python)
    if ! python3 -c "import sqlite3" 2>/dev/null; then
        echo -e "${RED}❌ Module sqlite3 manquant${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dépendances OK${NC}"
    echo
}

# Recherche automatique de la base Plex
find_plex_db() {
    echo "🔍 Recherche de la base de données Plex..."
    
    # Chemins possibles selon l'OS
    possible_paths=(
        "$HOME/.config/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
        "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
        "$HOME/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
        "$HOME/AppData/Local/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    )
    
    for path in "${possible_paths[@]}"; do
        if [ -f "$path" ]; then
            echo -e "${GREEN}✅ Base Plex trouvée: $path${NC}"
            return 0
        fi
    done
    
    echo -e "${YELLOW}⚠️ Base Plex non trouvée automatiquement${NC}"
    echo "Assurez-vous que Plex Media Server est installé et configuré."
    return 1
}

# Affiche les statistiques des ratings
show_stats() {
    echo "📊 Affichage des statistiques des ratings..."
    python3 "$sync_script" --auto-find-db --stats
}

# Mode simulation
simulate() {
    local rating=${1:-1}
    echo "🎭 Simulation de suppression des fichiers avec $rating étoile(s)..."
    python3 "$sync_script" --auto-find-db --rating "$rating"
}

# Mode suppression réelle
delete_real() {
    local rating=${1:-1}
    local backup_dir="$HOME/plex_backup_$(date +%Y%m%d_%H%M%S)"
    
    echo -e "${RED}⚠️  MODE SUPPRESSION RÉELLE${NC}"
    echo "Rating cible: $rating étoile(s)"
    echo "Sauvegarde: $backup_dir"
    echo
    
    read -p "Créer une sauvegarde avant suppression ? (O/n): " create_backup
    
    if [[ "$create_backup" =~ ^[Nn]$ ]]; then
        python3 "$sync_script" --auto-find-db --rating "$rating" --delete
    else
        echo "💾 Sauvegarde activée: $backup_dir"
        python3 "$sync_script" --auto-find-db --rating "$rating" --delete --backup "$backup_dir"
    fi
}

# Configuration interactive
configure_interactive() {
    echo "⚙️ Configuration interactive"
    echo "==========================="
    echo
    
    # Demander le rating cible
    read -p "Quel rating supprimer ? (1-5 étoiles, défaut: 1): " target_rating
    target_rating=${target_rating:-1}
    
    if ! [[ "$target_rating" =~ ^[1-5]$ ]]; then
        echo -e "${RED}❌ Rating invalide (doit être entre 1 et 5)${NC}"
        return 1
    fi
    
    echo
    echo "Options disponibles:"
    echo "1) 🎭 Simulation (aucune suppression)"
    echo "2) 🗑️ Suppression réelle AVEC sauvegarde"
    echo "3) 🗑️ Suppression réelle SANS sauvegarde (DANGEREUX)"
    echo "4) 📊 Voir les statistiques uniquement"
    echo
    
    read -p "Votre choix (1-4): " choice
    
    case "$choice" in
        1)
            simulate "$target_rating"
            ;;
        2)
            delete_real "$target_rating"
            ;;
        3)
            echo -e "${RED}⚠️ ATTENTION: Aucune sauvegarde!${NC}"
            read -p "Êtes-vous VRAIMENT sûr ? (tapez 'DANGEREUX'): " confirm
            if [ "$confirm" = "DANGEREUX" ]; then
                python3 "$sync_script" --auto-find-db --rating "$target_rating" --delete
            else
                echo "Opération annulée."
            fi
            ;;
        4)
            show_stats
            ;;
        *)
            echo -e "${RED}❌ Choix invalide${NC}"
            return 1
            ;;
    esac
}

# Menu principal
show_menu() {
    echo "Actions disponibles:"
    echo "==================="
    echo "1) 📊 Voir les statistiques des ratings"
    echo "2) 🎭 Simulation suppression 1 étoile"
    echo "3) 🗑️ Suppression réelle (mode interactif)"
    echo "4) ⚙️ Configuration avancée"
    echo "5) 🔍 Rechercher manuellement la base Plex"
    echo "6) ❌ Quitter"
    echo
}

# Fonction principale
main() {
    check_dependencies
    
    # Si des arguments sont passés, traiter directement
    case "${1:-}" in
        "stats"|"--stats")
            show_stats
            exit 0
            ;;
        "simulate"|"--simulate")
            rating=${2:-1}
            simulate "$rating"
            exit 0
            ;;
        "delete"|"--delete")
            rating=${2:-1}
            delete_real "$rating"
            exit 0
            ;;
        "find"|"--find")
            find_plex_db
            exit 0
            ;;
        "help"|"--help"|"-h")
            echo "Usage: $0 [stats|simulate|delete|find|help] [rating]"
            echo
            echo "Exemples:"
            echo "  $0 stats              - Afficher les statistiques"
            echo "  $0 simulate 2         - Simuler suppression 2 étoiles"
            echo "  $0 delete 1           - Supprimer réellement 1 étoile"
            echo "  $0 find               - Trouver la base Plex"
            echo
            echo "Sans argument: mode interactif"
            exit 0
            ;;
    esac
    
    # Mode interactif si aucun argument
    while true; do
        show_menu
        read -p "Votre choix (1-6): " choice
        echo
        
        case "$choice" in
            1)
                show_stats
                ;;
            2)
                simulate 1
                ;;
            3)
                configure_interactive
                ;;
            4)
                echo "🔧 Configuration avancée:"
                echo "Pour une utilisation avancée, utilisez directement:"
                echo "python3 $sync_script --help"
                ;;
            5)
                find_plex_db
                ;;
            6)
                echo "👋 Au revoir!"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Choix invalide${NC}"
                ;;
        esac
        
        echo
        read -p "Appuyez sur Entrée pour continuer..."
        echo
    done
}

# Lancer le script
main "$@"