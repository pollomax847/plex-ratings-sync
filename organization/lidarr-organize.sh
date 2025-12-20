#!/bin/bash
# Script d'organisation pour Lidarr - Version corrigée et simplifiée

set -euo pipefail

SOURCE_DIR="/mnt/mybook/Musiques/Non_identifiés"
DEST_BASE="/mnt/mybook/Musiques/Organisé_Lidarr"
LOG_FILE="$HOME/lidarr_organization_$(date +%Y%m%d_%H%M%S).log"
BATCH_SIZE=100
DRY_RUN=false
CLEAN_DUPLICATES=false
VERBOSE=false

# Statistiques
TOTAL_FILES=0
PROCESSED_FILES=0
ORGANIZED_FILES=0
FAILED_FILES=0
DUPLICATES_FOUND=0

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions de log
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Nettoyage pour Lidarr
sanitize_lidarr() {
    local name="$1"
    echo "$name" | sed '
        s/[<>:"|?*]//g
        s/\//⧸/g
        s/\\/∖/g
        s/&/and/g
        s/'"'"'/'"'"'/g
        s/^[[:space:]]*//
        s/[[:space:]]*$//
        s/[[:space:]]\+/ /g
        s/\.*$//
    ' | cut -c1-180
}

# Extraction de métadonnées depuis le nom de fichier
get_metadata_from_filename() {
    local file="$1"
    local basename=$(basename "$file")
    basename="${basename%.*}"
    
    local artist="" title="" album="" year=""
    
    # Pattern: "Artist - Year - Title [Album]"
    if [[ "$basename" =~ ^(.+)\ -\ ([0-9]{4})\ -\ (.+)\ \[(.+)\]$ ]]; then
        artist="${BASH_REMATCH[1]}"
        year="${BASH_REMATCH[2]}"
        title="${BASH_REMATCH[3]}"
        album="${BASH_REMATCH[4]}"
    elif [[ "$basename" =~ ^(.+)\ -\ ([0-9]{4})\ -\ (.+)$ ]]; then
        artist="${BASH_REMATCH[1]}"
        year="${BASH_REMATCH[2]}"
        title="${BASH_REMATCH[3]}"
    elif [[ "$basename" =~ ^(.+)\ -\ (.+)$ ]]; then
        artist="${BASH_REMATCH[1]}"
        title="${BASH_REMATCH[2]}"
    else
        # Fallback: utiliser le nom de fichier comme titre
        title="$basename"
        artist="Unknown Artist"
    fi
    
    # Nettoyer et normaliser
    artist=$(sanitize_lidarr "$artist")
    title=$(sanitize_lidarr "$title")
    album=$(sanitize_lidarr "$album")
    
    if [ -z "$album" ]; then
        album="Unknown Album"
    fi
    
    if [ -z "$artist" ]; then
        artist="Unknown Artist"
    fi
    
    if [ -z "$title" ]; then
        title=$(basename "$file" .${file##*.})
        title=$(sanitize_lidarr "$title")
    fi
    
    echo "$artist|$year|$title|$album"
}

# Calcul du checksum pour détecter les doublons
get_checksum() {
    local file="$1"
    md5sum "$file" 2>/dev/null | cut -d' ' -f1 || echo "no_checksum"
}

# Traitement d'un fichier
process_file() {
    local file="$1"
    
    if [ ! -f "$file" ]; then
        warning "Fichier introuvable: $file"
        return 1
    fi
    
    # Vérifier l'intégrité basique
    local file_ext="${file##*.}"
    if ! [[ "$file_ext" =~ ^(mp3|flac|m4a|ogg|wav)$ ]]; then
        warning "Extension non supportée: $file"
        return 1
    fi
    
    # Extraire les métadonnées
    local metadata=$(get_metadata_from_filename "$file")
    IFS='|' read -r artist year title album <<< "$metadata"
    
    if [ "$VERBOSE" = true ]; then
        log "Traitement: $file"
        log "  Artist: $artist"
        log "  Album: $album ($year)"
        log "  Title: $title"
    fi
    
    # Construire la destination Lidarr: Artist/Album (Year)/Title.ext
    local dest_dir="$DEST_BASE/$artist"
    if [ -n "$year" ] && [ "$year" != "empty" ]; then
        dest_dir="$dest_dir/$album ($year)"
    else
        dest_dir="$dest_dir/$album"
    fi
    
    local dest_file="$dest_dir/$title.$file_ext"
    
    # Gestion des doublons
    if [ -f "$dest_file" ]; then
        if [ "$CLEAN_DUPLICATES" = true ]; then
            local orig_checksum=$(get_checksum "$file")
            local dest_checksum=$(get_checksum "$dest_file")
            
            if [ "$orig_checksum" = "$dest_checksum" ]; then
                warning "Doublon détecté et supprimé: $file"
                [ "$DRY_RUN" = false ] && rm "$file"
                ((DUPLICATES_FOUND++))
                return 0
            fi
        fi
        
        # Fichier différent, ajouter un suffixe
        local counter=1
        local base_name="$title"
        while [ -f "$dest_dir/${base_name}_${counter}.$file_ext" ]; do
            ((counter++))
        done
        dest_file="$dest_dir/${base_name}_${counter}.$file_ext"
    fi
    
    # Effectuer le déplacement
    if [ "$DRY_RUN" = true ]; then
        log "DRY-RUN: $file → $dest_file"
    else
        mkdir -p "$dest_dir"
        if mv "$file" "$dest_file" 2>/dev/null; then
            [ "$VERBOSE" = true ] && success "Organisé: $dest_file"
            ((ORGANIZED_FILES++))
        else
            error "Échec du déplacement: $file → $dest_file"
            ((FAILED_FILES++))
            return 1
        fi
    fi
    
    return 0
}

# Nettoyage à la fin
cleanup() {
    log "📊 Organisation terminée"
    log "📁 Fichiers traités: $PROCESSED_FILES / $TOTAL_FILES"
    log "✅ Fichiers organisés: $ORGANIZED_FILES"
    log "❌ Échecs: $FAILED_FILES"
    log "🔄 Doublons trouvés: $DUPLICATES_FOUND"
    log "📝 Log complet: $LOG_FILE"
}
trap cleanup EXIT

# Fonction principale
main() {
    log "🎵 Début de l'organisation pour Lidarr"
    log "📂 Source: $SOURCE_DIR"
    log "📁 Destination: $DEST_BASE"
    
    if [ ! -d "$SOURCE_DIR" ]; then
        error "Répertoire source inexistant: $SOURCE_DIR"
        exit 1
    fi
    
    mkdir -p "$DEST_BASE"
    
    # Compter les fichiers
    log "📊 Comptage des fichiers audio..."
    TOTAL_FILES=$(find "$SOURCE_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) | wc -l)
    log "📈 Fichiers à traiter: $TOTAL_FILES"
    
    if [ $TOTAL_FILES -eq 0 ]; then
        warning "Aucun fichier audio trouvé"
        exit 0
    fi
    
    # Traitement avec tableau pour éviter le subshell
    log "🔄 Collecte des fichiers..."
    local all_files=()
    while IFS= read -r -d '' file; do
        all_files+=("$file")
    done < <(find "$SOURCE_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) -print0)
    
    log "🔄 Début du traitement de ${#all_files[@]} fichiers..."
    
    for file in "${all_files[@]}"; do
        ((PROCESSED_FILES++))
        process_file "$file" || true
        
        # Afficher le progrès
        if [ $((PROCESSED_FILES % 100)) -eq 0 ]; then
            local progress=$((PROCESSED_FILES * 100 / TOTAL_FILES))
            log "Progression: $PROCESSED_FILES/$TOTAL_FILES ($progress%)"
        fi
    done
    
    success "✅ Organisation Lidarr terminée !"
}

# Gestion des arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true; shift ;;
        -v|--verbose)
            VERBOSE=true; shift ;;
        --clean-duplicates)
            CLEAN_DUPLICATES=true; shift ;;
        --batch-size)
            BATCH_SIZE="$2"; shift 2 ;;
        --source)
            SOURCE_DIR="$2"; shift 2 ;;
        --dest)
            DEST_BASE="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $(basename "$0") [options]

Organisation des fichiers audio pour Lidarr avec structure:
  Artist/Album (Year)/Title.ext

Options:
  -n, --dry-run              Simulation sans déplacement réel
  -v, --verbose              Mode verbeux
  --clean-duplicates         Supprimer les doublons automatiquement
  --batch-size NUMBER        Taille des lots (défaut: 100)
  --source PATH              Répertoire source
  --dest PATH                Répertoire de destination
  -h, --help                 Afficher cette aide

Exemples:
  $(basename "$0") --dry-run --verbose
  $(basename "$0") --clean-duplicates
EOF
            exit 0 ;;
        *)
            error "Argument inconnu: $1"
            exit 1 ;;
    esac
done

# Lancer le traitement
main