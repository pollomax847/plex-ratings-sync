#!/bin/bash
# Script de récupération automatique des fichiers 2 étoiles via songrec
# Utilise songrec pour identifier et retélécharger les fichiers manquants

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLEX_RATINGS_SYNC="$SCRIPT_DIR/plex_ratings_sync.py"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCÈS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

# Vérifier si songrec est installé
check_songrec() {
    if ! command -v songrec &> /dev/null; then
        error "songrec n'est pas installé. Installation..."
        pip install songrec
        if [ $? -ne 0 ]; then
            error "Impossible d'installer songrec. Veuillez l'installer manuellement."
            exit 1
        fi
    fi
    success "songrec est installé"
}

# Vérifier si ffprobe est disponible (optionnel pour la méthode songrec_queue)
check_ffprobe() {
    if ! command -v ffprobe &> /dev/null; then
        warning "ffprobe n'est pas installé. Le script utilisera uniquement la liste songrec_queue."
        return 1
    fi
    return 0
}

# Obtenir la liste des fichiers 2 étoiles
get_two_star_files() {
    log "Recherche de la liste existante des fichiers 2 étoiles..."
    
    # Chercher d'abord dans songrec_queue
    SONGREC_QUEUE_DIR="$HOME/songrec_queue"
    
    if [ -d "$SONGREC_QUEUE_DIR" ]; then
        log "Répertoire songrec_queue trouvé: $SONGREC_QUEUE_DIR"
        
        # Trouver le répertoire le plus récent
        LATEST_DIR=$(ls -td "$SONGREC_QUEUE_DIR"/20*/ | head -1)
        
        if [ -n "$LATEST_DIR" ] && [ -f "$LATEST_DIR/files_to_scan.txt" ]; then
            log "Utilisation de la liste existante: $LATEST_DIR/files_to_scan.txt"
            cat "$LATEST_DIR/files_to_scan.txt"
            return 0
        fi
    fi
    
    # Fallback: scanner les répertoires musicaux (ancienne méthode)
    log "Liste songrec_queue non trouvée, scan des répertoires musicaux..."
    
    # Pour une approche plus directe, on peut scanner les répertoires musicaux
    AUDIO_DIRS=(
        "/mnt/mybook/Musiques"
        "/mnt/mybook/itunes/Music"
        "/mnt/mybook/itunes/Downloads"
        "/home/paulceline/Musique"
    )

    TWO_STAR_FILES=()

    for dir in "${AUDIO_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            log "Scan du répertoire: $dir"
            while IFS= read -r -d '' file; do
                # Vérifier si le fichier a 2 étoiles dans ses métadonnées
                if ffprobe -v quiet -show_entries stream_tags=Rating -of csv=p=0 "$file" 2>/dev/null | grep -q "2.0"; then
                    TWO_STAR_FILES+=("$file")
                fi
            done < <(find "$dir" \( -name "*.mp3" -o -name "*.m4a" -o -name "*.flac" \) -print0)
        fi
    done

    printf '%s\n' "${TWO_STAR_FILES[@]}"
}

# Traiter un fichier avec songrec
process_file_with_songrec() {
    local file="$1"
    local filename=$(basename "$file")
    local dirname=$(dirname "$file")

    log "Traitement de: $filename"

    # Créer un répertoire temporaire pour le téléchargement
    temp_dir=$(mktemp -d)
    cd "$temp_dir"

    # Utiliser songrec pour identifier le fichier
    log "Identification avec songrec..."
    if songrec "$file" --output . 2>/dev/null; then
        # Chercher le fichier téléchargé
        downloaded_file=$(find . -type f \( -name "*.mp3" -o -name "*.m4a" -o -name "*.flac" \) | head -1)

        if [ -n "$downloaded_file" ] && [ -f "$downloaded_file" ]; then
            # Copier le fichier téléchargé vers l'emplacement original
            cp "$downloaded_file" "$file"
            success "Fichier récupéré: $filename"
            echo "$file" >> "$SCRIPT_DIR/recovered_files.log"
        else
            warning "Aucun fichier téléchargé trouvé pour: $filename"
        fi
    else
        error "Échec de l'identification pour: $filename"
    fi

    # Nettoyer
    cd "$SCRIPT_DIR"
    rm -rf "$temp_dir"
}

# Fonction principale
main() {
    log "=== SCRIPT DE RÉCUPÉRATION DES FICHIERS 2 ÉTOILES ==="
    log "Ce script utilise songrec pour identifier et retélécharger les fichiers perdus"

    # Vérifications préalables
    check_songrec
    
    # Vérifier ffprobe (optionnel)
    check_ffprobe

    # Obtenir la liste des fichiers 2 étoiles
    log "Recherche des fichiers 2 étoiles..."
    two_star_files=$(get_two_star_files)

    if [ -z "$two_star_files" ]; then
        warning "Aucun fichier 2 étoiles trouvé"
        exit 0
    fi

    # Convertir en array (chaque ligne est un fichier)
    mapfile -t files_array <<< "$two_star_files"

    log "Trouvé ${#files_array[@]} fichiers 2 étoiles"

    # VERSION TEST: traiter seulement les 3 premiers fichiers
    log "VERSION TEST: traitement des 3 premiers fichiers seulement"
    files_array=("${files_array[@]:0:3}")
    log "Test avec ${#files_array[@]} fichiers"

    # Traiter chaque fichier
    processed=0
    recovered=0

    for file in "${files_array[@]}"; do
        if [ -f "$file" ]; then
            ((processed++))
            log "[$processed/${#files_array[@]}] Traitement en cours..."

            # Sauvegarder le fichier original avant de le remplacer
            backup_file="${file}.backup"
            cp "$file" "$backup_file"

            process_file_with_songrec "$file"

            if [ $? -eq 0 ]; then
                ((recovered++))
            fi

            # Petite pause pour éviter de surcharger
            sleep 2
        fi
    done

    # Résumé
    log "=== RÉSULTATS ==="
    log "Fichiers traités: $processed"
    log "Fichiers récupérés: $recovered"

    if [ -f "$SCRIPT_DIR/recovered_files.log" ]; then
        log "Liste des fichiers récupérés sauvegardée dans: $SCRIPT_DIR/recovered_files.log"
    fi

    success "Script terminé!"
}

# Gestion des signaux
trap 'error "Script interrompu par l utilisateur"; exit 1' INT TERM

# Lancer le script
main "$@"
