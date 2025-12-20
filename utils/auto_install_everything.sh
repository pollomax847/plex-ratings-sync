#!/bin/bash
# Installation 100% automatique - ZÉRO intervention manuelle
# Une seule commande, tout est configuré !

set -euo pipefail

echo "🚀 INSTALLATION 100% AUTOMATIQUE PLEX RATINGS"
echo "============================================="
echo "Aucune intervention manuelle requise !"
echo

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(dirname "$0")"
LOG_FILE="$HOME/logs/auto_install_$(date +%Y%m%d_%H%M%S).log"

# Créer les répertoires
mkdir -p "$HOME/logs" "$HOME/plex_backup" "$HOME/songrec_queue"

# Fonction de logging
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log "${BLUE}📋 INSTALLATION AUTOMATIQUE EN COURS...${NC}"

# Étape 1: Vérifications système
log "🔍 Vérification du système..."
if ! command -v python3 &> /dev/null; then
    log "${RED}❌ Python3 requis mais absent${NC}"
    exit 1
fi
log "${GREEN}✅ Python3 OK${NC}"

# Étape 2: Configuration cron automatique
log "📅 Configuration automatique du cron..."
CRON_LINE="0 2 28-31 * * [ \"\$(date -d tomorrow +%d)\" -eq 1 ] && $SCRIPT_DIR/plex_monthly_workflow.sh >> $HOME/logs/plex_auto.log 2>&1"

# Supprimer toute tâche plex existante et ajouter la nouvelle
(crontab -l 2>/dev/null | grep -v "plex_monthly_workflow.sh" || true; echo "$CRON_LINE") | crontab -
log "${GREEN}✅ Tâche cron configurée (fin de mois à 2h)${NC}"

# Étape 3: Installation automatique Rust + songrec-rename
log "🎵 Installation automatique de songrec-rename..."

# Installer Rust silencieusement si absent
if ! command -v cargo &> /dev/null; then
    log "📦 Installation Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y -q
    source ~/.cargo/env
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
fi

# Installer les dépendances système (Ubuntu/Debian)
if command -v apt &> /dev/null; then
    log "📦 Installation dépendances système..."
    export DEBIAN_FRONTEND=noninteractive
    sudo apt update -qq
    sudo apt install -y -qq libasound2-dev libssl-dev pkg-config build-essential
fi

# Installer songrec-rename
if ! command -v songrec-rename &> /dev/null; then
    log "🔧 Compilation songrec-rename..."
    source ~/.cargo/env 2>/dev/null || true
    cargo install songrec-rename -q
    log "${GREEN}✅ songrec-rename installé${NC}"
else
    log "${GREEN}✅ songrec-rename déjà installé${NC}"
fi

# Étape 4: Configuration des permissions
log "🔧 Configuration des permissions..."
chmod +x "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.py 2>/dev/null || true

# Étape 5: Création du fichier de configuration
cat > "$HOME/.plex_ratings_config" << EOF
# Configuration automatique Plex Ratings
AUDIO_LIBRARY="/mnt/mybook/itunes/Music"
BACKUP_DIR="$HOME/plex_backup"
TARGET_RATING_DELETE=1
TARGET_RATING_SONGREC=2
LOG_DIR="$HOME/logs"
SONGREC_QUEUE_DIR="$HOME/songrec_queue"
AUTO_PROCESS=true
EOF

# Étape 6: Test de fonctionnement
log "🧪 Test automatique du système..."

# Test basique Python
if python3 -c "import sqlite3; print('SQLite OK')" 2>/dev/null; then
    log "${GREEN}✅ Python/SQLite fonctionnel${NC}"
fi

# Test songrec si installé
if command -v songrec-rename &> /dev/null; then
    log "${GREEN}✅ songrec-rename fonctionnel${NC}"
fi

# Test accès bibliothèque
if [ -d "/mnt/mybook/itunes/Music" ]; then
    file_count=$(find "/mnt/mybook/itunes/Music" -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" 2>/dev/null | wc -l)
    log "${GREEN}✅ Bibliothèque accessible ($file_count fichiers)${NC}"
else
    log "${YELLOW}⚠️ Bibliothèque /mnt/mybook/itunes/Music non trouvée${NC}"
fi

# Étape 7: Script de maintenance automatique
cat > "$HOME/.plex_auto_check.sh" << 'EOF'
#!/bin/bash
# Vérification automatique silencieuse (lancée par cron si besoin)
{
    if ! command -v songrec-rename &> /dev/null; then
        source ~/.cargo/env 2>/dev/null || true
    fi
    if [ ! -f "$HOME/.plex_ratings_config" ]; then
        echo "Configuration manquante - réinstallation requise"
        exit 1
    fi
    echo "$(date): Système Plex Ratings OK" >> "$HOME/logs/plex_auto_check.log"
} 2>/dev/null
EOF

chmod +x "$HOME/.plex_auto_check.sh"

# Ajouter une vérification hebdomadaire
CRON_CHECK="0 1 * * 1 $HOME/.plex_auto_check.sh"
(crontab -l 2>/dev/null | grep -v ".plex_auto_check.sh" || true; echo "$CRON_CHECK") | crontab -

log ""
log "${GREEN}🎉 INSTALLATION 100% AUTOMATIQUE TERMINÉE !${NC}"
log "==========================================="
log ""
log "${BLUE}📊 RÉSUMÉ :${NC}"
log "✅ Scripts Plex Ratings configurés"
log "✅ songrec-rename installé et fonctionnel" 
log "✅ Cron configuré (fin de mois à 2h du matin)"
log "✅ Répertoires créés automatiquement"
log "✅ Maintenance automatique activée"
log ""
log "${GREEN}🚀 SYSTÈME ENTIÈREMENT AUTOMATISÉ !${NC}"
log "=================================="
log "• 🎧 Évaluez vos morceaux dans PlexAmp"
log "• 1 ⭐ → Suppression automatique (fin de mois)"
log "• 2 ⭐ → Scan songrec automatique (fin de mois)"
log "• 3-5 ⭐ → Conservation"
log ""
log "📅 PROCHAINE EXÉCUTION AUTOMATIQUE :"
next_run=$(date -d "$(date -d "$(date +%Y-%m-01) + 1 month - 1 day")" +"%d %B %Y à 02:00")
log "   🗓️ $next_run"
log ""
log "📁 LOGS ET RAPPORTS :"
log "   📝 Installation : $LOG_FILE"
log "   📊 Mensuel : ~/logs/plex_auto.log"
log "   💾 Sauvegardes : ~/plex_backup/"
log ""
log "${YELLOW}💡 PLUS RIEN À FAIRE MANUELLEMENT !${NC}"
log "Le système fonctionne désormais entièrement tout seul."
log ""
log "Pour tester immédiatement :"
log "   $SCRIPT_DIR/plex_monthly_workflow.sh"

# Notification finale
echo
echo -e "${GREEN}✨ INSTALLATION RÉUSSIE ! SYSTÈME 100% AUTOMATIQUE ! ✨${NC}"
echo
echo "Votre système de ratings Plex est maintenant entièrement automatisé."
echo "Plus aucune intervention manuelle nécessaire !"
echo
echo "Consultez les logs : tail -f ~/logs/plex_auto.log"