#!/bin/bash
# Script de synchronisation QUOTIDIENNE des ratings Plex
# Exécution recommandée: chaque soir (22h00 par défaut)
# À configurer dans crontab : 0 22 * * * /home/paulceline/bin/plex-ratings-sync/plex_daily_ratings_sync.sh
#
# Différences avec le workflow mensuel:
# - Plus léger: pas de traitement SongRec
# - Plus rapide: synchronisation simple des ratings
# - Quotidien: meilleure traçabilité des changements

# Configuration
SCRIPT_DIR="$(dirname "$0")"
CONFIG_FILE="$HOME/.plex_ratings_sync.conf"
LOG_DIR="$HOME/.plex/logs/plex_ratings"

# Bibliothèques audio à vérifier (séparées par des espaces)
AUDIO_LIBRARIES="${AUDIO_LIBRARY:-/home/paulceline/Musiques}"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Créer le répertoire de logs
mkdir -p "$LOG_DIR"

# Charger la configuration si elle existe
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    # Configuration par défaut
    TARGET_RATING=1
    VERBOSE=false
fi

# Fichiers de log avec horodatage
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/daily_sync_$TIMESTAMP.log"
REPORT_FILE="$LOG_DIR/report_daily_$TIMESTAMP.json"

# Fonction de logging avec horodatage
log() {
    local level="$1"
    local message="$2"
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

# Fonction pour les actions importantes
log_action() {
    log "ACTION" "${BLUE}$1${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$1${NC}"
}

log_error() {
    log "ERROR" "${RED}$1${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}$1${NC}"
}

# ============================================
# DÉBUT DU SCRIPT
# ============================================

log_action "Début de la synchronisation quotidienne Plex Ratings"
log_action "========================================================"
log_action "Date/Heure: $(date '+%A %d %B %Y à %H:%M:%S')"
log_action "Bibliothèques: $AUDIO_LIBRARIES"
log_action "Traitement: 1⭐ → Suppression, 2⭐ → SongRec"

# ============================================
# VÉRIFICATIONS PRÉALABLES
# ============================================

log_action "Vérification des prérequis..."

# Vérifier que toutes les bibliothèques existent
for lib in $AUDIO_LIBRARIES; do
    if [ ! -d "$lib" ]; then
        log_error "Bibliothèque introuvable: $lib"
        exit 1
    fi
    log_success "Bibliothèque accessible: $lib"
done

# Vérifier que Python est disponible
if ! command -v python3 &> /dev/null; then
    log_error "Python3 n'est pas installé"
    exit 1
fi
log_success "Python3 disponible"

# Vérifier que le script de synchronisation existe
if [ ! -f "$SCRIPT_DIR/plex_ratings_sync.py" ]; then
    log_error "Script plex_ratings_sync.py non trouvé: $SCRIPT_DIR/plex_ratings_sync.py"
    exit 1
fi
log_success "Script de synchronisation trouvé"

# Trouver la base de données Plex
log_action "Recherche de la base de données Plex..."
_plex_db_candidates=(
    "/plex/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    "/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    "$HOME/.config/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
)
PLEX_DB=""
for _c in "${_plex_db_candidates[@]}"; do
    if [ -f "$_c" ]; then PLEX_DB="$_c"; break; fi
done

if [ -z "$PLEX_DB" ]; then
    log_error "Base de données Plex non trouvée dans les chemins connus"
    exit 1
fi
log_success "Base de données Plex trouvée: $PLEX_DB"

# Vérifier si Plex est en cours d'exécution, sinon le démarrer
if ! systemctl is-active --quiet snap.plexmediaserver.plexmediaserver.service; then
    log_warning "Plex n'est pas en cours d'exécution, démarrage en cours..."
    sudo snap start plexmediaserver
    sleep 10
    if ! systemctl is-active --quiet snap.plexmediaserver.plexmediaserver.service; then
        log_error "Impossible de démarrer Plex"
        exit 1
    fi
    log_success "Plex démarré avec succès"
fi

# ============================================
# SYNCHRONISATION RATINGS
# ============================================

log_action "Lancement de la synchronisation des ratings..."
echo ""

# Compter les fichiers avec ratings 1 et 2 étoiles avant traitement
BEFORE_COUNT_1=$(python3 "$SCRIPT_DIR/plex_ratings_sync.py" \
    --plex-db "$PLEX_DB" \
    --stats 2>/dev/null | grep -oP "(?<=⭐ \(1\.0\) : )\d+" || echo "0")

BEFORE_COUNT_2=$(python3 "$SCRIPT_DIR/plex_ratings_sync.py" \
    --plex-db "$PLEX_DB" \
    --stats 2>/dev/null | grep -oP "(?<=⭐⭐ \(2\.0\) : )\d+" || echo "0")

log_action "Fichiers à traiter: $BEFORE_COUNT_1 avec 1⭐ (suppression), $BEFORE_COUNT_2 avec 2⭐ (songrec)"

# Exécuter la synchronisation (traite les 1⭐ et 2⭐ automatiquement)
python3 "$SCRIPT_DIR/plex_ratings_sync.py" \
    --plex-db "$PLEX_DB" \
    --delete \
    ${VERBOSE:+--verbose} \
    2>&1 | tee -a "$LOG_FILE"

SYNC_EXIT=$?

# Vérifier le résultat
if [ $SYNC_EXIT -eq 0 ]; then
    log_success "Synchronisation terminée avec succès"
else
    log_error "Erreur lors de la synchronisation (code: $SYNC_EXIT)"
fi

# ============================================
# SYNCHRONISATION VERS MÉTADONNÉES ID3
# ============================================

log_action "Synchronisation des ratings vers métadonnées ID3..."

# Arrêter Plex pour accéder à la base de données
log_action "Arrêt temporaire de Plex pour accès base de données..."
if sudo snap stop plexmediaserver >/dev/null 2>&1; then
    log_success "Plex arrêté temporairement"
    PLEX_WAS_RUNNING=true
else
    log_warning "Plex était déjà arrêté"
    PLEX_WAS_RUNNING=false
fi

# Attendre que Plex se ferme complètement
sleep 3

# Créer un fichier temporaire avec les fichiers 3-5 étoiles
TEMP_RATING_FILE="$LOG_DIR/temp_ratings_sync_$TIMESTAMP.json"

# Extraire les fichiers avec ratings 3-5 étoiles
python3 -c "
import sqlite3
import json
import sys

try:
    # Connexion à la base Plex
    conn = sqlite3.connect('$PLEX_DB')
    cursor = conn.cursor()
    
    # Récupérer les fichiers avec ratings 3-5 étoiles
    cursor.execute('''
        SELECT mp.file, mt.title, ar.title as artist, al.title as album, mt.user_thumb_rating
        FROM media_items mt
        JOIN media_parts mp ON mt.id = mp.media_item_id
        JOIN library_sections ls ON mt.library_section_id = ls.id
        LEFT JOIN albums al ON mt.album_id = al.id
        LEFT JOIN artists ar ON al.artist_id = ar.id
        WHERE ls.section_type = 8
        AND mt.user_thumb_rating IN (3.0, 4.0, 5.0)
        AND mp.file IS NOT NULL
    ''')
    
    files_to_sync = []
    for row in cursor.fetchall():
        files_to_sync.append({
            'file_path': row[0],
            'title': row[1] or 'Unknown',
            'artist': row[2] or 'Unknown Artist',
            'album': row[3] or 'Unknown Album',
            'rating': row[4]
        })
    
    conn.close()
    
    # Sauvegarder dans le fichier temporaire
    with open('$TEMP_RATING_FILE', 'w', encoding='utf-8') as f:
        json.dump(files_to_sync, f, indent=2, ensure_ascii=False)
    
    print(f'✅ {len(files_to_sync)} fichiers avec ratings 3-5⭐ à synchroniser')
    
except Exception as e:
    print(f'❌ Erreur lors de l\'extraction: {e}')
    sys.exit(1)
" >> "$LOG_FILE" 2>&1

if [ -f "$TEMP_RATING_FILE" ]; then
    # Vérifier que mutagen est installé
    if python3 -c "import mutagen" &>/dev/null; then
        log_success "Mutagen disponible pour la synchronisation ID3"
        
        # Lancer la synchronisation ID3
        if python3 "$SCRIPT_DIR/sync_ratings_to_id3.py" "$TEMP_RATING_FILE" >> "$LOG_FILE" 2>&1; then
            log_success "Synchronisation ID3 terminée avec succès"
            
            # Compter les fichiers traités
            ID3_SYNCED=$(grep -c "✅.*rating.*écrit:" "$LOG_FILE" 2>/dev/null || echo "0")
            ID3_ERRORS=$(grep -c "❌ Erreur.*:" "$LOG_FILE" 2>/dev/null || echo "0")
            
            log_success "📊 ID3 - Synchronisés: $ID3_SYNCED, Erreurs: $ID3_ERRORS"
        else
            log_warning "Échec de la synchronisation ID3 (continuer le workflow)"
        fi
    else
        log_warning "Mutagen non installé - synchronisation ID3 ignorée"
    fi
    
    # Nettoyer le fichier temporaire
    rm -f "$TEMP_RATING_FILE"
else
    log_warning "Aucun fichier à synchroniser vers ID3"
fi

# ============================================
# STATISTIQUES ET RAPPORTS
# ============================================

log_action "Génération du rapport..."

# Compter les opérations effectuées
DELETED=$(grep -c "🗑️ Supprimé\|deleted" "$LOG_FILE" 2>/dev/null || echo "0")
SONGREC_PROCESSED=$(grep -c "🎧.*songrec\|🎵.*fichiers.*2⭐" "$LOG_FILE" 2>/dev/null || echo "0")
SONGREC_IDENTIFIED=$(grep -c "✅ Identifié" "$LOG_FILE" 2>/dev/null || echo "0")
ERRORS=$(grep -c "ERREUR\|ERROR\|❌" "$LOG_FILE" 2>/dev/null || echo "0")

log_success "Rapport généré"

# ============================================
# ARCHIVAGE DES LOGS
# ============================================

log_action "Nettoyage des anciens logs..."

# Garder seulement les 30 derniers logs quotidiens
old_logs=$(ls -t "$LOG_DIR"/daily_sync_*.log 2>/dev/null | tail -n +31)
if [ -n "$old_logs" ]; then
    echo "$old_logs" | xargs rm -f
    log_success "Anciens logs supprimés"
else
    log_success "Aucun ancien log à nettoyer"
fi

# ============================================
# RÉSUMÉ FINAL
# ============================================

echo ""
log_action "========================================================"
log_action "RÉSUMÉ DE L'EXÉCUTION"
log_action "========================================================"
log_action "Heure de début: $(head -1 "$LOG_FILE" | cut -d']' -f1 | tr -d '[')"
log_action "Heure de fin: $(date '+%Y-%m-%d %H:%M:%S')"
log_action "📊 Statistiques:"
log_action "   🗑️ Fichiers 1⭐ supprimés: $DELETED"
log_action "   🎧 Fichiers 2⭐ traités: $SONGREC_PROCESSED"
log_action "   ✅ Fichiers 2⭐ identifiés: $SONGREC_IDENTIFIED"
log_action "   ❌ Erreurs: $ERRORS"
log_action "   🗑️ Fichiers supprimés: $DELETED"
log_action "   ❌ Erreurs: $ERRORS"
log_action "   📁 Fichier log: $LOG_FILE"
log_action ""

if [ $SYNC_EXIT -eq 0 ]; then
    log_success "✅ Synchronisation quotidienne réussie!"
else
    log_error "❌ Problème détecté lors de la synchronisation"
fi

# Redémarrer Plex si on l'avait arrêté
if [ "$PLEX_WAS_RUNNING" = true ]; then
    log_action "Redémarrage de Plex..."
    if sudo snap start plexmediaserver >/dev/null 2>&1; then
        log_success "Plex redémarré"
    else
        log_error "Échec du redémarrage de Plex"
    fi
fi

log_action "========================================================"

exit $SYNC_EXIT
