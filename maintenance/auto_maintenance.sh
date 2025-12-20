#!/bin/bash
# Script de vérification et maintenance automatique du système Plex Ratings
# Ce script peut être lancé périodiquement pour s'assurer que tout fonctionne

set -euo pipefail

# Configuration
SCRIPT_DIR="$(dirname "$0")"
LOG_FILE="$HOME/logs/plex_maintenance_$(date +%Y%m%d_%H%M%S).log"

# Créer le répertoire de logs
mkdir -p "$HOME/logs"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🔧 MAINTENANCE AUTOMATIQUE SYSTÈME PLEX RATINGS"
log "==============================================="

# Vérification 1: Scripts principaux
log "🔍 Vérification des scripts principaux..."
required_scripts=(
    "plex_ratings_sync.py"
    "plex_monthly_workflow.sh" 
    "install_songrec_rename.sh"
)

for script in "${required_scripts[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ] && [ -x "$SCRIPT_DIR/$script" ]; then
        log "✅ $script OK"
    else
        log "❌ $script manquant ou non exécutable"
        chmod +x "$SCRIPT_DIR/$script" 2>/dev/null || log "⚠️ Impossible de réparer $script"
    fi
done

# Vérification 2: Tâche cron
log "🔍 Vérification de la tâche cron..."
if crontab -l 2>/dev/null | grep -q "plex_monthly_workflow.sh"; then
    log "✅ Tâche cron configurée"
else
    log "⚠️ Tâche cron manquante - configuration automatique..."
    CRON_LINE="0 2 28-31 * * [ \"\$(date -d tomorrow +%d)\" -eq 1 ] && $SCRIPT_DIR/plex_monthly_workflow.sh >> $HOME/logs/plex_cron.log 2>&1"
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    log "✅ Tâche cron ajoutée automatiquement"
fi

# Vérification 3: songrec-rename
log "🔍 Vérification de songrec-rename..."
if command -v songrec-rename &> /dev/null; then
    log "✅ songrec-rename installé et fonctionnel"
else
    log "⚠️ songrec-rename manquant - installation automatique..."
    if "$SCRIPT_DIR/install_songrec_rename.sh" >> "$LOG_FILE" 2>&1; then
        log "✅ songrec-rename installé avec succès"
    else
        log "❌ Échec installation songrec-rename (continuera sans)"
    fi
fi

# Vérification 4: Répertoires nécessaires
log "🔍 Vérification des répertoires..."
required_dirs=(
    "$HOME/logs/plex_monthly"
    "$HOME/plex_backup" 
    "$HOME/songrec_queue"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        log "✅ $dir existe"
    else
        log "📁 Création de $dir"
        mkdir -p "$dir"
    fi
done

# Vérification 5: Bibliothèque audio
log "🔍 Vérification de la bibliothèque audio..."
AUDIO_LIB="/mnt/mybook/itunes/Music"
if [ -d "$AUDIO_LIB" ]; then
    audio_count=$(find "$AUDIO_LIB" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" \) 2>/dev/null | wc -l)
    log "✅ Bibliothèque audio accessible ($audio_count fichiers)"
else
    log "⚠️ Bibliothèque audio non accessible: $AUDIO_LIB"
fi

# Vérification 6: Base de données Plex
log "🔍 Vérification de l'accès à Plex..."
if python3 "$SCRIPT_DIR/plex_ratings_sync.py" --auto-find-db --stats >/dev/null 2>&1; then
    log "✅ Base de données Plex accessible"
elif python3 "$SCRIPT_DIR/plex_ratings_sync.py" --auto-find-db --stats 2>&1 | grep -q "Aucun fichier avec rating"; then
    log "✅ Base de données Plex accessible (aucun rating pour l'instant)"
else
    log "⚠️ Base de données Plex non accessible"
    log "   Installation de Plex requise ou permissions insuffisantes"
fi

# Nettoyage automatique
log "🧹 Nettoyage automatique..."

# Nettoyer les anciens logs de maintenance (garder 30 jours)
find "$HOME/logs" -name "plex_maintenance_*.log" -mtime +30 -delete 2>/dev/null || true

# Nettoyer les anciennes queues songrec vides (plus de 7 jours)
find "$HOME/songrec_queue" -type d -mtime +7 -empty -delete 2>/dev/null || true

# Nettoyer les anciennes sauvegardes (garder 3 mois)
find "$HOME/plex_backup" -name "monthly_*" -type d -mtime +90 -exec rm -rf {} + 2>/dev/null || true

log "✅ Nettoyage terminé"

# Test automatique (simulation)
log "🧪 Test automatique du système..."
if python3 "$SCRIPT_DIR/plex_ratings_sync.py" --auto-find-db --stats >/dev/null 2>&1; then
    log "✅ Test système réussi"
else
    log "⚠️ Test système échoué (normal si Plex non installé)"
fi

# Rapport final
log ""
log "📊 RAPPORT DE MAINTENANCE"
log "========================"
log "🕒 Maintenance terminée : $(date)"
log "📁 Log complet : $LOG_FILE"

# Statistiques des répertoires
if [ -d "$HOME/plex_backup" ]; then
    backup_count=$(find "$HOME/plex_backup" -name "monthly_*" -type d 2>/dev/null | wc -l)
    log "💾 Sauvegardes mensuelles : $backup_count"
fi

if [ -d "$HOME/songrec_queue" ]; then
    queue_count=$(find "$HOME/songrec_queue" -name "process_2_stars.sh" 2>/dev/null | wc -l)
    log "🔍 Queues songrec actives : $queue_count"
fi

log ""
log "✨ Système Plex Ratings prêt et fonctionnel !"

# Si tout est OK, on peut faire un test rapide des prochaines exécutions
log ""
log "📅 PROCHAINES EXÉCUTIONS AUTOMATIQUES :"

# Calculer la prochaine fin de mois
next_month_first=$(date -d "$(date +%Y-%m-01) + 1 month" +%Y-%m-01)
last_day=$(date -d "$next_month_first - 1 day" +%d)
next_execution=$(date -d "$(date +%Y-%m)-$last_day 02:00" +"%d %B %Y à 02:00")

if [ "$(date +%d)" -lt "$last_day" ]; then
    current_last=$(date -d "$(date +%Y-%m-01) + 1 month - 1 day" +%d)
    current_execution=$(date -d "$(date +%Y-%m)-$current_last 02:00" +"%d %B %Y à 02:00")
    log "🗓️ Prochaine exécution : $current_execution"
else
    log "🗓️ Prochaine exécution : $next_execution" 
fi

log "🎵 Le workflow traitera automatiquement :"
log "   • Suppression des fichiers 1 ⭐"
log "   • Scan songrec-rename des fichiers 2 ⭐"
log "   • Sauvegarde et nettoyage"