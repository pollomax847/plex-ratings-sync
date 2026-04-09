#!/bin/bash
# Démonstration de la notification de résumé complète
# Montre une seule notification avec toutes les statistiques

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Charger le système de notifications
if [[ -f "$BASE_DIR/notifications/audio_notifications.sh" ]]; then
    source "$BASE_DIR/notifications/audio_notifications.sh"
    export NOTIFICATION_APP_NAME="Demo - Résumé Complet"
    export NOTIFICATION_ENABLE_DESKTOP=true
    export NOTIFICATION_ENABLE_CONSOLE=true
else
    echo "Erreur: audio_notifications.sh non trouvé"
    exit 1
fi

echo "🎯 Démonstration - Notification de Résumé Complet"
echo "==============================================="
echo

# Simulation d'un workflow complet avec statistiques
echo "🔄 Simulation d'un workflow Plex complet..."
echo "   • Fichiers supprimés (1⭐): 15"
echo "   • Fichiers scannés (2⭐): 8"
echo "   • Erreurs de traitement: 2"
echo "   • Fichiers synchronisés: 45"
echo "   • Erreurs de sync: 1"
echo "   • Durée totale: 2h 15m"
echo

# Notification de résumé complet
notify_summary "Monthly Sync" "completed" "2h 15m" "15" "8" "2" "45" "1"

echo "✅ Notification de résumé envoyée !"
echo "Vérifiez votre bureau pour voir la notification complète."
echo
echo "Au lieu de 3-4 notifications séparées, vous avez maintenant"
echo "UNE SEULE notification qui contient TOUTES les informations !"