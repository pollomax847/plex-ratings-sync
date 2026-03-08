#!/bin/bash
# Exemple d'intégration du système de notifications générique
# Ce script montre comment utiliser audio_notifications.sh dans vos scripts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Charger le système de notifications
if [[ -f "$SCRIPT_DIR/audio_notifications.sh" ]]; then
    source "$SCRIPT_DIR/audio_notifications.sh"
    # Configuration pour cet exemple
    export NOTIFICATION_APP_NAME="Audio Management Demo"
    export NOTIFICATION_ENABLE_CONSOLE=true
    export NOTIFICATION_ENABLE_DESKTOP=true  # Activer pour la démo
else
    echo "Erreur: audio_notifications.sh non trouvé"
    exit 1
fi

echo "=== Démonstration du système de notifications ==="
echo

# Notification de démarrage
notify_info "Demo Started" "Starting audio management demonstration"

# Simulation d'une tâche réussie
echo "🔄 Simulation d'une tâche de traitement audio..."
sleep 1
notify_success "Task Complete" "Audio file processing finished successfully"

# Simulation d'un avertissement
echo "⚠️  Simulation d'un avertissement..."
sleep 1
notify_warning "Low Disk Space" "Only 5GB remaining on audio drive"

# Simulation d'une erreur
echo "❌ Simulation d'une erreur..."
sleep 1
notify_error "Sync Failed" "Unable to connect to media server"

echo
echo "=== Test terminé ==="
echo "Vérifiez vos notifications desktop et console"
echo "Modifiez les variables d'environnement pour personnaliser:"
echo "  NOTIFICATION_ENABLE_DESKTOP=true/false"
echo "  NOTIFICATION_ENABLE_EMAIL=true/false"
echo "  NOTIFICATION_APP_NAME='Votre App'"