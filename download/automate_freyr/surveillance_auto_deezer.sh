# Script de surveillance automatique (tourne en arrière-plan)
#!/bin/bash

INTERVAL=3600  # 1 heure en secondes
LOG_FILE="$HOME/deezer_monitor.log"

echo "🔄 Démarrage de la surveillance automatique des playlists..." | tee -a "$LOG_FILE"
echo "Intervalle: $INTERVAL secondes ($(($INTERVAL/60)) minutes)" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "PID: $$" | tee -a "$LOG_FILE"
echo | tee -a "$LOG_FILE"

while true; do
    echo "$(date): Vérification des playlists..." >> "$LOG_FILE"
    
    # Vérifier toutes les playlists
    ~/surveille_liste_deezer.sh >> "$LOG_FILE" 2>&1
    
    # Si des changements sont détectés, envoyer une notification (optionnel)
    if grep -q "PLAYLIST.*MISE À JOUR" "$LOG_FILE" 2>/dev/null; then
        echo "🔔 NOTIFICATION: Nouveaux titres détectés !" | tee -a "$LOG_FILE"
        # Tu peux ajouter ici une notification desktop ou email
        # notify-send "Deezer Monitor" "Nouveaux titres dans tes playlists !" 2>/dev/null || true
    fi
    
    echo "$(date): Prochaine vérification dans $(($INTERVAL/60)) minutes" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    
    sleep $INTERVAL
done
