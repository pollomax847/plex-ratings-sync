#!/bin/bash
# Script pour détecter les problèmes d'encodage potentiels avant songrec

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

detect_encoding_issues() {
    local target_path="$1"
    local output_file="${2:-encoding_issues.txt}"
    
    log "${BLUE}🔍 Détection des problèmes d'encodage dans: $target_path${NC}"
    
    # Initialiser le fichier de sortie
    echo "# Problèmes d'encodage détectés le $(date)" > "$output_file"
    echo "# Chemin analysé: $target_path" >> "$output_file"
    echo "" >> "$output_file"
    
    local issues_found=0
    
    # Chercher des caractères d'encodage problématiques
    while IFS= read -r -d '' file; do
        local basename_file=$(basename "$file")
        local dirname_file=$(dirname "$file")
        
        # Vérifier les caractères d'encodage coréens mal formés
        if [[ "$basename_file" =~ .*[ë][¸][\"]*.*|.*[ì][•][„]*.*|.*[í][‹][€]*.*|.*[î][ï]*.* ]]; then
            echo "ENCODING_ISSUE:FILE:$file" >> "$output_file"
            log "${YELLOW}⚠️  Fichier problématique: $file${NC}"
            ((issues_found++))
        fi
        
        # Vérifier le répertoire parent
        if [[ "$dirname_file" =~ .*[ë][¸][\"]*.*|.*[ì][•][„]*.*|.*[í][‹][€]*.*|.*[î][ï]*.* ]]; then
            echo "ENCODING_ISSUE:DIR:$dirname_file" >> "$output_file"
            log "${YELLOW}⚠️  Répertoire problématique: $dirname_file${NC}"
            ((issues_found++))
        fi
        
    done < <(find "$target_path" -type f -print0)
    
    # Chercher spécifiquement les répertoires avec des problèmes d'encodage
    while IFS= read -r -d '' dir; do
        local basename_dir=$(basename "$dir")
        
        if [[ "$basename_dir" =~ .*[ë][¸][\"]*.*|.*[ì][•][„]*.*|.*[í][‹][€]*.*|.*[î][ï]*.* ]]; then
            echo "ENCODING_ISSUE:DIR:$dir" >> "$output_file"
            log "${YELLOW}⚠️  Répertoire problématique: $dir${NC}"
            ((issues_found++))
        fi
    done < <(find "$target_path" -type d -print0)
    
    echo "" >> "$output_file"
    echo "# Total des problèmes trouvés: $issues_found" >> "$output_file"
    
    if [ "$issues_found" -gt 0 ]; then
        log "${RED}❌ $issues_found problèmes d'encodage détectés${NC}"
        log "${BLUE}📋 Rapport sauvegardé dans: $output_file${NC}"
        
        # Créer un rapport résumé
        echo ""
        log "${YELLOW}📊 Résumé des problèmes:${NC}"
        grep "ENCODING_ISSUE:DIR:" "$output_file" | sort | uniq | while read -r line; do
            dir_path=$(echo "$line" | cut -d':' -f3-)
            log "   📁 Répertoire: $(basename "$dir_path")"
        done
        
        grep "ENCODING_ISSUE:FILE:" "$output_file" | wc -l | while read -r count; do
            if [ "$count" -gt 0 ]; then
                log "   📄 $count fichiers affectés"
            fi
        done
        
        return 1
    else
        log "${GREEN}✅ Aucun problème d'encodage détecté${NC}"
        return 0
    fi
}

# Test d'un fichier spécifique pour songrec
test_songrec_compatibility() {
    local file_path="$1"
    
    if [ ! -f "$file_path" ]; then
        log "${RED}❌ Fichier introuvable: $file_path${NC}"
        return 1
    fi
    
    log "${BLUE}🎵 Test de compatibilité songrec pour: $(basename "$file_path")${NC}"
    
    # Vérifier que le répertoire parent n'a pas de caractères problématiques
    local parent_dir=$(dirname "$file_path")
    local parent_basename=$(basename "$parent_dir")
    
    if [[ "$parent_basename" =~ .*[ë][¸][\"]*.*|.*[ì][•][„]*.*|.*[í][‹][€]*.*|.*[î][ï]*.* ]]; then
        log "${RED}❌ Répertoire parent incompatible: $parent_dir${NC}"
        log "${YELLOW}💡 Solution: Utilisez fix_encoding_issues.sh pour corriger${NC}"
        return 1
    fi
    
    # Vérifier le nom de fichier lui-même
    local file_basename=$(basename "$file_path")
    if [[ "$file_basename" =~ .*[ë][¸][\"]*.*|.*[ì][•][„]*.*|.*[í][‹][€]*.*|.*[î][ï]*.* ]]; then
        log "${RED}❌ Nom de fichier incompatible: $file_basename${NC}"
        log "${YELLOW}💡 Solution: Renommez le fichier manuellement${NC}"
        return 1
    fi
    
    log "${GREEN}✅ Fichier compatible avec songrec${NC}"
    return 0
}

# Fonction principale
main() {
    local target_path="${1:-/mnt/mybook/itunes/Music}"
    local action="${2:-detect}"
    local output_file="${3:-encoding_issues_$(date +%Y%m%d_%H%M%S).txt}"
    
    case "$action" in
        "detect")
            detect_encoding_issues "$target_path" "$output_file"
            ;;
        "test")
            if [ -z "$3" ]; then
                echo "Usage: $0 path test fichier_audio.mp3"
                exit 1
            fi
            test_songrec_compatibility "$3"
            ;;
        *)
            echo "Usage: $0 [chemin] [detect|test] [fichier_ou_rapport]"
            echo ""
            echo "Exemples:"
            echo "  $0 /mnt/mybook/itunes/Music detect"
            echo "  $0 /mnt/mybook/itunes/Music test /path/to/audio.mp3"
            exit 1
            ;;
    esac
}

main "$@"