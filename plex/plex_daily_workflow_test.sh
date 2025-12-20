#!/bin/bash
# Script quotidien de gestion des ratings Plex avec workflows spécialisés
# - 1 étoile : suppression définitive
# - 2 étoiles : scan avec songrec-rename pour identification/correction
# Exécution automatique : quotidiennement à 02h00

# Configuration
SCRIPT_DIR="$(dirname "$0")"
AUDIO_LIBRARY="/mnt/mybook/itunes/Music"
LOG_DIR="$HOME/logs/plex_daily"
BACKUP_DIR="$HOME/plex_backup"
SONGREC_QUEUE_DIR="$HOME/songrec_queue"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Créer les répertoires nécessaires
mkdir -p "$LOG_DIR" "$BACKUP_DIR" "$SONGREC_QUEUE_DIR"

# Fichiers de log avec horodatage
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/daily_sync_$TIMESTAMP.log"

# Fonction de logging
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Variables pour notifications
WORKFLOW_START_TIME=$(date +%s)
TOTAL_DELETED=0
TOTAL_SONGREC_PROCESSED=0
TOTAL_SONGREC_ERRORS=0
TOTAL_RATINGS_SYNCED=0
TOTAL_RATINGS_ERRORS=0

# Début du traitement
log "${BLUE}🎵 TRAITEMENT MENSUEL DES RATINGS PLEX${NC}"
log "=============================================="
log "📅 Date: $(date '+%d %B %Y à %H:%M')"
log "📁 Bibliothèque: $AUDIO_LIBRARY"
log ""

# Vérifier les prérequis
log "${YELLOW}🔍 Vérification des prérequis...${NC}"

# Vérifier l'accès à la bibliothèque
if [ ! -d "$AUDIO_LIBRARY" ]; then
    log "${RED}❌ ERREUR: Bibliothèque audio introuvable: $AUDIO_LIBRARY${NC}"
    exit 1
fi

# Vérifier l'accès à la base Plex
PLEX_DB=$(python3 "$SCRIPT_DIR/plex_ratings_sync.py" --auto-find-db --stats 2>/dev/null | head -1 || echo "")
if [ -z "$PLEX_DB" ]; then
    log "${RED}❌ ERREUR: Base de données Plex introuvable${NC}"
    exit 1
fi

log "${GREEN}✅ Prérequis OK${NC}"

# Créer un répertoire de sauvegarde mensuel
MONTHLY_BACKUP="$BACKUP_DIR/monthly_$(date +%Y%m)"
mkdir -p "$MONTHLY_BACKUP"
log "💾 Sauvegarde mensuelle: $MONTHLY_BACKUP"

# ================================================================
# ÉTAPE 1: ANALYSER LES RATINGS ACTUELS
# ================================================================
log ""
log "${BLUE}📊 ÉTAPE 1: Analyse des ratings actuels${NC}"
log "========================================"

# Obtenir les statistiques détaillées
/home/paulceline/bin/audio/.venv/bin/python "$SCRIPT_DIR/plex_ratings_sync.py" --auto-find-db --stats >> "$LOG_FILE" 2>&1

# Extraire les fichiers par rating pour traitement (albums ET pistes)
log "🔍 Extraction des ratings d'albums et de pistes..."

# Créer des listes temporaires
TEMP_DIR="/tmp/plex_ratings_$$"
mkdir -p "$TEMP_DIR"

# NOUVELLE APPROCHE: Utiliser le gestionnaire d'albums pour une analyse complète
log "📀 Analyse des albums avec ratings..."
/home/paulceline/bin/audio/.venv/bin/python "$SCRIPT_DIR/../utils/album_ratings_manager.py" "$PLEX_DB" "$TEMP_DIR" >> "$LOG_FILE" 2>&1

# Vérifier que l'analyse a réussi
if [ ! -f "$TEMP_DIR/ratings_stats.json" ]; then
    log "${YELLOW}⚠️ Fallback: Analyse classique des pistes uniquement${NC}"
    
    # Fallback vers l'ancienne méthode si le nouveau script échoue
    /home/paulceline/bin/audio/.venv/bin/python -c "
import sqlite3
import json

# Chemin direct vers la base Plex snap
plex_db = '/var/snap/plexmediaserver/common/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db'

try:
    conn = sqlite3.connect(plex_db)
    cursor = conn.cursor()

    query = '''
    SELECT 
        mi.title as track_title,
        mis.rating as user_rating,
        mis.view_count as play_count,
        mp.file as file_path,
        parent_mi.title as album_title,
        grandparent_mi.title as artist_name
    FROM metadata_items mi
    LEFT JOIN media_items media ON mi.id = media.metadata_item_id
    LEFT JOIN media_parts mp ON media.id = mp.media_item_id
    LEFT JOIN metadata_items parent_mi ON mi.parent_id = parent_mi.id
    LEFT JOIN metadata_items grandparent_mi ON parent_mi.parent_id = grandparent_mi.id
    LEFT JOIN metadata_item_settings mis ON mi.guid = mis.guid
    WHERE mi.metadata_type = 10
    AND mp.file IS NOT NULL
    AND mis.rating IS NOT NULL
    '''

    cursor.execute(query)
    rows = cursor.fetchall()

    files_1_star = []
    files_2_star = []
    files_sync_rating = []

    for row in rows:
        track_title, user_rating, play_count, file_path, album_title, artist_name = row
        
        final_rating = user_rating
        if final_rating:
            if final_rating > 5:
                final_rating = final_rating / 2
            
            file_info = {
                'file_path': file_path,
                'rating': final_rating,
                'play_count': play_count or 0,
                'track_title': track_title or 'Unknown',
                'album_title': album_title or 'Unknown Album',
                'artist_name': artist_name or 'Unknown Artist'
            }
            
            if final_rating == 1.0:
                files_1_star.append(file_info)
            elif final_rating == 2.0:
                files_2_star.append(file_info)
            elif final_rating in [3.0, 4.0, 5.0]:
                files_sync_rating.append(file_info)

    # Sauvegarder les listes
    with open('$TEMP_DIR/files_1_star.json', 'w') as f:
        json.dump(files_1_star, f, indent=2)
        
    with open('$TEMP_DIR/files_2_star.json', 'w') as f:
        json.dump(files_2_star, f, indent=2)

    with open('$TEMP_DIR/files_sync_rating.json', 'w') as f:
        json.dump(files_sync_rating, f, indent=2)

    print(f'✅ Trouvé {len(files_1_star)} fichiers avec 1 étoile')
    print(f'✅ Trouvé {len(files_2_star)} fichiers avec 2 étoiles')
    print(f'✅ Trouvé {len(files_sync_rating)} fichiers avec 3-5 étoiles à synchroniser')

    conn.close()
except Exception as e:
    print(f'❌ Erreur: {e}')
    exit(1)
" >> "$LOG_FILE" 2>&1
fi

# Lire les résultats (priorité aux nouveaux fichiers avec gestion d'albums)
if [ -f "$TEMP_DIR/ratings_stats.json" ]; then
    log "${GREEN}✅ Analyse albums + pistes terminée${NC}"
    
    # Lire les statistiques détaillées
    ALBUMS_1_STAR=$(jq -r '.albums_1_star' "$TEMP_DIR/ratings_stats.json")
    ALBUMS_2_STAR=$(jq -r '.albums_2_star' "$TEMP_DIR/ratings_stats.json")
    FILES_FROM_ALBUMS_1_STAR=$(jq -r '.files_from_albums_1_star' "$TEMP_DIR/ratings_stats.json")
    FILES_FROM_ALBUMS_2_STAR=$(jq -r '.files_from_albums_2_star' "$TEMP_DIR/ratings_stats.json")
    FILES_FROM_TRACKS_1_STAR=$(jq -r '.files_from_tracks_1_star' "$TEMP_DIR/ratings_stats.json")
    FILES_FROM_TRACKS_2_STAR=$(jq -r '.files_from_tracks_2_star' "$TEMP_DIR/ratings_stats.json")
    
    COUNT_1_STAR=$(jq -r '.files_1_star_total' "$TEMP_DIR/ratings_stats.json")
    COUNT_2_STAR=$(jq -r '.files_2_star_total' "$TEMP_DIR/ratings_stats.json")
    COUNT_SYNC_RATING=$(jq -r '.files_sync_rating_total' "$TEMP_DIR/ratings_stats.json")
    
    log "📊 Analyse détaillée:"
    log "   📀 Albums 1⭐: $ALBUMS_1_STAR ($FILES_FROM_ALBUMS_1_STAR fichiers)"
    log "   📀 Albums 2⭐: $ALBUMS_2_STAR ($FILES_FROM_ALBUMS_2_STAR fichiers)"
    log "   🎵 Pistes seules 1⭐: $FILES_FROM_TRACKS_1_STAR"
    log "   🎵 Pistes seules 2⭐: $FILES_FROM_TRACKS_2_STAR"
    
    # Notification de démarrage
    "$SCRIPT_DIR/plex_notifications.sh" workflow_started \
        "$COUNT_1_STAR" "$COUNT_2_STAR" "$COUNT_SYNC_RATING" \
        "$ALBUMS_1_STAR" "$ALBUMS_2_STAR"
    
else
    log "${YELLOW}⚠️ Utilisation de l'analyse classique (pistes uniquement)${NC}"
    
    # Lire les résultats de l'ancienne méthode
    if [ -f "$TEMP_DIR/files_1_star.json" ]; then
        COUNT_1_STAR=$(jq length "$TEMP_DIR/files_1_star.json")
    else
        COUNT_1_STAR=0
    fi

    if [ -f "$TEMP_DIR/files_2_star.json" ]; then
        COUNT_2_STAR=$(jq length "$TEMP_DIR/files_2_star.json")
    else
        COUNT_2_STAR=0
    fi
    
    # Valeurs par défaut pour compatibilité
    ALBUMS_1_STAR=0
    ALBUMS_2_STAR=0
    
    # Notification de démarrage (mode fallback)
    "$SCRIPT_DIR/plex_notifications.sh" workflow_started \
        "$COUNT_1_STAR" "$COUNT_2_STAR" "$COUNT_SYNC_RATING" \
        "$ALBUMS_1_STAR" "$ALBUMS_2_STAR"

fi

log "📊 Résumé de l'analyse:"
log "   🗑️ Fichiers à supprimer (1 ⭐): $COUNT_1_STAR"
log "   🔍 Fichiers à scanner (2 ⭐): $COUNT_2_STAR"
log "   🎵 Fichiers à synchroniser (3-5 ⭐): $COUNT_SYNC_RATING"

# ================================================================
# ÉTAPE 2: TRAITEMENT DES FICHIERS 1 ÉTOILE (SUPPRESSION)
# ================================================================
if [ "$COUNT_1_STAR" -gt 0 ]; then
    log ""
    log "${RED}🗑️ ÉTAPE 2: Suppression des fichiers 1 étoile${NC}"
    log "============================================="
    
    log "⚠️ Suppression de $COUNT_1_STAR fichiers avec 1 étoile..."
    
    # Lancer la suppression avec sauvegarde
    python3 "$SCRIPT_DIR/plex_ratings_sync.py" \
        --auto-find-db \
        --rating 1 \
        --delete \
        --backup "$MONTHLY_BACKUP/deleted_1_star" \
        --verbose >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "${GREEN}✅ Suppression terminée avec succès${NC}"
        TOTAL_DELETED=$COUNT_1_STAR
        
        # Notification suppression
        "$SCRIPT_DIR/plex_notifications.sh" files_deleted "$COUNT_1_STAR" "Albums: ${ALBUMS_1_STAR:-0}"
    else
        log "${RED}❌ Erreur lors de la suppression${NC}"
        "$SCRIPT_DIR/plex_notifications.sh" critical_error "Suppression" "Échec de la suppression des fichiers 1 étoile"
    fi
else
    log ""
    log "${GREEN}✅ ÉTAPE 2: Aucun fichier 1 étoile à supprimer${NC}"
fi

# ================================================================
# ÉTAPE 2.5: VÉRIFICATION ET CORRECTION DES PROBLÈMES D'ENCODAGE
# ================================================================
log ""
log "${YELLOW}🔍 ÉTAPE 2.5: Vérification des problèmes d'encodage${NC}"
log "=================================================="

# Vérifier et corriger les problèmes d'encodage avant songrec
ENCODING_SCRIPT="$SCRIPT_DIR/find_encoding_problems.sh"
if [ -x "$ENCODING_SCRIPT" ]; then
    log "🔍 Recherche des problèmes d'encodage..."
    
    # Test rapide pour voir s'il y a des problèmes
    if ! "$ENCODING_SCRIPT" test "$MUSIC_ROOT" >/dev/null 2>&1; then
        log "${YELLOW}⚠️  Problèmes d'encodage détectés${NC}"
        
        # Correction automatique
        FIX_SCRIPT="$SCRIPT_DIR/fix_encoding_issues.sh"
        if [ -x "$FIX_SCRIPT" ]; then
            log "${BLUE}🔧 Correction automatique en cours...${NC}"
            "$FIX_SCRIPT" "$MUSIC_ROOT" fix
            log "${GREEN}✅ Correction des problèmes d'encodage terminée${NC}"
        else
            log "${RED}❌ Script de correction introuvable: $FIX_SCRIPT${NC}"
        fi
    else
        log "${GREEN}✅ Aucun problème d'encodage détecté${NC}"
    fi
else
    log "${YELLOW}⚠️  Script de vérification d'encodage introuvable: $ENCODING_SCRIPT${NC}"
fi

# ================================================================
# ÉTAPE 3: TRAITEMENT DES FICHIERS 2 ÉTOILES (SONGREC-RENAME)
# ================================================================
if [ "$COUNT_2_STAR" -gt 0 ]; then
    log ""
    log "${YELLOW}🔍 ÉTAPE 3: Préparation scan songrec-rename (2 étoiles)${NC}"
    log "=================================================="
    
    # Créer le répertoire de queue pour cette session
    SESSION_QUEUE="$SONGREC_QUEUE_DIR/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$SESSION_QUEUE"
    
    log "📁 Répertoire de queue: $SESSION_QUEUE"
    
    # Préparer le script de traitement songrec
    SONGREC_SCRIPT="$SESSION_QUEUE/process_2_stars.sh"
    
    cat > "$SONGREC_SCRIPT" << 'EOF'
#!/bin/bash
# Script de traitement automatique des fichiers 2 étoiles avec songrec-rename
# Généré automatiquement

QUEUE_DIR="$(dirname "$0")"
LOG_FILE="$QUEUE_DIR/songrec_processing.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🎵 Début du traitement songrec-rename"
log "===================================="

# Vérifier que songrec-rename est installé
if ! command -v songrec-rename &> /dev/null; then
    log "❌ ERREUR: songrec-rename non trouvé"
    log "   Installation : cargo install songrec-rename"
    exit 1
fi

# Traiter chaque fichier dans la liste
processed=0
errors=0

while IFS= read -r file_path; do
    if [ -f "$file_path" ]; then
        log "🔍 Scan: $(basename "$file_path")"
        
        # Lancer songrec-rename
        if songrec-rename "$file_path" >> "$LOG_FILE" 2>&1; then
            log "✅ Succès: $(basename "$file_path")"
            ((processed++))
        else
            log "❌ Échec: $(basename "$file_path")"
            ((errors++))
        fi
    else
        log "⚠️ Fichier introuvable: $file_path"
        ((errors++))
    fi
done < "$QUEUE_DIR/files_to_scan.txt"

log "📊 Traitement terminé:"
log "   ✅ Traités: $processed"
log "   ❌ Erreurs: $errors"
EOF

    chmod +x "$SONGREC_SCRIPT"
    
    # Créer la liste des fichiers à traiter
    jq -r '.[].file_path' "$TEMP_DIR/files_2_star.json" > "$SESSION_QUEUE/files_to_scan.txt"
    
    # Créer un rapport détaillé
    jq '.' "$TEMP_DIR/files_2_star.json" > "$SESSION_QUEUE/files_details.json"
    
    log "📝 Fichiers préparés pour songrec-rename:"
    log "   📁 Queue: $SESSION_QUEUE"
    log "   📋 Liste: $SESSION_QUEUE/files_to_scan.txt"
    log "   🔧 Script: $SESSION_QUEUE/process_2_stars.sh"
    
    # VÉRIFICATION D'ENCODAGE AVANT SONGREC
    log ""
    log "${BLUE}🔍 ÉTAPE 3.1: Vérification des problèmes d'encodage${NC}"
    log "================================================"
    
    # Détecter les problèmes d'encodage dans la bibliothèque
    ENCODING_REPORT="$SESSION_QUEUE/encoding_issues.txt"
    if "$SCRIPT_DIR/detect_encoding_problems.sh" "$AUDIO_LIBRARY" detect "$ENCODING_REPORT" >> "$LOG_FILE" 2>&1; then
        log "${GREEN}✅ Aucun problème d'encodage détecté${NC}"
    else
        log "${YELLOW}⚠️ Problèmes d'encodage détectés${NC}"
        log "   📋 Rapport: $ENCODING_REPORT"
        
        # Proposer la correction automatique
        log "${BLUE}🔧 Correction automatique des problèmes d'encodage...${NC}"
        if "$SCRIPT_DIR/fix_encoding_issues.sh" "$AUDIO_LIBRARY" fix >> "$LOG_FILE" 2>&1; then
            log "${GREEN}✅ Correction d'encodage réussie${NC}"
        else
            log "${RED}❌ Échec de la correction d'encodage${NC}"
            log "   ⚠️ Le traitement songrec risque d'échouer"
        fi
    fi
    
    # TRAITEMENT AUTOMATIQUE des fichiers 2 étoiles
    log ""
    log "${BLUE}🚀 Lancement automatique du scan songrec-rename...${NC}"
    
    # Vérifier que songrec-rename est disponible
    if command -v songrec-rename &> /dev/null; then
        log "✅ songrec-rename trouvé, traitement automatique en cours..."
        
        # Lancer le script de traitement automatiquement
        cd "$SESSION_QUEUE"
        if ./process_2_stars.sh >> "$LOG_FILE" 2>&1; then
            log "${GREEN}✅ Traitement songrec-rename terminé avec succès${NC}"
            
            # Compter les fichiers traités
            processed_count=$(grep -c "✅ Succès:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0")
            error_count=$(grep -c "❌ Échec:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0")
            
            TOTAL_SONGREC_PROCESSED=$processed_count
            TOTAL_SONGREC_ERRORS=$error_count
            
            log "📊 Résultats songrec-rename:"
            log "   ✅ Fichiers traités: $processed_count"
            log "   ❌ Erreurs: $error_count"
            
            # NOUVEAU : Supprimer automatiquement les ratings 2 étoiles après songrec réussi
            if [ "$processed_count" -gt 0 ]; then
                log ""
                log "${BLUE}🧹 ÉTAPE 3.2: Suppression automatique des ratings 2 étoiles${NC}"
                log "====================================================="
                log "Les fichiers ont été traités avec songrec-rename, suppression des ratings 2⭐..."
                
                if "$SCRIPT_DIR/remove_2_stars_after_songrec.sh" >> "$LOG_FILE" 2>&1; then
                    log "${GREEN}✅ Ratings 2 étoiles supprimés automatiquement${NC}"
                    log "   Les fichiers traités n'ont plus de ratings 2⭐ dans Plex"
                else
                    log "${YELLOW}⚠️ Erreur lors de la suppression automatique des ratings 2⭐${NC}"
                    log "   Vous pouvez les supprimer manuellement avec: $SCRIPT_DIR/remove_2_stars_after_songrec.sh"
                fi
            fi
            
            # Notification songrec
            "$SCRIPT_DIR/plex_notifications.sh" songrec_completed \
                "$processed_count" "$error_count" \
                "${ALBUMS_2_STAR:-0}" "${FILES_FROM_TRACKS_2_STAR:-0}"
        else
            log "${YELLOW}⚠️ Erreur lors du traitement songrec-rename${NC}"
            log "   Les fichiers restent en queue pour traitement manuel si nécessaire"
            TOTAL_SONGREC_ERRORS=$COUNT_2_STAR
            
            # Notification d'erreur songrec
            "$SCRIPT_DIR/plex_notifications.sh" critical_error "Songrec" "Échec du traitement songrec-rename"
        fi
    else
        log "${YELLOW}⚠️ songrec-rename non installé${NC}"
        log "   Installez avec: ./install_songrec_rename.sh"
        log "   Les fichiers 2 ⭐ restent en queue pour traitement ultérieur"
        
        # Notification songrec non installé
        "$SCRIPT_DIR/plex_notifications.sh" critical_error "Songrec" "songrec-rename non installé"
    fi
    
else
    log ""
    log "${GREEN}✅ ÉTAPE 3: Aucun fichier 2 étoiles à scanner${NC}"
fi

# ================================================================
# ÉTAPE 4: GÉNÉRATION DU RAPPORT QUOTIDIEN
# ================================================================
log ""
log "${BLUE}📊 ÉTAPE 4: Génération du rapport quotidien${NC}"
log "=============================================="

if [ -f "$SCRIPT_DIR/generate_monthly_report.py" ]; then
    log "📈 Génération du rapport mensuel..."

    if python3 "$SCRIPT_DIR/generate_monthly_report.py" >> "$LOG_FILE" 2>&1; then
        log "${GREEN}✅ Rapport mensuel généré avec succès${NC}"

        # Trouver le dernier rapport généré
        LATEST_REPORT=$(ls -t "$SCRIPT_DIR"/monthly_report_*.json 2>/dev/null | head -1)
        if [ -n "$LATEST_REPORT" ]; then
            log "📄 Rapport: $LATEST_REPORT"

            # Notification rapport généré
            "$SCRIPT_DIR/plex_notifications.sh" monthly_report_generated "$LATEST_REPORT"
        fi
    else
        log "${YELLOW}⚠️ Erreur lors de la génération du rapport mensuel${NC}"
        "$SCRIPT_DIR/plex_notifications.sh" minor_error "Rapport mensuel" "Échec de génération"
    fi
else
    log "${YELLOW}⚠️ Script de rapport mensuel introuvable${NC}"
fi

# ================================================================
# ÉTAPE 5: ANALYSE DES DOUBLONS
# ================================================================
log ""
log "${BLUE}🔍 ÉTAPE 5: Analyse des doublons${NC}"
log "==================================="

if [ -f "$SCRIPT_DIR/duplicate_detector.py" ]; then
    log "🔍 Analyse des doublons en cours..."

    if python3 "$SCRIPT_DIR/duplicate_detector.py" >> "$LOG_FILE" 2>&1; then
        log "${GREEN}✅ Analyse des doublons terminée${NC}"

        # Trouver le dernier rapport de doublons
        LATEST_DUPLICATES=$(ls -t "$SCRIPT_DIR"/duplicate_analysis_*.json 2>/dev/null | head -1)
        if [ -n "$LATEST_DUPLICATES" ]; then
            log "📄 Rapport doublons: $LATEST_DUPLICATES"

            # Extraire quelques statistiques du rapport JSON
            if command -v jq &> /dev/null; then
                EXACT_DUPS=$(jq -r '.statistics.total_exact_duplicate_groups // 0' "$LATEST_DUPLICATES" 2>/dev/null || echo "0")
                SIMILAR_DUPS=$(jq -r '.statistics.total_similar_groups // 0' "$LATEST_DUPLICATES" 2>/dev/null || echo "0")
                FILE_DUPS=$(jq -r '.statistics.total_file_duplicate_groups // 0' "$LATEST_DUPLICATES" 2>/dev/null || echo "0")

                log "📊 Résumé doublons:"
                log "   🎯 Doublons exacts: $EXACT_DUPS groupes"
                log "   🔍 Titres similaires: $SIMILAR_DUPS groupes"
                log "   📁 Fichiers identiques: $FILE_DUPS groupes"

                # Notification analyse doublons
                "$SCRIPT_DIR/plex_notifications.sh" duplicates_analysis_completed \
                    "$EXACT_DUPS" "$SIMILAR_DUPS" "$FILE_DUPS"
            else
                # Notification sans statistiques détaillées
                "$SCRIPT_DIR/plex_notifications.sh" duplicates_analysis_completed "N/A" "N/A" "N/A"
            fi
        fi
    else
        log "${YELLOW}⚠️ Erreur lors de l'analyse des doublons${NC}"
        "$SCRIPT_DIR/plex_notifications.sh" minor_error "Analyse doublons" "Échec de l'analyse"
    fi
else
    log "${YELLOW}⚠️ Script d'analyse des doublons introuvable${NC}"
fi

# ================================================================
# ÉTAPE 6: NETTOYAGE ET FINALISATION
# ================================================================
log ""
log "${BLUE}🧹 ÉTAPE 6: Nettoyage et finalisation${NC}"
log "====================================="

# Nettoyer les fichiers temporaires
rm -rf "$TEMP_DIR"
log "🧹 Fichiers temporaires supprimés"

# Nettoyage des anciens logs (garder 6 mois)
find "$LOG_DIR" -name "monthly_sync_*.log" -mtime +180 -delete 2>/dev/null || true
log "🧹 Anciens logs nettoyés (>6 mois)"

# Nettoyage des anciennes sauvegardes (garder 3 mois)
find "$BACKUP_DIR" -name "monthly_*" -type d -mtime +90 -exec rm -rf {} + 2>/dev/null || true
log "🧹 Anciennes sauvegardes nettoyées (>3 mois)"

# Optionnel: Déclencher un scan de bibliothèque Plex après modifications
# Décommentez si vous avez configuré l'API Plex
# curl -X POST "http://localhost:32400/library/sections/MUSIC_SECTION_ID/refresh?X-Plex-Token=YOUR_TOKEN" 2>/dev/null || true

# ================================================================
# RÉSUMÉ FINAL
# ================================================================
log ""
log "${GREEN}🎉 TRAITEMENT MENSUEL TERMINÉ${NC}"
log "============================="

END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
log "🕒 Fin: $END_TIME"
log "📁 Log complet: $LOG_FILE"
log "💾 Sauvegardes: $MONTHLY_BACKUP"

if [ "$COUNT_2_STAR" -gt 0 ]; then
    log "🔍 Queue songrec: $SESSION_QUEUE"
fi

# Statistiques finales
log ""
log "📊 STATISTIQUES MENSUELLES:"
log "   🗑️ Fichiers supprimés (1⭐): $COUNT_1_STAR"
log "   🔍 Fichiers scannés (2⭐): $COUNT_2_STAR"

# Rapport par email (optionnel) - 100% automatique
if [ -n "${NOTIFICATION_EMAIL:-}" ] && command -v mail &> /dev/null; then
    {
        echo "Rapport automatique Plex Ratings - $(date '+%B %Y')"
        echo "================================================="
        echo
        echo "Traitement mensuel terminé automatiquement"
        echo "Date: $(date '+%d %B %Y à %H:%M')"
        echo
        echo "STATISTIQUES:"
        echo "• Fichiers supprimés (1⭐): $COUNT_1_STAR"
        echo "• Fichiers scannés songrec (2⭐): $COUNT_2_STAR"
        echo
        echo "SAUVEGARDES:"
        echo "• Répertoire: $MONTHLY_BACKUP"
        echo
        if [ "$COUNT_2_STAR" -gt 0 ] && [ -n "${SESSION_QUEUE:-}" ]; then
            echo "SONGREC-RENAME:"
            if [ -f "$SESSION_QUEUE/songrec_processing.log" ]; then
                processed_auto=$(grep -c "✅ Succès:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0")
                error_auto=$(grep -c "❌ Échec:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0")
                echo "• Fichiers traités: $processed_auto"
                echo "• Erreurs: $error_auto" 
            fi
        fi
        echo
        echo "Log complet: $LOG_FILE"
        echo "Configuration: 100% automatique, aucune intervention requise"
    } | mail -s "✅ Plex Ratings - Traitement automatique $(date '+%B %Y')" "$NOTIFICATION_EMAIL" 2>/dev/null || true
fi

# Rapport automatique dans les logs même sans email
log ""
log "${BLUE}📧 RAPPORT AUTOMATIQUE GÉNÉRÉ${NC}"
log "============================="

# Créer un résumé JSON pour les outils d'analyse
SUMMARY_FILE="$LOG_DIR/monthly_summary_$(date +%Y%m).json"
cat > "$SUMMARY_FILE" << EOF
{
  "date": "$(date -Iseconds)",
  "month": "$(date '+%Y-%m')",
  "files_deleted_1_star": $COUNT_1_STAR,
  "files_processed_2_star": $COUNT_2_STAR,
  "ratings_sync_errors": ${SYNC_RATING_ERRORS:-0},
  "backup_directory": "$MONTHLY_BACKUP",
  "log_file": "$LOG_FILE",
  "songrec_auto_processed": $([ -f "$SESSION_QUEUE/songrec_processing.log" ] && grep -c "✅ Succès:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0"),
  "songrec_auto_errors": $([ -f "$SESSION_QUEUE/songrec_processing.log" ] && grep -c "❌ Échec:" "$SESSION_QUEUE/songrec_processing.log" 2>/dev/null || echo "0"),
  "automation_level": "100% automatique + synchronisation ratings",
  "manual_intervention_required": false
}
EOF

log "📄 Résumé JSON: $SUMMARY_FILE"

# Calculer la durée totale
WORKFLOW_END_TIME=$(date +%s)
WORKFLOW_DURATION=$((WORKFLOW_END_TIME - WORKFLOW_START_TIME))
DURATION_FORMATTED=$(printf "%02d:%02d:%02d" $((WORKFLOW_DURATION/3600)) $((WORKFLOW_DURATION%3600/60)) $((WORKFLOW_DURATION%60)))

# Notification finale de résumé complet
"$SCRIPT_DIR/plex_notifications.sh" workflow_completed \
    "$TOTAL_DELETED" "$TOTAL_SONGREC_PROCESSED" "$TOTAL_SONGREC_ERRORS" \
    "$TOTAL_RATINGS_SYNCED" "$TOTAL_RATINGS_ERRORS" \
    "${ALBUMS_1_STAR:-0}" "${ALBUMS_2_STAR:-0}" "$DURATION_FORMATTED"

log ""
log "${BLUE}✨ Votre bibliothèque est maintenant synchronisée !${NC}"
log "⏱️  Durée totale: $DURATION_FORMATTED"