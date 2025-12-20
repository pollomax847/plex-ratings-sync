#!/bin/bash
# Script de récupération automatique des fichiers 2 étoiles via yt-dlp
# Utilise yt-dlp pour rechercher et retélécharger les fichiers manquants depuis YouTube

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

# Vérifier si yt-dlp est installé
check_ytdlp() {
    if ! command -v yt-dlp &> /dev/null; then
        error "yt-dlp n'est pas installé. Installation..."
        pip install yt-dlp
        if [ $? -ne 0 ]; then
            error "Impossible d'installer yt-dlp. Veuillez l'installer manuellement."
            exit 1
        fi
    fi
    success "yt-dlp est installé"
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
        
        if [ -n "$LATEST_DIR" ] && [ -f "$LATEST_DIR/files_details.json" ]; then
            log "Utilisation des métadonnées détaillées: $LATEST_DIR/files_details.json"
            # Extraire seulement les chemins des fichiers
            jq -r '.[].file_path' "$LATEST_DIR/files_details.json" 2>/dev/null || cat "$LATEST_DIR/files_to_scan.txt"
            return 0
        elif [ -n "$LATEST_DIR" ] && [ -f "$LATEST_DIR/files_to_scan.txt" ]; then
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

# Traiter un fichier avec yt-dlp
process_file_with_ytdlp() {
    local file="$1"
    local filename=$(basename "$file")
    local dirname=$(dirname "$file")

    log "Traitement de: $filename"

    # Créer un répertoire temporaire pour le téléchargement
    temp_dir=$(mktemp -d)
    cd "$temp_dir"

    # Vérifier si le fichier existe
    if [ -f "$file" ]; then
        # Fichier existe - utiliser yt-dlp pour rechercher et remplacer
        log "Fichier existe, recherche de remplacement avec yt-dlp..."
        
        # Pour les fichiers existants, on peut essayer de deviner le titre depuis le nom du fichier
        # Enlever l'extension et nettoyer le nom
        base_name=$(basename "$file" | sed 's/\.[^.]*$//')
        search_query="$base_name"
        
        log "Recherche YouTube: $search_query"
        
        if yt-dlp "ytsearch:$search_query" --extract-audio --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" --max-downloads 1 --no-playlist 2>/dev/null; then
            # Chercher le fichier téléchargé
            downloaded_file=$(find . -type f -name "*.mp3" | head -1)

            if [ -n "$downloaded_file" ] && [ -f "$downloaded_file" ]; then
                # Copier le fichier téléchargé vers l'emplacement original
                cp "$downloaded_file" "$file"
                success "Fichier remplacé: $filename"
                echo "$file" >> "$SCRIPT_DIR/recovered_files.log"
                cd "$SCRIPT_DIR"
                rm -rf "$temp_dir"
                return 0
            else
                warning "Aucun fichier téléchargé trouvé pour: $filename"
            fi
        else
            error "Échec de la recherche pour: $filename"
        fi
    else
        # Fichier n'existe pas - utiliser les métadonnées JSON
        log "Fichier manquant, recherche des métadonnées..."
        
        # Trouver le fichier de métadonnées
        SONGREC_QUEUE_DIR="$HOME/songrec_queue"
        LATEST_DIR=$(ls -td "$SONGREC_QUEUE_DIR"/20*/ | head -1)
        METADATA_FILE="$LATEST_DIR/files_details.json"
        
        if [ -f "$METADATA_FILE" ]; then
            # Utiliser grep pour trouver la ligne correspondante (plus robuste que jq avec les caractères spéciaux)
            metadata_line=$(grep -F "$file" "$METADATA_FILE")
            
            if [ -n "$metadata_line" ]; then
                # Extraire les informations avec jq sur cette ligne spécifique
                track_title=$(echo "$metadata_line" | jq -r '.track_title' 2>/dev/null)
                artist_name=$(echo "$metadata_line" | jq -r '.artist_name' 2>/dev/null)
                album_title=$(echo "$metadata_line" | jq -r '.album_title' 2>/dev/null)
                
                if [ -n "$track_title" ] && [ "$track_title" != "null" ]; then
                    log "Métadonnées trouvées - Titre: '$track_title', Artiste: '$artist_name', Album: '$album_title'"
                    
                    # Utiliser yt-dlp avec les métadonnées
                    log "Téléchargement avec yt-dlp basé sur les métadonnées..."
                    
                    # yt-dlp peut rechercher par titre et artiste
                    search_query="$artist_name - $track_title"
                    log "Recherche YouTube: $search_query"
                    
                    if yt-dlp "ytsearch:$search_query" --extract-audio --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" --max-downloads 1 --no-playlist 2>/dev/null; then
                        # Chercher le fichier téléchargé
                        downloaded_file=$(find . -type f -name "*.mp3" | head -1)

                        if [ -n "$downloaded_file" ] && [ -f "$downloaded_file" ]; then
                            # Créer le répertoire de destination s'il n'existe pas
                            mkdir -p "$dirname"
                            
                            # Copier le fichier téléchargé vers l'emplacement original
                            cp "$downloaded_file" "$file"
                            success "Fichier récupéré: $filename"
                            echo "$file" >> "$SCRIPT_DIR/recovered_files.log"
                            cd "$SCRIPT_DIR"
                            rm -rf "$temp_dir"
                            return 0
                        else
                            warning "Aucun fichier téléchargé trouvé pour: $filename"
                        fi
                    else
                        error "Échec du téléchargement pour: $filename"
                    fi
                else
                    warning "Titre non trouvé dans les métadonnées pour: $filename"
                fi
            else
                warning "Aucune métadonnée trouvée pour: $filename"
            fi
        else
            warning "Fichier de métadonnées non trouvé: $METADATA_FILE"
        fi
    fi

    # Nettoyer
    cd "$SCRIPT_DIR"
    rm -rf "$temp_dir"
    return 1
}

# Fonction principale
main() {
    log "=== SCRIPT DE RÉCUPÉRATION DES FICHIERS 2 ÉTOILES ==="
    log "Ce script utilise yt-dlp pour rechercher et retélécharger les fichiers perdus sur YouTube"

    # Vérifications préalables
    check_ytdlp
    
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

    # Charger la progression précédente
    progress_file="$SCRIPT_DIR/recovery_progress.txt"
    start_index=0
    if [ -f "$progress_file" ]; then
        start_index=$(cat "$progress_file" 2>/dev/null || echo 0)
        log "Reprise depuis l'index $start_index"
    fi

    # Traiter chaque fichier à partir de l'index sauvegardé
    processed=0
    recovered=0
    batch_size=10
    batch_count=0

    for ((i=start_index; i<${#files_array[@]}; i++)); do
        file="${files_array[$i]}"
        
        # Sauvegarder la progression
        echo "$i" > "$progress_file"
        if [ -f "$file" ]; then
            ((processed++))
            log "[$processed/${#files_array[@]}] Traitement en cours..."

            # Vérifier si le fichier a déjà été traité (présence de backup ou dans le log)
            backup_file="${file}.backup"
            if [ -f "$backup_file" ] || grep -q "^$file$" "$SCRIPT_DIR/recovered_files.log" 2>/dev/null; then
                log "Fichier déjà traité, ignoré: $(basename "$file")"
                continue
            fi

            # Sauvegarder le fichier original avant de le remplacer
            cp "$file" "$backup_file"

            process_file_with_ytdlp "$file"

            if [ $? -eq 0 ]; then
                ((recovered++))
            fi

            # Petite pause pour éviter de surcharger
            sleep 2
        else
            # Fichier n'existe pas - vérifier s'il a été récupéré depuis
            if [ -f "$file" ]; then
                log "Fichier déjà récupéré, ignoré: $(basename "$file")"
                ((processed++))
                continue
            fi
            
            # Fichier n'existe pas - c'est normal, on va le récupérer avec yt-dlp
            ((processed++))
            filename=$(basename "$file")
            log "[$processed/${#files_array[@]}] Fichier manquant, récupération avec yt-dlp: $filename"

            process_file_with_ytdlp "$file"

            if [ $? -eq 0 ]; then
                ((recovered++))
            fi

            # Pause plus longue entre les fichiers manquants
            sleep 5
        fi

        # Pause entre les lots
        ((batch_count++))
        if [ $((batch_count % batch_size)) -eq 0 ]; then
            log "Lot de $batch_size fichiers traité. Pause de 30 secondes..."
            sleep 30
        fi
    done

    # Supprimer le fichier de progression une fois terminé
    rm -f "$progress_file"

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
