#!/bin/bash
# Système de notifications pour les workflows Plex
# Supporte les notifications desktop et email

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NOTIFICATION_CONFIG="$HOME/.config/plex_notifications.conf"
DEFAULT_EMAIL=""
DEFAULT_SMTP_SERVER=""
DEFAULT_ENABLE_DESKTOP=true
DEFAULT_ENABLE_EMAIL=false

# Charger la configuration
load_config() {
    if [ -f "$NOTIFICATION_CONFIG" ]; then
        source "$NOTIFICATION_CONFIG"
    else
        # Créer une configuration par défaut
        cat > "$NOTIFICATION_CONFIG" << EOF
# Configuration des notifications Plex
ENABLE_DESKTOP_NOTIFICATIONS=$DEFAULT_ENABLE_DESKTOP
ENABLE_EMAIL_NOTIFICATIONS=$DEFAULT_ENABLE_EMAIL
EMAIL_RECIPIENT="$DEFAULT_EMAIL"
SMTP_SERVER="$DEFAULT_SMTP_SERVER"
NOTIFICATION_LEVEL="info"  # debug, info, warning, error
LOG_NOTIFICATIONS=true
EOF
        echo "Configuration créée : $NOTIFICATION_CONFIG"
    fi
    
    source "$NOTIFICATION_CONFIG"
}

# Fonction pour jouer un son de notification (si disponible)
play_notification_sound() {
    local sound_type="${1:-bell}"
    
    # Essayer différents systèmes de son
    if command -v paplay &> /dev/null; then
        paplay /usr/share/sounds/freedesktop/stereo/$sound_type.oga 2>/dev/null && return 0
    fi
    
    if command -v aplay &> /dev/null; then
        aplay /usr/share/sounds/alsa/$sound_type.wav 2>/dev/null && return 0
    fi
    
    # Fallback: bell ASCII
    echo -e "\a" 2>/dev/null || true
}

# Fonction pour envoyer une notification desktop
send_desktop_notification() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"  # low, normal, critical
    local icon="${4:-audio-x-generic}"
    
    if [ "$ENABLE_DESKTOP_NOTIFICATIONS" = "true" ]; then
        # Vérifier si notify-send est disponible et si on peut envoyer des notifications
        if command -v notify-send &> /dev/null; then
            # Tester si on peut vraiment envoyer une notification (timeout court)
            if timeout 2 notify-send --help &> /dev/null; then
                notify-send \
                    --urgency="$urgency" \
                    --icon="$icon" \
                    --app-name="Plex Audio Manager" \
                    --expire-time=10000 \
                    "$title" \
                    "$message" 2>/dev/null && return 0
            fi
        fi
        
        # Fallback: notification console si desktop ne fonctionne pas
        echo -e "${BLUE}🔔 [DESKTOP] $title: $message${NC}"
    fi
}

# Fonction pour envoyer une notification email (optionnelle)
send_email_notification() {
    local subject="$1"
    local body="$2"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && [ -n "$EMAIL_RECIPIENT" ]; then
        if command -v mail &> /dev/null; then
            echo "$body" | mail -s "[$HOSTNAME] Plex Audio: $subject" "$EMAIL_RECIPIENT"
        elif command -v sendmail &> /dev/null; then
            {
                echo "Subject: [$HOSTNAME] Plex Audio: $subject"
                echo ""
                echo "$body"
            } | sendmail "$EMAIL_RECIPIENT"
        fi
    fi
}

# Notification pour suppression de fichiers 1 étoile
notify_files_deleted() {
    local count="$1"
    local details="$2"
    
    if [ "$count" -gt 0 ]; then
        local title="🗑️ Fichiers supprimés"
        local message="$count fichier(s) avec 1 étoile supprimé(s)"
        
        send_desktop_notification "$title" "$message" "normal" "user-trash-full"
        play_notification_sound "bell"
        
        if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
            send_email_notification "Suppression terminée" "Nombre de fichiers supprimés: $count\n\nDétails:\n$details"
        fi
        
        echo -e "${GREEN}✅ Notification envoyée: $count fichier(s) supprimé(s)${NC}"
    fi
}

# Notification pour traitement songrec
notify_songrec_completed() {
    local processed="$1"
    local errors="$2"
    local album_count="$3"
    local track_count="$4"
    
    local title="🔍 Songrec terminé"
    local message="Traités: $processed | Erreurs: $errors"
    local urgency="normal"
    local sound="bell"
    
    if [ "$errors" -gt 0 ]; then
        urgency="critical"
        title="⚠️ Songrec avec erreurs"
        sound="dialog-warning"
    fi
    
    send_desktop_notification "$title" "$message" "$urgency" "audio-card"
    play_notification_sound "$sound"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        local body="Traitement songrec-rename terminé:

📀 Albums traités: $album_count
🎵 Pistes individuelles: $track_count
✅ Fichiers traités: $processed
❌ Erreurs: $errors

Vérifiez les logs pour plus de détails."
        
        send_email_notification "Songrec terminé" "$body"
    fi
    
    echo -e "${BLUE}🔔 Notification envoyée: Songrec ($processed traités, $errors erreurs)${NC}"
}

# Notification pour synchronisation des ratings
notify_rating_sync_completed() {
    local synced="$1"
    local errors="$2"
    local file_count="$3"
    
    local title="🎵 Sync ratings terminé"
    local message="$synced fichiers synchronisés"
    local urgency="normal"
    
    if [ "$errors" -gt 0 ]; then
        urgency="critical"
        title="⚠️ Sync avec erreurs"
        message="$synced synchronisés, $errors erreurs"
    fi
    
    send_desktop_notification "$title" "$message" "$urgency" "audio-volume-high"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        local body="Synchronisation des ratings terminée:

📁 Fichiers traités: $file_count
✅ Synchronisés: $synced
❌ Erreurs: $errors

Les ratings ont été écrits dans les métadonnées ID3."
        
        send_email_notification "Sync ratings terminé" "$body"
    fi
    
    echo -e "${GREEN}🔔 Notification envoyée: Sync ratings ($synced synchronisés)${NC}"
}

# Notification de résumé complet du workflow
notify_workflow_completed() {
    local deleted="$1"
    local songrec_processed="$2"
    local songrec_errors="$3"
    local ratings_synced="$4"
    local ratings_errors="$5"
    local albums_1_star="$6"
    local albums_2_star="$7"
    local duration="$8"
    
    local title="🎵 Workflow Plex terminé"
    local total_processed=$((deleted + songrec_processed + ratings_synced))
    local message="$total_processed fichiers traités en $duration"
    
    # Déterminer l'urgence
    local urgency="normal"
    if [ "$songrec_errors" -gt 0 ] || [ "$ratings_errors" -gt 0 ]; then
        urgency="critical"
        title="⚠️ Workflow terminé avec erreurs"
    fi
    
    send_desktop_notification "$title" "$message" "$urgency" "multimedia-audio-player"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        local body="Workflow mensuel Plex terminé en $duration

📊 RÉSUMÉ DES ACTIONS:
═══════════════════════════

🗑️  SUPPRESSION (1⭐):
   📀 Albums: $albums_1_star
   📁 Fichiers supprimés: $deleted

🔍 SONGREC-RENAME (2⭐):
   📀 Albums: $albums_2_star  
   ✅ Fichiers traités: $songrec_processed
   ❌ Erreurs: $songrec_errors

🎵 SYNC RATINGS (3-5⭐):
   ✅ Fichiers synchronisés: $ratings_synced
   ❌ Erreurs: $ratings_errors

📈 TOTAL:
   📁 Fichiers traités: $total_processed
   ⏱️  Durée: $duration

$([ $((songrec_errors + ratings_errors)) -gt 0 ] && echo "⚠️ Des erreurs sont survenues. Vérifiez les logs pour plus de détails." || echo "✅ Workflow terminé sans erreur.")

Logs disponibles dans: ~/logs/plex_monthly/"
        
        send_email_notification "Workflow mensuel terminé" "$body"
    fi
    
    echo -e "${BLUE}📬 Notification complète envoyée: $total_processed fichiers traités${NC}"
}

# Notification d'erreur critique
notify_critical_error() {
    local error_type="$1"
    local error_message="$2"
    
    local title="❌ Erreur Plex"
    local message="$error_type: $error_message"
    
    send_desktop_notification "$title" "$message" "critical" "dialog-error"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        send_email_notification "Erreur critique" "Type: $error_type\nMessage: $error_message\n\nVérifiez les logs et la configuration."
    fi
    
    echo -e "${RED}🚨 Notification d'erreur envoyée: $error_type${NC}"
}

notify_monthly_report_generated() {
    local report_path="$1"
    
    local title="📊 Rapport mensuel généré"
    local message="Le rapport mensuel de votre bibliothèque audio a été créé avec succès.
    
📄 Fichier: $(basename "$report_path")
📁 Localisation: $(dirname "$report_path")
    
Le rapport contient des statistiques détaillées sur vos écoutes, ratings et recommandations d'amélioration."
    
    send_desktop_notification "$title" "$message" "normal" "text-x-generic"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && [ -n "$EMAIL_RECIPIENT" ]; then
        send_email_notification "$title" "$message"
    fi
}

notify_duplicates_analysis_completed() {
    local exact_duplicates="$1"
    local similar_titles="$2"
    local file_duplicates="$3"
    
    local title="🔍 Analyse des doublons terminée"
    local message="L'analyse des doublons dans votre bibliothèque est terminée.
    
📊 Résultats:
• Doublons exacts: $exact_duplicates groupes
• Titres similaires: $similar_titles groupes  
• Fichiers identiques: $file_duplicates groupes
    
Consultez le rapport détaillé pour examiner les doublons trouvés."
    
    send_desktop_notification "$title" "$message" "normal" "edit-find"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && [ -n "$EMAIL_RECIPIENT" ]; then
        send_email_notification "$title" "$message"
    fi
}

notify_minor_error() {
    local error_type="$1"
    local error_message="$2"
    
    local title="⚠️ Erreur mineure - $error_type"
    local message="Une erreur mineure s'est produite: $error_message
    
Le workflow continue normalement."
    
    send_desktop_notification "$title" "$message" "normal" "dialog-warning"
    
    # Les erreurs mineures ne génèrent pas d'email par défaut
}

# Notification de début de workflow
notify_workflow_started() {
    local files_1_star="$1"
    local files_2_star="$2"
    local files_sync="$3"
    local albums_1_star="$4"
    local albums_2_star="$5"
    
    local title="🚀 Workflow Plex démarré"
    local total_files=$((files_1_star + files_2_star + files_sync))
    local message="$total_files fichiers à traiter"
    
    send_desktop_notification "$title" "$message" "normal" "media-playlist-shuffle"
    
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        local body="Workflow mensuel Plex démarré:

📊 PLANIFICATION:
════════════════

🗑️  À supprimer (1⭐): $files_1_star fichiers ($albums_1_star albums)
🔍 Pour songrec (2⭐): $files_2_star fichiers ($albums_2_star albums)  
🎵 À synchroniser (3-5⭐): $files_sync fichiers

📁 TOTAL: $total_files fichiers

Le traitement est en cours..."
        
        send_email_notification "Workflow démarré" "$body"
    fi
    
    echo -e "${BLUE}🔔 Notification de démarrage envoyée${NC}"
}

# Test des notifications
test_notifications() {
    echo -e "${YELLOW}🧪 Test des notifications...${NC}"
    
    # Test notification desktop
    if [ "$ENABLE_DESKTOP_NOTIFICATIONS" = "true" ]; then
        echo -n "Test notification desktop... "
        if send_desktop_notification "🧪 Test Plex" "Test de notification desktop" "normal" "audio-card"; then
            echo -e "${GREEN}✅ Desktop OK${NC}"
        else
            echo -e "${RED}❌ Desktop KO (affichage console)${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ Notifications desktop désactivées${NC}"
    fi
    
    # Test son
    echo -n "Test notification sonore... "
    if play_notification_sound "bell"; then
        echo -e "${GREEN}✅ Son OK${NC}"
    else
        echo -e "${YELLOW}⚠️ Son limité (bell ASCII)${NC}"
    fi
    
    # Test email
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ]; then
        echo -n "Test notification email... "
        if send_email_notification "Test" "Test de notification email depuis le système Plex Audio Manager."; then
            echo -e "${GREEN}✅ Email OK${NC}"
        else
            echo -e "${RED}❌ Email KO${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ Notifications email désactivées${NC}"
    fi
    
    echo -e "${GREEN}✅ Test terminé${NC}"
    
    # Résumé
    echo -e "${BLUE}📋 Résumé des notifications actives:${NC}"
    echo "   Desktop: $([ "$ENABLE_DESKTOP_NOTIFICATIONS" = "true" ] && echo "Activé" || echo "Désactivé")"
    echo "   Email: $([ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && echo "Activé" || echo "Désactivé")"
    echo "   Sonore: Activé (fallback disponible)"
}

# Fonction de diagnostic
diagnose_notifications() {
    echo -e "${BLUE}🔍 Diagnostic complet des notifications${NC}"
    echo ""
    
    echo -e "${YELLOW}Environnement système:${NC}"
    echo "   OS: $(uname -s) $(uname -r)"
    echo "   Desktop: ${XDG_CURRENT_DESKTOP:-'Inconnu'} (${DESKTOP_SESSION:-'N/A'})"
    echo "   Display: ${DISPLAY:-'Non défini'}"
    echo "   User: $(whoami)"
    echo ""
    
    echo -e "${YELLOW}Outils disponibles:${NC}"
    echo "   notify-send: $(command -v notify-send &> /dev/null && echo "✅ $(notify-send --version 2>&1 | head -1)" || echo "❌ Non installé")"
    echo "   paplay: $(command -v paplay &> /dev/null && echo "✅ PulseAudio" || echo "❌ Non disponible")"
    echo "   aplay: $(command -v aplay &> /dev/null && echo "✅ ALSA" || echo "❌ Non disponible")"
    echo "   mail: $(command -v mail &> /dev/null && echo "✅ $(mail --version 2>&1 | head -1)" || echo "❌ Non installé")"
    echo "   sendmail: $(command -v sendmail &> /dev/null && echo "✅ Disponible" || echo "❌ Non disponible")"
    echo ""
    
    echo -e "${YELLOW}Configuration actuelle:${NC}"
    echo "   Fichier config: ${NOTIFICATION_CONFIG}"
    echo "   Desktop activé: $([ "$ENABLE_DESKTOP_NOTIFICATIONS" = "true" ] && echo "✅ Oui" || echo "❌ Non")"
    echo "   Email activé: $([ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && echo "✅ Oui" || echo "❌ Non")"
    echo "   Destinataire: ${EMAIL_RECIPIENT:-'Non défini'}"
    echo ""
    
    echo -e "${YELLOW}Test des fonctionnalités:${NC}"
    
    # Test desktop
    echo -n "   Notification desktop: "
    if [ "$ENABLE_DESKTOP_NOTIFICATIONS" = "true" ] && command -v notify-send &> /dev/null; then
        if timeout 2 notify-send "Test diagnostic" "Ceci est un test de diagnostic" --expire-time=2000 2>/dev/null; then
            echo -e "${GREEN}✅ Fonctionnelle${NC}"
        else
            echo -e "${RED}❌ Échec (vérifiez votre environnement graphique)${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ Désactivée ou non disponible${NC}"
    fi
    
    # Test son
    echo -n "   Notification sonore: "
    if play_notification_sound "bell" 2>/dev/null; then
        echo -e "${GREEN}✅ Fonctionnelle${NC}"
    else
        echo -e "${YELLOW}⚠️ Limitée (bell ASCII)${NC}"
    fi
    
    # Test email
    echo -n "   Notification email: "
    if [ "$ENABLE_EMAIL_NOTIFICATIONS" = "true" ] && [ -n "$EMAIL_RECIPIENT" ]; then
        if command -v mail &> /dev/null || command -v sendmail &> /dev/null; then
            echo -e "${GREEN}✅ Configurée${NC}"
        else
            echo -e "${RED}❌ Outil d'envoi non disponible${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️ Non configurée${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}💡 Conseils de dépannage:${NC}"
    echo "   • Si desktop ne fonctionne pas: vérifiez que vous êtes dans un environnement graphique"
    echo "   • Si email ne fonctionne pas: configurez un serveur SMTP ou utilisez mail/sendmail"
    echo "   • Pour les serveurs headless: utilisez uniquement les notifications email"
    echo "   • Testez avec: ./plex_notifications.sh test"
}

# Fonction principale
main() {
    local action="${1:-help}"
    
    # Charger la configuration
    load_config
    
    case "$action" in
        "workflow_started")
            notify_workflow_started "$2" "$3" "$4" "$5" "$6"
            ;;
        "files_deleted")
            notify_files_deleted "$2" "$3"
            ;;
        "songrec_completed")
            notify_songrec_completed "$2" "$3" "$4" "$5"
            ;;
        "rating_sync_completed")
            notify_rating_sync_completed "$2" "$3" "$4"
            ;;
        "workflow_completed")
            notify_workflow_completed "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9"
            ;;
        "critical_error")
            notify_critical_error "$2" "$3"
            ;;
        "monthly_report_generated")
            notify_monthly_report_generated "$2"
            ;;
        "duplicates_analysis_completed")
            notify_duplicates_analysis_completed "$2" "$3" "$4"
            ;;
        "minor_error")
            notify_minor_error "$2" "$3"
            ;;
        "test")
            test_notifications
            ;;
        "configure"|"config")
            configure_notifications
            ;;
        "diagnose"|"diag")
            diagnose_notifications
            ;;
        "help"|*)
            echo "Usage: $0 [action] [parameters]"
            echo ""
            echo "Actions:"
            echo "  workflow_started files_1_star files_2_star files_sync albums_1_star albums_2_star"
            echo "  files_deleted count details"
            echo "  songrec_completed processed errors album_count track_count"
            echo "  rating_sync_completed synced errors file_count"
            echo "  workflow_completed deleted songrec_proc songrec_err ratings_sync ratings_err albums_1 albums_2 duration"
            echo "  critical_error error_type error_message"
            echo "  monthly_report_generated report_path"
            echo "  duplicates_analysis_completed exact_dups similar_titles file_dups"
            echo "  minor_error error_type error_message"
            echo "  test              - Tester les notifications"
            echo "  configure         - Configuration interactive"
            echo "  diagnose          - Diagnostic complet du système de notifications"
            ;;
    esac
}

# Lancer le script
main "$@"