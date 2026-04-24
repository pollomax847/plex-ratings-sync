#!/bin/bash
# Generic Notification System for Audio Management Scripts
# Open Source - No hardcoded paths or personal information
#
# This script provides a unified notification system that can be used by
# various audio management tools. It supports multiple notification methods:
# - Desktop notifications (notify-send)
# - Email notifications (mail/sendmail)
# - Console output with colors
# - Sound notifications
#
# Configuration is done via environment variables or config file

# Default configuration - can be overridden by environment variables
: "${NOTIFICATION_CONFIG_FILE:=${XDG_CONFIG_HOME:-$HOME/.config}/audio_notifications.conf}"
: "${NOTIFICATION_APP_NAME:=Audio Manager}"
: "${NOTIFICATION_ENABLE_DESKTOP:=false}"
: "${NOTIFICATION_ENABLE_EMAIL:=false}"
: "${NOTIFICATION_ENABLE_CONSOLE:=true}"
: "${NOTIFICATION_ENABLE_SOUND:=true}"
: "${NOTIFICATION_EMAIL_RECIPIENT:=}"
: "${NOTIFICATION_SMTP_SERVER:=}"
: "${NOTIFICATION_LOG_LEVEL:=info}"
: "${NOTIFICATION_LOG_FILE:=}"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Load configuration from file if it exists
load_config() {
    if [ -f "$NOTIFICATION_CONFIG_FILE" ]; then
        # shellcheck source=/dev/null
        . "$NOTIFICATION_CONFIG_FILE"
    fi
}

# Save current configuration to file
save_config() {
    local config_dir
    config_dir=$(dirname "$NOTIFICATION_CONFIG_FILE")

    if [ ! -d "$config_dir" ]; then
        mkdir -p "$config_dir" 2>/dev/null || return 1
    fi

    cat > "$NOTIFICATION_CONFIG_FILE" << EOF
# Audio Manager Notifications Configuration
# Generated on $(date)
NOTIFICATION_APP_NAME="$NOTIFICATION_APP_NAME"
NOTIFICATION_ENABLE_DESKTOP="$NOTIFICATION_ENABLE_DESKTOP"
NOTIFICATION_ENABLE_EMAIL="$NOTIFICATION_ENABLE_EMAIL"
NOTIFICATION_ENABLE_CONSOLE="$NOTIFICATION_ENABLE_CONSOLE"
NOTIFICATION_ENABLE_SOUND="$NOTIFICATION_ENABLE_SOUND"
NOTIFICATION_EMAIL_RECIPIENT="$NOTIFICATION_EMAIL_RECIPIENT"
NOTIFICATION_SMTP_SERVER="$NOTIFICATION_SMTP_SERVER"
NOTIFICATION_LOG_LEVEL="$NOTIFICATION_LOG_LEVEL"
NOTIFICATION_LOG_FILE="$NOTIFICATION_LOG_FILE"
EOF
}

# Log function
log_message() {
    local level="$1"
    local message="$2"

    # Check if we should log this level
    case "$NOTIFICATION_LOG_LEVEL" in
        debug) ;;
        info) [ "$level" = "debug" ] && return ;;
        warning) [ "$level" = "debug" ] || [ "$level" = "info" ] && return ;;
        error) [ "$level" != "error" ] && return ;;
        *) return ;;
    esac

    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [ -n "$NOTIFICATION_LOG_FILE" ]; then
        echo "[$timestamp] [$level] $message" >> "$NOTIFICATION_LOG_FILE"
    fi

    # Also log to stderr for debugging
    if [ "$level" = "error" ] || [ "$level" = "debug" ]; then
        echo "[$timestamp] [$level] $message" >&2
    fi
}

# Play notification sound
play_sound() {
    local sound_type="${1:-bell}"

    if [ "$NOTIFICATION_ENABLE_SOUND" != "true" ]; then
        return 0
    fi

    # Try different sound systems
    if command -v paplay >/dev/null 2>&1; then
        paplay "/usr/share/sounds/freedesktop/stereo/${sound_type}.oga" 2>/dev/null && return 0
    fi

    if command -v aplay >/dev/null 2>&1; then
        aplay "/usr/share/sounds/alsa/${sound_type}.wav" 2>/dev/null && return 0
    fi

    # Fallback: ASCII bell
    printf '\a' 2>/dev/null || true
}

# Send desktop notification
send_desktop() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"
    local icon="${4:-audio-x-generic}"

    if [ "$NOTIFICATION_ENABLE_DESKTOP" != "true" ]; then
        return 0
    fi

    if command -v notify-send >/dev/null 2>&1; then
        notify-send \
            --urgency="$urgency" \
            --icon="$icon" \
            --app-name="$NOTIFICATION_APP_NAME" \
            --expire-time=5000 \
            "$title" \
            "$message" 2>/dev/null
        return $?
    fi

    return 1
}

# Send email notification
send_email() {
    local subject="$1"
    local body="$2"

    if [ "$NOTIFICATION_ENABLE_EMAIL" != "true" ] || [ -z "$NOTIFICATION_EMAIL_RECIPIENT" ]; then
        return 0
    fi

    local full_subject="[$NOTIFICATION_APP_NAME] $subject"

    if command -v mail >/dev/null 2>&1; then
        echo "$body" | mail -s "$full_subject" "$NOTIFICATION_EMAIL_RECIPIENT"
        return $?
    elif command -v sendmail >/dev/null 2>&1; then
        {
            echo "Subject: $full_subject"
            echo "To: $NOTIFICATION_EMAIL_RECIPIENT"
            echo ""
            echo "$body"
        } | sendmail "$NOTIFICATION_EMAIL_RECIPIENT"
        return $?
    fi

    return 1
}

# Send console notification
send_console() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"

    if [ "$NOTIFICATION_ENABLE_CONSOLE" != "true" ]; then
        return 0
    fi

    case "$urgency" in
        critical)
            echo -e "${RED}🚨 $title: $message${NC}"
            ;;
        warning)
            echo -e "${YELLOW}⚠️  $title: $message${NC}"
            ;;
        success)
            echo -e "${GREEN}✅ $title: $message${NC}"
            ;;
        info|normal)
            echo -e "${BLUE}ℹ️  $title: $message${NC}"
            ;;
        *)
            echo -e "${CYAN}🔔 $title: $message${NC}"
            ;;
    esac
}

# Unified notification function
notify() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"
    local icon="${4:-audio-x-generic}"
    local sound="${5:-bell}"

    log_message "info" "Notification: $title - $message"

    # Send notifications in order of preference
    local desktop_result=1
    local email_result=1
    local console_result=0

    send_desktop "$title" "$message" "$urgency" "$icon" && desktop_result=0
    send_email "$title" "$message" && email_result=0
    send_console "$title" "$message" "$urgency" && console_result=0

    # Play sound if any notification was sent successfully
    if [ $desktop_result -eq 0 ] || [ $email_result -eq 0 ] || [ $console_result -eq 0 ]; then
        play_sound "$sound"
    fi

    # Return success if at least one notification method worked
    [ $desktop_result -eq 0 ] || [ $email_result -eq 0 ] || [ $console_result -eq 0 ]
}

# Specific notification types
notify_success() {
    local title="$1"
    local message="$2"
    notify "$title" "$message" "success" "dialog-information" "bell"
}

notify_warning() {
    local title="$1"
    local message="$2"
    notify "$title" "$message" "warning" "dialog-warning" "bell"
}

notify_error() {
    local title="$1"
    local message="$2"
    notify "$title" "$message" "critical" "dialog-error" "bell"
}

notify_info() {
    local title="$1"
    local message="$2"
    notify "$title" "$message" "info" "dialog-information" "bell"
}

# Summary notification - single comprehensive notification
notify_summary() {
    local operation="$1"
    local status="${2:-completed}"
    local duration="${3:-}"
    local deleted="${4:-0}"
    local processed="${5:-0}"
    local errors="${6:-0}"
    local synced="${7:-0}"
    local sync_errors="${8:-0}"

    # Build comprehensive message
    local title="$NOTIFICATION_APP_NAME - $operation"
    local message=""

    case "$status" in
        "completed")
            message="✅ $operation terminé avec succès"
            if [ -n "$duration" ]; then
                message="$message en $duration"
            fi
            message="$message\n"
            ;;
        "failed")
            message="❌ $operation échoué"
            if [ -n "$duration" ]; then
                message="$message après $duration"
            fi
            message="$message\n"
            ;;
        "running")
            message="🔄 $operation en cours..."
            if [ -n "$duration" ]; then
                message="$message depuis $duration"
            fi
            message="$message\n"
            ;;
    esac

    # Add statistics if provided
    local has_stats=false
    if [ "$deleted" != "0" ] || [ "$processed" != "0" ] || [ "$errors" != "0" ] || [ "$synced" != "0" ] || [ "$sync_errors" != "0" ]; then
        has_stats=true
        message="$message📊 Statistiques:\n"
        [ "$deleted" != "0" ] && message="$message• Supprimés: $deleted\n"
        [ "$processed" != "0" ] && message="$message• Traités: $processed\n"
        [ "$errors" != "0" ] && message="$message• Erreurs: $errors\n"
        [ "$synced" != "0" ] && message="$message• Synchronisés: $synced\n"
        [ "$sync_errors" != "0" ] && message="$message• Erreurs sync: $sync_errors\n"
    fi

    # Determine urgency and icon based on status and errors
    local urgency="normal"
    local icon="audio-x-generic"
    local sound="bell"

    if [ "$status" = "failed" ] || [ "$errors" != "0" ] || [ "$sync_errors" != "0" ]; then
        urgency="critical"
        icon="dialog-error"
        sound="bell"
    elif [ "$status" = "completed" ]; then
        urgency="normal"
        icon="dialog-information"
        sound="bell"
    fi

    # Send the comprehensive notification
    notify "$title" "$message" "$urgency" "$icon" "$sound"
}

# Test all notification methods
test_notifications() {
    echo -e "${YELLOW}🧪 Testing $NOTIFICATION_APP_NAME notifications...${NC}"
    echo

    # Test console
    if [ "$NOTIFICATION_ENABLE_CONSOLE" = "true" ]; then
        echo -n "Console notifications: "
        if send_console "Test" "Console notification test" "success"; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${RED}❌ Failed${NC}"
        fi
    else
        echo -e "Console notifications: ${BLUE}Disabled${NC}"
    fi

    # Test desktop
    if [ "$NOTIFICATION_ENABLE_DESKTOP" = "true" ]; then
        echo -n "Desktop notifications: "
        if send_desktop "Test" "Desktop notification test" "normal" "audio-card"; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${YELLOW}⚠️  Not available or failed${NC}"
        fi
    else
        echo -e "Desktop notifications: ${BLUE}Disabled${NC}"
    fi

    # Test email
    if [ "$NOTIFICATION_ENABLE_EMAIL" = "true" ] && [ -n "$NOTIFICATION_EMAIL_RECIPIENT" ]; then
        echo -n "Email notifications: "
        if send_email "Test" "Email notification test from $NOTIFICATION_APP_NAME"; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${YELLOW}⚠️  Not available or failed${NC}"
        fi
    else
        echo -e "Email notifications: ${BLUE}Disabled or not configured${NC}"
    fi

    # Test sound
    if [ "$NOTIFICATION_ENABLE_SOUND" = "true" ]; then
        echo -n "Sound notifications: "
        if play_sound "bell"; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${YELLOW}⚠️  Limited (ASCII bell only)${NC}"
        fi
    else
        echo -e "Sound notifications: ${BLUE}Disabled${NC}"
    fi

    echo
    echo -e "${GREEN}✅ Test completed${NC}"
}

# Interactive configuration
configure() {
    echo -e "${BLUE}🔧 $NOTIFICATION_APP_NAME Notification Configuration${NC}"
    echo

    # App name
    echo -n "Application name [$NOTIFICATION_APP_NAME]: "
    read -r input
    [ -n "$input" ] && NOTIFICATION_APP_NAME="$input"

    # Console notifications
    echo -n "Enable console notifications? [Y/n]: "
    read -r input
    if [[ $input =~ ^[Nn]$ ]]; then
        NOTIFICATION_ENABLE_CONSOLE=false
    else
        NOTIFICATION_ENABLE_CONSOLE=true
    fi

    # Desktop notifications
    echo -n "Enable desktop notifications? [y/N]: "
    read -r input
    if [[ $input =~ ^[Yy]$ ]]; then
        NOTIFICATION_ENABLE_DESKTOP=true
    else
        NOTIFICATION_ENABLE_DESKTOP=false
    fi

    # Sound notifications
    echo -n "Enable sound notifications? [Y/n]: "
    read -r input
    if [[ $input =~ ^[Nn]$ ]]; then
        NOTIFICATION_ENABLE_SOUND=false
    else
        NOTIFICATION_ENABLE_SOUND=true
    fi

    # Email notifications
    echo -n "Enable email notifications? [y/N]: "
    read -r input
    if [[ $input =~ ^[Yy]$ ]]; then
        NOTIFICATION_ENABLE_EMAIL=true
        echo -n "Email recipient: "
        read -r NOTIFICATION_EMAIL_RECIPIENT
        echo -n "SMTP server (optional): "
        read -r NOTIFICATION_SMTP_SERVER
    else
        NOTIFICATION_ENABLE_EMAIL=false
        NOTIFICATION_EMAIL_RECIPIENT=""
        NOTIFICATION_SMTP_SERVER=""
    fi

    # Log level
    echo -n "Log level [info]: "
    read -r input
    case "$input" in
        debug|info|warning|error) NOTIFICATION_LOG_LEVEL="$input" ;;
        *) NOTIFICATION_LOG_LEVEL="info" ;;
    esac

    # Save configuration
    if save_config; then
        echo -e "${GREEN}✅ Configuration saved to: $NOTIFICATION_CONFIG_FILE${NC}"
    else
        echo -e "${RED}❌ Failed to save configuration${NC}"
    fi

    # Test
    echo -n "Test notifications now? [Y/n]: "
    read -r input
    if [[ ! $input =~ ^[Nn]$ ]]; then
        test_notifications
    fi
}

# Show current configuration
show_config() {
    echo -e "${BLUE}📋 Current $NOTIFICATION_APP_NAME Notification Configuration${NC}"
    echo
    echo "Configuration file: $NOTIFICATION_CONFIG_FILE"
    echo "Application name: $NOTIFICATION_APP_NAME"
    echo "Console notifications: $([ "$NOTIFICATION_ENABLE_CONSOLE" = "true" ] && echo "✅ Enabled" || echo "❌ Disabled")"
    echo "Desktop notifications: $([ "$NOTIFICATION_ENABLE_DESKTOP" = "true" ] && echo "✅ Enabled" || echo "❌ Disabled")"
    echo "Email notifications: $([ "$NOTIFICATION_ENABLE_EMAIL" = "true" ] && echo "✅ Enabled" || echo "❌ Disabled")"
    echo "Sound notifications: $([ "$NOTIFICATION_ENABLE_SOUND" = "true" ] && echo "✅ Enabled" || echo "❌ Disabled")"
    echo "Email recipient: ${NOTIFICATION_EMAIL_RECIPIENT:-Not set}"
    echo "SMTP server: ${NOTIFICATION_SMTP_SERVER:-Not set}"
    echo "Log level: $NOTIFICATION_LOG_LEVEL"
    echo "Log file: ${NOTIFICATION_LOG_FILE:-Not set}"
}

# Main function
main() {
    load_config

    case "${1:-help}" in
        success)
            notify_success "$2" "$3"
            ;;
        warning)
            notify_warning "$2" "$3"
            ;;
        error)
            notify_error "$2" "$3"
            ;;
        info)
            notify_info "$2" "$3"
            ;;
        summary)
            # summary <operation> <status> <duration> <deleted> <processed> <errors> <synced> <sync_errors>
            notify_summary "${2:-operation}" "${3:-completed}" "${4:-}" "${5:-0}" "${6:-0}" "${7:-0}" "${8:-0}" "${9:-0}"
            ;;
        test)
            test_notifications
            ;;
        config|configure)
            configure
            ;;
        show)
            show_config
            ;;
        help|*)
            cat << EOF
$NOTIFICATION_APP_NAME Notification System

USAGE: $0 <command> [options]

COMMANDS:
    success <title> <message>    Send success notification
    warning <title> <message>    Send warning notification
    error <title> <message>      Send error notification
    info <title> <message>       Send info notification
    summary <operation> [status] [duration] [deleted] [processed] [errors] [synced] [sync_errors]
                                 Send comprehensive summary notification
    test                         Test all notification methods
    config                       Interactive configuration
    show                         Show current configuration
    help                         Show this help

ENVIRONMENT VARIABLES:
    NOTIFICATION_CONFIG_FILE     Config file path (default: ~/.config/audio_notifications.conf)
    NOTIFICATION_APP_NAME        Application name (default: Audio Manager)
    NOTIFICATION_ENABLE_DESKTOP  Enable desktop notifications (default: false)
    NOTIFICATION_ENABLE_EMAIL    Enable email notifications (default: false)
    NOTIFICATION_ENABLE_CONSOLE  Enable console notifications (default: true)
    NOTIFICATION_ENABLE_SOUND    Enable sound notifications (default: true)
    NOTIFICATION_EMAIL_RECIPIENT Email recipient address
    NOTIFICATION_SMTP_SERVER     SMTP server (optional)
    NOTIFICATION_LOG_LEVEL       Log level: debug, info, warning, error
    NOTIFICATION_LOG_FILE        Log file path (optional)

EXAMPLES:
    $0 success "Backup Complete" "All files backed up successfully"
    $0 error "Disk Full" "No space left on device"
    $0 summary "Monthly Sync" completed "2h 15m" 15 8 2 45 1
    NOTIFICATION_ENABLE_DESKTOP=true $0 test

EOF
            ;;
    esac
}

# N'exécute main que si le script est lancé directement (pas sourcé)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi