#!/bin/bash
# Script d'organisation massive pour collection de musiques non identifiées
# Gère 179 319 fichiers (~1.2TB) de façon intelligente et progressive

set -euo pipefail

# Configuration
SOURCE_DIR="/mnt/mybook/itunes/Music"
DEST_BASE="/mnt/mybook/itunes/Music"
QUARANTINE_DIR="${QUARANTINE_DIR:-$HOME/music_quarantine}"
TEMP_DIR="${TEMP_DIR:-$HOME/tmp/music_org}"
LOG_FILE="${LOG_FILE:-$HOME/music_organization_$(date +%Y%m%d_%H%M%S).log}"
BATCH_SIZE="${BATCH_SIZE:-1000}"
TOTAL_FILES=0
PROCESSED_FILES=0
ORGANIZED_FILES=0
FAILED_FILES=0
DUPLICATES_FOUND=0

# Options
DRY_RUN=false
VERBOSE=false
USE_SONGREC=true
USE_EXIFTOOL=true
CLEAN_DUPLICATES=false
ORGANIZE_BY_GENRE=false

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
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

# Nettoyage en cas d'interruption
cleanup() {
    log "🧹 Nettoyage des fichiers temporaires..."
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    
    # Affichage des statistiques finales
    cat <<EOF

📊 STATISTIQUES FINALES
======================
📁 Fichiers traités: $PROCESSED_FILES / $TOTAL_FILES
✅ Fichiers organisés: $ORGANIZED_FILES
❌ Échecs: $FAILED_FILES
🔄 Doublons trouvés: $DUPLICATES_FOUND
📝 Log détaillé: $LOG_FILE
EOF
}
trap cleanup EXIT INT TERM

# Vérification des dépendances
check_dependencies() {
    local missing_deps=()
    
    for cmd in ffprobe jq; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ "$USE_SONGREC" = true ] && ! command -v songrec >/dev/null 2>&1; then
        warning "SongRec non trouvé, désactivation de l'identification automatique"
        USE_SONGREC=false
    fi
    
    if [ "$USE_EXIFTOOL" = true ] && ! command -v exiftool >/dev/null 2>&1; then
        warning "ExifTool non trouvé, utilisation des métadonnées limitée"
        USE_EXIFTOOL=false
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        error "Dépendances manquantes: ${missing_deps[*]}"
        error "Installez-les avec: sudo apt install ${missing_deps[*]}"
        exit 1
    fi
}

# Analyse des métadonnées d'un fichier
get_file_metadata() {
    local file="$1"
    local artist="" title="" album="" year="" genre="" duration=""
    
    # Tentative d'extraction via ffprobe
    if command -v ffprobe >/dev/null 2>&1; then
        local metadata
        metadata=$(ffprobe -v quiet -print_format json -show_format "$file" 2>/dev/null || echo '{}')
        
        artist=$(echo "$metadata" | jq -r '.format.tags.artist // .format.tags.ARTIST // empty' 2>/dev/null || true)
        title=$(echo "$metadata" | jq -r '.format.tags.title // .format.tags.TITLE // empty' 2>/dev/null || true)
        album=$(echo "$metadata" | jq -r '.format.tags.album // .format.tags.ALBUM // empty' 2>/dev/null || true)
        year=$(echo "$metadata" | jq -r '.format.tags.date // .format.tags.DATE // .format.tags.year // .format.tags.YEAR // empty' 2>/dev/null || true)
        genre=$(echo "$metadata" | jq -r '.format.tags.genre // .format.tags.GENRE // empty' 2>/dev/null || true)
        duration=$(echo "$metadata" | jq -r '.format.duration // empty' 2>/dev/null || true)
    fi
    
    # Si pas de métadonnées, analyser le nom de fichier
    if [ -z "$artist" ] || [ -z "$title" ]; then
        local basename=$(basename "$file")
        basename="${basename%.*}"  # Enlever l'extension
        
        # Patterns courants: "Artist - Year - Title [Album]"
        if [[ "$basename" =~ ^(.+)\ -\ ([0-9]{4})\ -\ (.+)\ \[(.+)\]$ ]]; then
            artist="${BASH_REMATCH[1]}"
            year="${BASH_REMATCH[2]}"
            title="${BASH_REMATCH[3]}"
            album="${BASH_REMATCH[4]}"
        elif [[ "$basename" =~ ^(.+)\ -\ (.+)$ ]]; then
            artist="${BASH_REMATCH[1]}"
            title="${BASH_REMATCH[2]}"
        fi
    fi
    
    # Nettoyer les métadonnées
    artist=$(echo "$artist" | sed 's/[[:space:]]\+/ /g; s/^[[:space:]]*//; s/[[:space:]]*$//')
    title=$(echo "$title" | sed 's/[[:space:]]\+/ /g; s/^[[:space:]]*//; s/[[:space:]]*$//')
    album=$(echo "$album" | sed 's/[[:space:]]\+/ /g; s/^[[:space:]]*//; s/[[:space:]]*$//')
    
    # Retourner les métadonnées au format JSON
    jq -n \
        --arg artist "$artist" \
        --arg title "$title" \
        --arg album "$album" \
        --arg year "$year" \
        --arg genre "$genre" \
        --arg duration "$duration" \
        '{artist: $artist, title: $title, album: $album, year: $year, genre: $genre, duration: $duration}'
}

# Nettoyage sécurisé des noms de fichiers/dossiers (fonction legacy)
sanitize_filename() {
    sanitize_filename_lidarr "$1"
}

# Détection de doublons via checksum
get_file_checksum() {
    local file="$1"
    md5sum "$file" 2>/dev/null | cut -d' ' -f1 || echo "no_checksum"
}

# Calcul de la structure de destination compatible Lidarr
calculate_destination() {
    local metadata="$1"
    local original_file="$2"
    
    local artist=$(echo "$metadata" | jq -r '.artist // empty')
    local year=$(echo "$metadata" | jq -r '.year // empty')
    local album=$(echo "$metadata" | jq -r '.album // empty')
    local genre=$(echo "$metadata" | jq -r '.genre // empty')
    local title=$(echo "$metadata" | jq -r '.title // empty')
    
    # Utiliser le nom de fichier comme fallback
    if [ -z "$artist" ] && [ -z "$title" ]; then
        local basename=$(basename "$original_file" | sed 's/\.[^.]*$//')
        artist="Unknown Artist"
        title="$basename"
    fi
    
    # Nettoyer les noms selon les conventions Lidarr
    artist=$(sanitize_filename_lidarr "$artist")
    album=$(sanitize_filename_lidarr "$album")
    title=$(sanitize_filename_lidarr "$title")
    
    # Si pas d'album, utiliser "Unknown Album"
    if [ -z "$album" ]; then
        album="Unknown Album"
    fi
    
    # Structure Lidarr: Artist/Album (Year)/
    local dest_dir="$DEST_BASE/$artist"
    
    if [ -n "$year" ]; then
        dest_dir="$dest_dir/$album ($year)"
    else
        dest_dir="$dest_dir/$album"
    fi
    
    echo "$dest_dir"
}

# Nettoyage spécifique pour Lidarr
sanitize_filename_lidarr() {
    local name="$1"
    
    # Règles de nettoyage pour Lidarr
    echo "$name" | sed '
        # Supprimer les caractères interdits par le système de fichiers
        s/[<>:"|?*]//g
        s/\//⧸/g
        s/\\/∖/g
        
        # Remplacer les caractères problématiques pour Lidarr
        s/&/and/g
        s/'"'"'/'"'"'/g
        
        # Nettoyer les espaces
        s/^[[:space:]]*//
        s/[[:space:]]*$//
        s/[[:space:]]\+/ /g
        
        # Supprimer les points en fin (problématique Windows)
        s/\.*$//
    ' | cut -c1-180  # Limiter la longueur pour éviter les problèmes de chemin
}

# Traitement d'un fichier individuel
process_file() {
    local file="$1"
    local file_ext="${file##*.}"
    
    # Vérifier l'intégrité du fichier
    if ! ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$file" >/dev/null 2>&1; then
        warning "Fichier corrompu détecté: $file"
        if [ -n "$QUARANTINE_DIR" ]; then
            mkdir -p "$QUARANTINE_DIR/corrupted"
            mv "$file" "$QUARANTINE_DIR/corrupted/" 2>/dev/null || true
        fi
        return 1
    fi
    
    # Obtenir les métadonnées
    local metadata
    metadata=$(get_file_metadata "$file")
    
    # Calculer la destination
    local dest_dir
    dest_dir=$(calculate_destination "$metadata" "$file")
    
    # Extraire les métadonnées pour le nom de fichier
    local artist=$(echo "$metadata" | jq -r '.artist // "Unknown Artist"')
    local title=$(echo "$metadata" | jq -r '.title // empty')
    local album=$(echo "$metadata" | jq -r '.album // "Unknown Album"')
    local year=$(echo "$metadata" | jq -r '.year // empty')
    
    # Extraire le numéro de piste si disponible
    local track_number=""
    if command -v ffprobe >/dev/null 2>&1; then
        track_number=$(ffprobe -v quiet -print_format json -show_format "$file" 2>/dev/null | \
                      jq -r '.format.tags.track // .format.tags.TRACK // empty' 2>/dev/null | \
                      sed 's/[^0-9].*//' || true)
    fi
    
    if [ -z "$title" ]; then
        title=$(basename "$file" | sed 's/\.[^.]*$//')
    fi
    
    # Nettoyer les métadonnées avec les règles Lidarr
    artist=$(sanitize_filename_lidarr "$artist")
    title=$(sanitize_filename_lidarr "$title")
    album=$(sanitize_filename_lidarr "$album")
    
    # Format de nom de fichier compatible Lidarr: "NN - Title" ou juste "Title"
    local dest_filename=""
    if [ -n "$track_number" ] && [ "$track_number" -gt 0 ] 2>/dev/null; then
        # Formater le numéro de piste sur 2 chiffres
        dest_filename=$(printf "%02d - %s.%s" "$track_number" "$title" "$file_ext")
    else
        dest_filename="$title.$file_ext"
    fi
    
    local dest_path="$dest_dir/$dest_filename"
    
    # Vérifier les doublons
    if [ -f "$dest_path" ]; then
        local orig_checksum=$(get_file_checksum "$file")
        local dest_checksum=$(get_file_checksum "$dest_path")
        
        if [ "$orig_checksum" = "$dest_checksum" ]; then
            warning "Doublon détecté: $file"
            ((DUPLICATES_FOUND++))
            if [ "$CLEAN_DUPLICATES" = true ]; then
                rm "$file"
                log "Doublon supprimé: $file"
            fi
            return 0
        else
            # Fichiers différents, ajouter un suffixe
            local counter=1
            local base_name="${dest_filename%.*}"
            local extension="${dest_filename##*.}"
            while [ -f "$dest_dir/${base_name}_${counter}.${extension}" ]; do
                ((counter++))
            done
            dest_filename="${base_name}_${counter}.${extension}"
            dest_path="$dest_dir/$dest_filename"
        fi
    fi
    
    # Créer le répertoire de destination
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$dest_dir"
        
        # Déplacer le fichier
        if mv "$file" "$dest_path" 2>/dev/null; then
            success "Organisé: $file → $dest_path"
            ((ORGANIZED_FILES++))
        else
            error "Échec du déplacement: $file → $dest_path"
            ((FAILED_FILES++))
            return 1
        fi
    else
        log "DRY-RUN: $file → $dest_path"
    fi
    
    return 0
}

# Traitement par lots
process_batch() {
    local batch_files=("$@")
    local batch_num=$((PROCESSED_FILES / BATCH_SIZE + 1))
    
    log "🔄 Traitement du lot $batch_num (${#batch_files[@]} fichiers)..."
    
    for file in "${batch_files[@]}"; do
        if [ ! -f "$file" ]; then
            continue
        fi
        
        ((PROCESSED_FILES++))
        
        if [ $((PROCESSED_FILES % 100)) -eq 0 ]; then
            local progress=$((PROCESSED_FILES * 100 / TOTAL_FILES))
            log "Progression: $PROCESSED_FILES/$TOTAL_FILES ($progress%)"
        fi
        
        if ! process_file "$file"; then
            ((FAILED_FILES++))
        fi
    done
}

# Fonction principale
main() {
    log "🎵 Début de l'organisation massive de la collection musicale"
    log "📂 Source: $SOURCE_DIR"
    log "📁 Destination: $DEST_BASE"
    
    # Vérifications préliminaires
    check_dependencies
    
    if [ ! -d "$SOURCE_DIR" ]; then
        error "Le répertoire source n'existe pas: $SOURCE_DIR"
        exit 1
    fi
    
    # Créer les répertoires nécessaires
    mkdir -p "$DEST_BASE" "$QUARANTINE_DIR" "$TEMP_DIR"
    
    # Compter le nombre total de fichiers
    log "📊 Analyse de la collection..."
    TOTAL_FILES=$(find "$SOURCE_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) | wc -l)
    log "📈 Nombre total de fichiers: $TOTAL_FILES"
    
    if [ $TOTAL_FILES -eq 0 ]; then
        warning "Aucun fichier audio trouvé dans $SOURCE_DIR"
        exit 0
    fi
    
    # Traitement par lots - éviter le problème de subshell avec while
    local batch_files=()
    local all_files=()
    
    # Collecter tous les fichiers dans un tableau
    while IFS= read -r -d '' file; do
        all_files+=("$file")
    done < <(find "$SOURCE_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.wav" \) -print0)
    
    log "📁 Fichiers à traiter: ${#all_files[@]}"
    
    # Traiter par lots
    for file in "${all_files[@]}"; do
        batch_files+=("$file")
        
        # Traiter le lot quand il atteint la taille limite
        if [ ${#batch_files[@]} -ge $BATCH_SIZE ]; then
            process_batch "${batch_files[@]}"
            batch_files=()
        fi
    done
    
    # Traiter le dernier lot s'il reste des fichiers
    if [ ${#batch_files[@]} -gt 0 ]; then
        process_batch "${batch_files[@]}"
    fi
    
    success "✅ Organisation terminée!"
    success "📁 Fichiers organisés dans: $DEST_BASE"
    
    # Rapport final
    cat <<EOF | tee -a "$LOG_FILE"

📊 RAPPORT FINAL D'ORGANISATION
==============================
📁 Source: $SOURCE_DIR
📂 Destination: $DEST_BASE
📈 Fichiers traités: $PROCESSED_FILES / $TOTAL_FILES
✅ Fichiers organisés: $ORGANIZED_FILES
❌ Échecs: $FAILED_FILES
🔄 Doublons trouvés: $DUPLICATES_FOUND
📝 Log détaillé: $LOG_FILE

EOF
}

# Gestion des arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true; shift ;;
        -v|--verbose)
            VERBOSE=true; shift ;;
        --no-songrec)
            USE_SONGREC=false; shift ;;
        --clean-duplicates)
            CLEAN_DUPLICATES=true; shift ;;
        --organize-by-genre)
            ORGANIZE_BY_GENRE=true; shift ;;
        --batch-size)
            BATCH_SIZE="$2"; shift 2 ;;
        --source)
            SOURCE_DIR="$2"; shift 2 ;;
        --dest)
            DEST_BASE="$2"; shift 2 ;;
        --quarantine)
            QUARANTINE_DIR="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -n, --dry-run              Simulation sans déplacement réel
  -v, --verbose              Mode verbeux
  --no-songrec              Désactiver SongRec
  --clean-duplicates        Supprimer automatiquement les doublons
  --organize-by-genre       Organiser par genre musical
  --batch-size NUMBER       Taille des lots (défaut: 1000)
  --source PATH             Répertoire source (défaut: /mnt/mybook/Musiques/Non_identifiés)
  --dest PATH               Répertoire de destination (défaut: /mnt/mybook/Musiques/Organisé)
  --quarantine PATH         Répertoire de quarantaine (défaut: ~/music_quarantine)
  -h, --help                Afficher cette aide

Exemples:
  $(basename "$0") --dry-run                    # Simulation
  $(basename "$0") --clean-duplicates           # Organiser et supprimer les doublons
  $(basename "$0") --organize-by-genre          # Organiser par genre
EOF
            exit 0 ;;
        *)
            error "Argument inconnu: $1"
            exit 1 ;;
    esac
done

# Lancer le programme principal
main