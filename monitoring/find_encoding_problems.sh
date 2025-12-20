#!/bin/bash
# Script pour détecter les problèmes d'encodage dans les chemins de fichiers/dossiers
# Compatible avec songrec et autres outils audio

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

find_encoding_problems() {
    local search_path="${1:-/mnt/mybook/itunes/Music}"
    local report_file="${2:-$HOME/encoding_problems_report.txt}"
    
    log "${BLUE}🔍 Recherche des problèmes d'encodage dans: $search_path${NC}"
    
    # Créer le rapport
    cat > "$report_file" << EOF
RAPPORT DES PROBLÈMES D'ENCODAGE
===============================
Date: $(date)
Répertoire analysé: $search_path

PROBLÈMES DÉTECTÉS:
EOF
    
    local problems_found=0
    
    # Rechercher les caractères problématiques dans les noms
    log "${YELLOW}📋 Analyse en cours...${NC}"
    
    # Caractères coréens mal encodés
    find "$search_path" -type d \( -name "*ë*" -o -name "*ì*" -o -name "*í*" -o -name "*î*" -o -name "*ï*" \) 2>/dev/null | while read -r problem_dir; do
        echo "DOSSIER: $problem_dir" >> "$report_file"
        echo "  Type: Caractères coréens mal encodés" >> "$report_file"
        echo "  Suggestion: $(basename "$problem_dir" | tr -cd '[:alnum:][:space:]()._-' | sed 's/  */ /g' | sed 's/^ *//;s/ *$//')" >> "$report_file"
        echo "" >> "$report_file"
        ((problems_found++))
        log "${RED}❌ Problème: $problem_dir${NC}"
    done
    
    # Caractères non-ASCII dans les noms
    find "$search_path" -type f -name "*[éèêëàáâäôöùúûü]*" 2>/dev/null | head -20 | while read -r problem_file; do
        echo "FICHIER: $problem_file" >> "$report_file"
        echo "  Type: Accents/caractères spéciaux" >> "$report_file"
        echo "" >> "$report_file"
        ((problems_found++))
    done
    
    # Noms avec caractères de contrôle ou invisibles
    find "$search_path" -name "*[[:cntrl:]]*" 2>/dev/null | while read -r control_file; do
        echo "FICHIER: $control_file" >> "$report_file"
        echo "  Type: Caractères de contrôle" >> "$report_file"
        echo "" >> "$report_file"
        ((problems_found++))
    done
    
    # Compléter le rapport
    cat >> "$report_file" << EOF

RÉSUMÉ:
- Total de problèmes détectés: Voir ci-dessus
- Rapport sauvé dans: $report_file

ACTIONS RECOMMANDÉES:
1. Exécuter: ./fix_encoding_issues.sh "$search_path" scan
2. Si OK, exécuter: ./fix_encoding_issues.sh "$search_path" fix
3. Tester songrec après correction

COMMANDES UTILES:
- Voir ce rapport: cat "$report_file"
- Corriger automatiquement: ./fix_encoding_issues.sh "$search_path" fix
- Tester un répertoire: songrec-rename "/chemin/vers/fichier.mp3"
EOF
    
    log "${GREEN}✅ Analyse terminée${NC}"
    log "${CYAN}📄 Rapport sauvé: $report_file${NC}"
    
    # Afficher le résumé
    if [ -s "$report_file" ]; then
        log "${YELLOW}📊 Résumé des problèmes:${NC}"
        grep -E "^(DOSSIER|FICHIER):" "$report_file" | wc -l | xargs -I {} log "   {} éléments avec problèmes d'encodage"
        
        # Afficher les 5 premiers problèmes
        log "${YELLOW}🔍 Premiers problèmes détectés:${NC}"
        grep -E "^(DOSSIER|FICHIER):" "$report_file" | head -5 | while read -r line; do
            log "   ${RED}→${NC} $line"
        done
    else
        log "${GREEN}✅ Aucun problème d'encodage détecté!${NC}"
    fi
    
    return 0
}

# Test spécifique pour songrec
test_songrec_compatibility() {
    local test_path="$1"
    
    if [ ! -d "$test_path" ]; then
        log "${RED}❌ Répertoire introuvable: $test_path${NC}"
        return 1
    fi
    
    log "${BLUE}🧪 Test de compatibilité songrec pour: $test_path${NC}"
    
    # Chercher des fichiers audio dans le répertoire
    local audio_files=($(find "$test_path" -type f \( -name "*.mp3" -o -name "*.m4a" -o -name "*.flac" \) | head -3))
    
    if [ ${#audio_files[@]} -eq 0 ]; then
        log "${YELLOW}⚠️  Aucun fichier audio trouvé dans $test_path${NC}"
        return 1
    fi
    
    for audio_file in "${audio_files[@]}"; do
        log "${CYAN}🔍 Test: $(basename "$audio_file")${NC}"
        
        # Vérifier le nom du fichier
        if echo "$audio_file" | grep -qE '[ëìíîï]'; then
            log "${RED}❌ Caractères problématiques dans: $audio_file${NC}"
        else
            log "${GREEN}✅ Nom de fichier OK${NC}"
        fi
        
        # Tester songrec si disponible
        if command -v songrec-rename &> /dev/null; then
            log "${CYAN}🎵 Test songrec-rename...${NC}"
            
            # Test en mode dry-run (si l'option existe)
            timeout 10s songrec-rename --help 2>/dev/null | grep -q "dry-run" && dry_option="--dry-run" || dry_option=""
            
            if timeout 10s songrec-rename $dry_option "$audio_file" >/dev/null 2>&1; then
                log "${GREEN}✅ songrec-rename compatible${NC}"
            else
                log "${RED}❌ songrec-rename échoue sur ce fichier${NC}"
                log "   Problème probable: nom de fichier/chemin avec caractères spéciaux"
            fi
        else
            log "${YELLOW}⚠️  songrec-rename non installé${NC}"
        fi
        
        break  # Tester seulement le premier fichier
    done
}

main() {
    local action="${1:-scan}"
    local target_path="${2:-/mnt/mybook/itunes/Music}"
    
    case "$action" in
        "scan")
            find_encoding_problems "$target_path"
            ;;
        "test")
            test_songrec_compatibility "$target_path"
            ;;
        "both")
            find_encoding_problems "$target_path"
            test_songrec_compatibility "$target_path"
            ;;
        *)
            echo "Usage: $0 [scan|test|both] [chemin]"
            echo ""
            echo "Exemples:"
            echo "  $0 scan                                    # Scan du répertoire par défaut"
            echo "  $0 scan /mnt/mybook/itunes/Music          # Scan d'un répertoire spécifique"
            echo "  $0 test /mnt/mybook/itunes/Music/Artiste  # Test songrec sur un répertoire"
            echo "  $0 both /mnt/mybook/itunes/Music          # Scan + test"
            echo ""
            echo "Répertoire par défaut: /mnt/mybook/itunes/Music"
            exit 1
            ;;
    esac
}

main "$@"
