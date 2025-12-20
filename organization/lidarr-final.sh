#!/bin/bash
# Organisation pour Lidarr - Version finale et robuste

SOURCE_DIRS=("/mnt/mybook/Musiques" "/home/paulceline/Musiques" "/home/paulceline")
DEST_BASE="/mnt/mybook/Musiques"
DRY_RUN=false
VERBOSE=false

# Statistiques
PROCESSED=0
ORGANIZED=0
FAILED=0
DUPLICATES=0

# Couleurs
G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'; R='\033[0;31m'; NC='\033[0m'

log() { echo -e "${B}[$((++PROCESSED))]${NC} $1"; }
success() { echo -e "${G}✅${NC} $1"; ((ORGANIZED++)); }
error() { echo -e "${R}❌${NC} $1"; ((FAILED++)); }
warning() { echo -e "${Y}⚠️${NC} $1"; }

# Nettoyage Lidarr
sanitize() {
    echo "$1" | sed 's/[<>:"|?*]//g; s/\//⧸/g; s/\\/∖/g; s/&/and/g; s/'"'"'/'"'"'/g; s/^[[:space:]]*//; s/[[:space:]]*$//; s/[[:space:]]\+/ /g; s/\.*$//' | cut -c1-180
}

# Traitement d'un fichier
process_file() {
    local file="$1"
    
    [ ! -f "$file" ] && { error "Fichier introuvable: $file"; return 1; }
    
    local ext="${file##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')  # Conversion en minuscules
    [[ ! "$ext" =~ ^(mp3|flac|m4a|ogg|wav)$ ]] && { warning "Extension non supportée: $ext"; return 1; }
    
    # Extraction métadonnées
    local basename=$(basename "$file" ".$ext")
    local artist="" year="" title="" album=""
    
    if [[ "$basename" =~ ^(.+)\ -\ ([0-9]{4})\ -\ (.+)\ \[(.+)\]$ ]]; then
        artist="${BASH_REMATCH[1]}"
        year="${BASH_REMATCH[2]}"
        title="${BASH_REMATCH[3]}"
        album="${BASH_REMATCH[4]}"
    elif [[ "$basename" =~ ^(.+)\ -\ ([0-9]{4})\ -\ (.+)$ ]]; then
        artist="${BASH_REMATCH[1]}"
        year="${BASH_REMATCH[2]}"
        title="${BASH_REMATCH[3]}"
        album="Unknown Album"
    elif [[ "$basename" =~ ^(.+)\ -\ (.+)$ ]]; then
        artist="${BASH_REMATCH[1]}"
        title="${BASH_REMATCH[2]}"
        album="Unknown Album"
    else
        artist="Unknown Artist"
        title="$basename"
        album="Unknown Album"
    fi
    
    # Nettoyage
    artist=$(sanitize "$artist")
    title=$(sanitize "$title")
    album=$(sanitize "$album")
    
    [ -z "$artist" ] && artist="Unknown Artist"
    [ -z "$title" ] && title="$basename"
    [ -z "$album" ] && album="Unknown Album"
    
    # Structure Lidarr: Artist/Album (Year)/Title.ext
    local dest_dir="$DEST_BASE/$artist"
    if [ -n "$year" ]; then
        dest_dir="$dest_dir/$album ($year)"
    else
        dest_dir="$dest_dir/$album"
    fi
    
    local dest_file="$dest_dir/$title.$ext"
    
    # Gestion doublons
    if [ -f "$dest_file" ]; then
        local counter=1
        while [ -f "$dest_dir/${title}_${counter}.$ext" ]; do
            ((counter++))
        done
        dest_file="$dest_dir/${title}_${counter}.$ext"
        warning "Conflit de nom résolu: ${title}_${counter}.$ext"
    fi
    
    [ "$VERBOSE" = true ] && log "$(basename "$file") → $artist/$album${year:+ ($year)}/"
    
    # Action
    if [ "$DRY_RUN" = true ]; then
        echo "DRY-RUN: $dest_file"
    else
        mkdir -p "$dest_dir" || { error "Impossible de créer: $dest_dir"; return 1; }
        if mv "$file" "$dest_file" 2>/dev/null; then
            success "$(basename "$dest_file")"
        else
            error "Échec: $file → $dest_file"
            return 1
        fi
    fi
    
    return 0
}

# Fonction principale
main() {
    echo -e "${B}🎵 Organisation Lidarr${NC}"
    echo "📂 Sources: ${SOURCE_DIRS[*]}"
    echo "📁 Dest: $DEST_BASE"
    [ "$DRY_RUN" = true ] && echo -e "${Y}🧪 MODE SIMULATION${NC}"
    
    # Validation des sources
    for source in "${SOURCE_DIRS[@]}"; do
        [ ! -d "$source" ] && { error "Source inexistante: $source"; exit 1; }
    done
    
    # Comptage total des fichiers
    local total=0
    for source in "${SOURCE_DIRS[@]}"; do
        local count=$(find "$source" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) | wc -l)
        total=$((total + count))
    done
    echo "📈 Fichiers total: $total"
    
    [ "$DRY_RUN" = false ] && mkdir -p "$DEST_BASE"
    
    echo -e "${B}🔄 Traitement en cours...${NC}"
    
    # Traitement de chaque source
    for source in "${SOURCE_DIRS[@]}"; do
        echo -e "${B}📂 Traitement de: $source${NC}"
        
        while IFS= read -r -d '' file; do
            process_file "$file" 2>/dev/null || true
            [ $((PROCESSED % 500)) -eq 0 ] && echo -e "${B}Traités: $PROCESSED${NC}"
        done < <(find "$source" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) -print0)
    done
    
    # Rapport final
    echo -e "\n${G}📊 TERMINÉ${NC}"
    echo "✅ Organisés: $ORGANIZED"
    echo "❌ Échecs: $FAILED"
    echo "📁 Structure: $DEST_BASE"
}

# Arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run) DRY_RUN=true ;;
        -v|--verbose) VERBOSE=true ;;
        --source) SOURCE_DIRS=("$2"); shift ;;
        --dest) DEST_BASE="$2"; shift ;;
        -h|--help)
            echo "Usage: $(basename "$0") [options]"
            echo "  -n, --dry-run       Simulation"
            echo "  -v, --verbose       Mode verbeux"
            echo "  --source PATH       Source"
            echo "  --dest PATH         Destination"
            echo ""
            echo "Structure Lidarr: Artist/Album (Year)/Title.ext"
            exit 0 ;;
        *) echo "❌ Argument inconnu: $1"; exit 1 ;;
    esac
    shift
done

# GO!
main