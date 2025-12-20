#!/bin/bash
# Interface graphique simple pour gérer les tâches cron

# Fonction pour afficher le crontab actuel
show_crontab() {
    crontab -l 2>/dev/null | zenity --text-info \
        --title="Crontab actuel" \
        --width=800 --height=600 \
        --editable \
        --filename=/dev/stdin \
        > /tmp/crontab_new.txt
    
    if [ $? -eq 0 ]; then
        # L'utilisateur a sauvegardé
        if zenity --question --text="Voulez-vous appliquer ces modifications ?" --title="Confirmer"; then
            crontab /tmp/crontab_new.txt
            zenity --info --text="✅ Crontab mis à jour avec succès !" --title="Succès"
        fi
    fi
    rm -f /tmp/crontab_new.txt
}

# Fonction pour ajouter la tâche 2 étoiles
add_2stars_hourly() {
    CRON_LINE="0 * * * * /home/paulceline/bin/audio/auto_cleanup_2_stars.sh >> /home/paulceline/logs/plex_ratings/auto_cleanup.log 2>&1"
    
    # Vérifier si déjà présente
    if crontab -l 2>/dev/null | grep -q "auto_cleanup_2_stars.sh"; then
        zenity --warning --text="⚠️  Cette tâche existe déjà dans votre crontab" --title="Déjà présente"
        return
    fi
    
    # Ajouter la ligne
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    zenity --info --text="✅ Tâche ajoutée !\n\nNettoyage auto des 2 étoiles : TOUTES LES HEURES" --title="Succès"
}

# Fonction pour supprimer la tâche 2 étoiles
remove_2stars() {
    if ! crontab -l 2>/dev/null | grep -q "auto_cleanup_2_stars.sh"; then
        zenity --warning --text="⚠️  Cette tâche n'existe pas dans votre crontab" --title="Non trouvée"
        return
    fi
    
    if zenity --question --text="Voulez-vous vraiment supprimer la tâche de nettoyage 2 étoiles ?" --title="Confirmer"; then
        crontab -l 2>/dev/null | grep -v "auto_cleanup_2_stars.sh" | crontab -
        zenity --info --text="✅ Tâche supprimée avec succès" --title="Succès"
    fi
}

# Fonction pour voir les logs
view_logs() {
    LOG_FILE="/home/paulceline/logs/plex_ratings/auto_cleanup.log"
    
    if [ ! -f "$LOG_FILE" ]; then
        zenity --warning --text="⚠️  Aucun log trouvé\n\nFichier: $LOG_FILE" --title="Pas de logs"
        return
    fi
    
    tail -n 500 "$LOG_FILE" | zenity --text-info \
        --title="Logs du nettoyage auto (500 dernières lignes)" \
        --width=900 --height=700 \
        --filename=/dev/stdin
}

# Menu principal
while true; do
    CHOICE=$(zenity --list \
        --title="🎵 Gestionnaire Cron - Plex Ratings" \
        --text="Choisissez une action :" \
        --column="Option" --column="Description" \
        --width=600 --height=400 \
        "1" "📝 Voir/Éditer tout le crontab" \
        "2" "➕ Ajouter nettoyage 2⭐ (toutes les heures)" \
        "3" "❌ Supprimer nettoyage 2⭐" \
        "4" "📋 Voir les logs du nettoyage auto" \
        "5" "🚪 Quitter")
    
    case $CHOICE in
        "1")
            show_crontab
            ;;
        "2")
            add_2stars_hourly
            ;;
        "3")
            remove_2stars
            ;;
        "4")
            view_logs
            ;;
        "5"|"")
            exit 0
            ;;
    esac
done
