#!/bin/bash

SCRIPT_DIR="$HOME/bin/audio/automate_freyr"
SCRIPT="$SCRIPT_DIR/surveille_auto_deezer.sh"
LOG_FILE="$SCRIPT_DIR/deezer_monitor.log"

case "$1" in
    start)
        echo "🚀 Démarrage de la surveillance automatique Deezer..."
        
        # Vérifier si cron est disponible
        if ! command -v crontab &> /dev/null; then
            echo "❌ Cron n'est pas installé. Installation..."
            sudo apt update && sudo apt install -y cron
        fi
        
        # Ajouter la tâche cron (toutes les 4 heures)
        (crontab -l 2>/dev/null; echo "0 */4 * * * $SCRIPT >> $LOG_FILE 2>&1") | crontab -
        
        echo "✅ Surveillance programmée toutes les 4 heures"
        echo "📝 Logs: $LOG_FILE"
        ;;
        
    stop)
        echo "⏹️ Arrêt de la surveillance automatique..."
        crontab -l 2>/dev/null | grep -v "surveille_auto_deezer.sh" | crontab -
        echo "✅ Surveillance arrêtée"
        ;;
        
    status)
        if crontab -l 2>/dev/null | grep -q "surveille_auto_deezer.sh"; then
            echo "✅ Surveillance ACTIVE (toutes les 4 heures)"
        else
            echo "❌ Surveillance INACTIVE"
        fi
        ;;
        
    log)
        if [ -f "$LOG_FILE" ]; then
            echo "📝 Dernières lignes du log:"
            tail -20 "$LOG_FILE"
        else
            echo "❌ Aucun log trouvé"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|status|log}"
        echo "  start  - Démarrer la surveillance automatique"
        echo "  stop   - Arrêter la surveillance"
        echo "  status - Vérifier le statut"
        echo "  log    - Afficher les logs"
        ;;
esac
