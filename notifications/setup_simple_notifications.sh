#!/bin/bash
# Configuration rapide du système de notifications - Version Simple
# Active les notifications desktop et console, désactive les emails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Configuration Rapide - Notifications Simples"
echo "=============================================="
echo

# Configuration recommandée
export NOTIFICATION_ENABLE_DESKTOP=true
export NOTIFICATION_ENABLE_EMAIL=false
export NOTIFICATION_ENABLE_CONSOLE=true
export NOTIFICATION_ENABLE_SOUND=true
export NOTIFICATION_APP_NAME="Plex Audio Manager"

echo "Configuration appliquée :"
echo "✅ Desktop notifications: Activées"
echo "❌ Email notifications: Désactivées (pas configuré)"
echo "✅ Console notifications: Activées"
echo "✅ Sound notifications: Activées"
echo

# Test du système
echo "🧪 Test du système..."
"$SCRIPT_DIR/audio_notifications.sh" test

echo
echo "🎉 Configuration terminée !"
echo "Utilisez maintenant vos scripts normalement."
echo "Les notifications apparaîtront dans la barre des tâches et dans la console."