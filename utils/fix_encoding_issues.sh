#!/bin/bash
# Script pour corriger les problèmes d'encodage dans les noms de fichiers/dossiers
# et permettre à songrec de fonctionner correctement

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de log
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fix_encoding_in_path() {
    local target_path="$1"
    local dry_run="${2:-false}"
    
    log "${BLUE}🔍 Analyse des problèmes d'encodage dans: $target_path${NC}"
    
    # Trouver tous les fichiers/dossiers avec des caractères d'encodage problématiques
    find "$target_path" -type d -name "*ë*" -o -name "*ì*" -o -name "*í*" -o -name "*î*" -o -name "*ï*" | while read -r problematic_path; do
        log "${YELLOW}⚠️  Problème d'encodage détecté: $problematic_path${NC}"
        
        # Extraire le nom de base et le répertoire parent
        parent_dir=$(dirname "$problematic_path")
        base_name=$(basename "$problematic_path")
        
        # Nettoyer le nom en supprimant/remplaçant les caractères problématiques
        clean_name=$(echo "$base_name" | \
            sed 's/ë¸"/(/g' | \
            sed 's/ëž™//g' | \
            sed 's/ì•„í‹€ë//g' | \
            sed 's/[ëìíîï]//g' | \
            tr -cd '[:alnum:][:space:]()._-' | \
            sed 's/  */ /g' | \
            sed 's/^ *//;s/ *$//')
        
        # Si le nom a changé, proposer le renommage
        if [ "$base_name" != "$clean_name" ] && [ -n "$clean_name" ]; then
            new_path="$parent_dir/$clean_name"
            
            if [ "$dry_run" = "true" ]; then
                log "${GREEN}📝 Renommage proposé:${NC}"
                log "   DE: $problematic_path"
                log "   VERS: $new_path"
            else
                log "${GREEN}🔄 Renommage en cours...${NC}"
                if mv "$problematic_path" "$new_path" 2>/dev/null; then
                    log "✅ Renommage réussi: $clean_name"
                else
                    log "${RED}❌ Échec du renommage: $problematic_path${NC}"
                fi
            fi
        fi
    done
}

# Solution spécifique pour le répertoire Black Atlass
fix_black_atlass() {
    local music_root="$1"
    local problematic_dir="$music_root/Black Atlass(ë¸\"ëž™ ì•„í‹€ë"
    local clean_dir="$music_root/Black Atlass"
    
    if [ -d "$problematic_dir" ]; then
        log "${YELLOW}🎵 Correction du répertoire Black Atlass${NC}"
        
        # Créer le nouveau répertoire avec le nom correct
        if [ ! -d "$clean_dir" ]; then
            mkdir -p "$clean_dir"
            log "✅ Répertoire créé: $clean_dir"
        fi
        
        # Déplacer tous les contenus
        if mv "$problematic_dir"/* "$clean_dir"/ 2>/dev/null; then
            log "✅ Contenu déplacé vers: $clean_dir"
            
            # Supprimer l'ancien répertoire
            if rmdir "$problematic_dir" 2>/dev/null; then
                log "✅ Ancien répertoire supprimé"
            fi
        else
            log "${RED}❌ Échec du déplacement${NC}"
            return 1
        fi
    else
        log "${GREEN}✅ Répertoire Black Atlass déjà correct ou introuvable${NC}"
    fi
}

# Fonction principale
main() {
    local music_path="${1:-/mnt/mybook/itunes/Music}"
    local action="${2:-fix}"  # fix, scan, ou dry-run
    
    log "${BLUE}🔧 Correction des problèmes d'encodage pour songrec${NC}"
    log "Répertoire cible: $music_path"
    
    case "$action" in
        "scan")
            log "${YELLOW}📋 Mode scan uniquement${NC}"
            fix_encoding_in_path "$music_path" true
            ;;
        "dry-run")
            log "${YELLOW}📋 Mode simulation${NC}"
            fix_black_atlass "$music_path"
            fix_encoding_in_path "$music_path" true
            ;;
        "fix")
            log "${GREEN}🔧 Mode correction${NC}"
            fix_black_atlass "$music_path"
            fix_encoding_in_path "$music_path" false
            ;;
        *)
            echo "Usage: $0 [chemin_musique] [scan|dry-run|fix]"
            echo "Exemple: $0 /mnt/mybook/itunes/Music fix"
            exit 1
            ;;
    esac
    
    log "${GREEN}✅ Traitement terminé${NC}"
}

# Lancer le script
main "$@"
