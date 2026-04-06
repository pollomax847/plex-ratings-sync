#!/bin/bash
# Script complet pour synchroniser Plexamp avec les ratings Plex

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/sync_plexamp_$(date +%Y%m%d_%H%M%S).log"

# Fonction de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_FILE"
}

log "🎵 Début de la synchronisation Plexamp..."

# Étape 1: Synchroniser les ratings Plex vers les métadonnées ID3
log "📊 Étape 1: Synchronisation des ratings vers métadonnées..."
if [ -f "$SCRIPT_DIR/plex_rating_sync_complete.py" ]; then
    python3 "$SCRIPT_DIR/plex_rating_sync_complete.py" --auto-find-db >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        log "✅ Ratings synchronisés vers métadonnées"
    else
        log "⚠️ Problèmes lors de la synchronisation des ratings"
    fi
else
    log "❌ Script plex_rating_sync_complete.py introuvable"
    exit 1
fi

# Étape 2: Générer les playlists Plexamp
log "🎵 Étape 2: Génération des playlists Plexamp..."
if [ -f "$SCRIPT_DIR/generate_plexamp_playlists.sh" ]; then
    "$SCRIPT_DIR/generate_plexamp_playlists.sh" --refresh >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then
        log "✅ Playlists Plexamp générées"
    else
        log "⚠️ Problèmes lors de la génération des playlists"
    fi
else
    log "⚠️ Script generate_plexamp_playlists.sh introuvable (optionnel)"
fi

# Étape 3: Forcer le rescan Plexamp
log "🔄 Étape 3: Forçage du rescan Plexamp..."
if [ -f "$SCRIPT_DIR/force_plexamp_rescan.sh" ]; then
    "$SCRIPT_DIR/force_plexamp_rescan.sh" >> "$LOG_FILE" 2>&1
    log "✅ Rescan Plexamp déclenché"
else
    log "⚠️ Script force_plexamp_rescan.sh introuvable"
fi

# Étape 4: Notification
log "🔔 Étape 4: Envoi de notification..."
if [ -f "$SCRIPT_DIR/plex_notifications.sh" ]; then
    "$SCRIPT_DIR/plex_notifications.sh" "plexamp_sync_completed" "Synchronisation Plexamp terminée" "Ratings mis à jour, playlists régénérées, rescan déclenché" >> "$LOG_FILE" 2>&1
fi

log "🎉 Synchronisation Plexamp terminée!"
log "📋 Log complet: $LOG_FILE"
log ""
log "📋 Actions à faire:"
log "1. Ouvrez Plexamp"
log "2. Allez dans Paramètres > Bibliothèque > Rescanner"
log "3. Les nouveaux ratings et playlists devraient apparaître!"

echo ""
echo "🎵 SYNCHRONISATION PLEXAMP TERMINÉE!"
echo "📄 Log: $LOG_FILE"
echo ""
echo "🔄 À faire dans Plexamp:"
echo "   Paramètres > Bibliothèque > Rescanner la bibliothèque"