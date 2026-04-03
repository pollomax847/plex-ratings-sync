#!/bin/bash
# Relance systemctl daemon-reload si uptime > 15 jours
UPTIME_SECONDS=$(awk '{print int($1)}' /proc/uptime)
FIFTEEN_DAYS=$((15 * 24 * 3600))  # 1296000 secondes

if [ "$UPTIME_SECONDS" -gt "$FIFTEEN_DAYS" ]; then
    systemctl --user daemon-reload
    sudo systemctl daemon-reload
    echo "$(date): daemon-reload lancé (uptime = $((UPTIME_SECONDS / 86400)) jours)" >> /home/paulceline/logs/daemon-reload.log
fi
