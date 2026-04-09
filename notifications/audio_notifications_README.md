# Audio Notifications - Système de Résumé Complet

**NOUVELLES FONCTIONNALITÉ :** Une seule notification qui contient TOUTES les informations !

Cette version utilise la configuration la plus simple et fiable : **notifications desktop et console uniquement**.

## Notification de Résumé Complet

Au lieu d'envoyer 3-4 notifications séparées (début, succès, erreur), le système envoie maintenant **UNE SEULE notification** avec toutes les statistiques.

### Avantages

- ✅ **Moins intrusif** : 1 notification au lieu de 4
- ✅ **Plus informatif** : Toutes les stats dans un seul endroit
- ✅ **Plus propre** : Interface utilisateur moins encombrée
- ✅ **Plus efficace** : Résumé complet en un coup d'œil

### Exemple d'Utilisation

```bash
# Notification de résumé complet
./audio_notifications.sh summary "Monthly Sync" completed "2h 15m" 15 8 2 45 1

# Affiche :
# ✅ Monthly Sync terminé avec succès en 2h 15m
# 📊 Statistiques:
# • Supprimés: 15
# • Traités: 8
# • Erreurs: 2
# • Synchronisés: 45
# • Erreurs sync: 1
```

### Paramètres de la Commande Summary

```bash
summary <operation> [status] [duration] [deleted] [processed] [errors] [synced] [sync_errors]
```

- `operation` : Nom de l'opération (ex: "Monthly Sync")
- `status` : "completed", "failed", ou "running"
- `duration` : Durée (ex: "2h 15m")
- `deleted` : Nombre d'éléments supprimés
- `processed` : Nombre d'éléments traités
- `errors` : Nombre d'erreurs de traitement
- `synced` : Nombre d'éléments synchronisés
- `sync_errors` : Nombre d'erreurs de synchronisation

## Configuration Ultra-Simple

Pour la configuration la plus simple possible :

```bash
# Exécutez ce script une seule fois
./setup_simple_notifications.sh
```

C'est tout ! Le système sera configuré avec :
- ✅ Notifications desktop (pop-ups)
- ✅ Notifications console (couleurs)
- ✅ Notifications sonores (bips)
- ❌ Emails désactivés (pas besoin de config SMTP)

## Utilisation dans vos Scripts

```bash
#!/bin/bash
source ./audio_notifications.sh

# Vos scripts existants fonctionneront automatiquement
# avec UNE SEULE notification de résumé à la fin
```

## Usage in Scripts

### Basic Usage

```bash
#!/bin/bash
source ./audio_notifications.sh

# Send a success notification
notify_success "Backup Complete" "All audio files backed up successfully"

# Send an error notification
notify_error "Sync Failed" "Unable to connect to Plex database"

# Send an info notification
notify_info "Processing Started" "Beginning audio file analysis"
```

### Advanced Usage with Environment Variables

```bash
#!/bin/bash

# Configure notifications
export NOTIFICATION_ENABLE_DESKTOP=true
export NOTIFICATION_ENABLE_EMAIL=false
export NOTIFICATION_ENABLE_CONSOLE=true
export NOTIFICATION_APP_NAME="My Audio Manager"

source ./audio_notifications.sh

# Your script logic here
if process_audio_files; then
    notify_success "Processing Complete" "All files processed successfully"
else
    notify_error "Processing Failed" "Some files could not be processed"
fi
```

### Configuration File

Create `~/.config/audio_notifications.conf`:

```bash
# Audio Manager Notifications Configuration
NOTIFICATION_APP_NAME="Plex Audio Manager"
NOTIFICATION_ENABLE_DESKTOP=true
NOTIFICATION_ENABLE_EMAIL=false
NOTIFICATION_ENABLE_CONSOLE=true
NOTIFICATION_ENABLE_SOUND=true
NOTIFICATION_EMAIL_RECIPIENT="admin@example.com"
NOTIFICATION_LOG_LEVEL="info"
NOTIFICATION_LOG_FILE="/var/log/audio_manager.log"
```

## Integration Examples

### In plex_ratings_sync.py

```python
#!/usr/bin/env python3
import subprocess
import sys

def notify(level, title, message):
    """Send notification using the generic notification script"""
    try:
        script_path = "/path/to/audio_notifications.sh"
        subprocess.run([script_path, level, title, message], check=True)
    except subprocess.CalledProcessError:
        # Fallback to console if notification fails
        print(f"[{level.upper()}] {title}: {message}")

# In your sync function
def sync_ratings():
    try:
        # Your sync logic here
        notify("success", "Sync Complete", f"Synchronized {count} ratings")
    except Exception as e:
        notify("error", "Sync Failed", str(e))
        sys.exit(1)
```

### In Bash Scripts

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/audio_notifications.sh"

# Enable notifications for this script
export NOTIFICATION_ENABLE_DESKTOP=true
export NOTIFICATION_APP_NAME="Plex Cleanup"

# Your script logic
if cleanup_old_files; then
    notify_success "Cleanup Complete" "Removed $deleted_count old files"
else
    notify_error "Cleanup Failed" "Unable to remove old files"
    exit 1
fi
```

## Command Line Usage

```bash
# Send notifications directly
./audio_notifications.sh success "Task Done" "Everything completed successfully"
./audio_notifications.sh error "Task Failed" "Something went wrong"
./audio_notifications.sh warning "Low Disk Space" "Only 10GB remaining"
./audio_notifications.sh info "Processing" "Starting batch job"

# Test all notification methods
./audio_notifications.sh test

# Interactive configuration
./audio_notifications.sh config

# Show current configuration
./audio_notifications.sh show
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTIFICATION_CONFIG_FILE` | `~/.config/audio_notifications.conf` | Configuration file path |
| `NOTIFICATION_APP_NAME` | `Audio Manager` | Application name in notifications |
| `NOTIFICATION_ENABLE_DESKTOP` | `false` | Enable desktop notifications |
| `NOTIFICATION_ENABLE_EMAIL` | `false` | Enable email notifications |
| `NOTIFICATION_ENABLE_CONSOLE` | `true` | Enable console notifications |
| `NOTIFICATION_ENABLE_SOUND` | `true` | Enable sound notifications |
| `NOTIFICATION_EMAIL_RECIPIENT` | `` | Email recipient address |
| `NOTIFICATION_SMTP_SERVER` | `` | SMTP server (optional) |
| `NOTIFICATION_LOG_LEVEL` | `info` | Log level: debug, info, warning, error |
| `NOTIFICATION_LOG_FILE` | `` | Log file path (optional) |

## Dependencies

- `notify-send` (for desktop notifications)
- `mail` or `sendmail` (for email notifications)
- `paplay` or `aplay` (for sound notifications)

## Open Source Notes

This version has been sanitized for open source distribution:
- Removed all hardcoded personal paths
- Removed specific user configurations
- Added flexible configuration system
- Included comprehensive documentation
- Made all paths relative or configurable

## License

MIT License - Free to use and modify for any purpose.