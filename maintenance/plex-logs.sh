#!/bin/bash
# Script pour consulter facilement les logs Plex
# Usage: ./plex-logs.sh [ratings|daily] [nombre]

LOG_TYPE=${1:-both}
COUNT=${2:-5}

echo "📋 LOGS PLEX - Derniers $COUNT fichiers"
echo "======================================"

if [ "$LOG_TYPE" = "ratings" ] || [ "$LOG_TYPE" = "both" ]; then
    echo ""
    echo "🎵 PLEX RATINGS:"
    ls -lt ~/.plex/logs/plex_ratings/ | head -n $((COUNT + 1)) | tail -n $COUNT
fi

if [ "$LOG_TYPE" = "daily" ] || [ "$LOG_TYPE" = "both" ]; then
    echo ""
    echo "📅 PLEX DAILY:"
    ls -lt ~/.plex/logs/plex_daily/ | head -n $((COUNT + 1)) | tail -n $COUNT
fi

echo ""
echo "💡 Commandes utiles:"
echo "   cat ~/plex-logs/plex_ratings/[fichier.log]  # Lire un log ratings"
echo "   cat ~/plex-logs/plex_daily/[fichier.log]    # Lire un log daily"
echo "   ./plex-logs.sh ratings 10                   # 10 derniers logs ratings"
echo "   ./plex-logs.sh daily 10                     # 10 derniers logs daily"