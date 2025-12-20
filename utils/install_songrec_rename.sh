#!/bin/bash
# Script d'installation et configuration de songrec-rename pour le workflow Plex

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎵 Installation songrec-rename pour workflow Plex${NC}"
echo "=================================================="
echo

# Vérifier si songrec-rename est déjà installé
if command -v songrec-rename &> /dev/null; then
    echo -e "${GREEN}✅ songrec-rename déjà installé${NC}"
    songrec-rename --version
    return 0 2>/dev/null || exit 0
fi

# Vérifier les prérequis système
echo -e "${YELLOW}🔍 Vérification des prérequis...${NC}"

# Vérifier Rust/Cargo
if ! command -v cargo &> /dev/null; then
    echo -e "${YELLOW}⚠️ Rust/Cargo non installé${NC}"
    echo "Installation de Rust..."
    
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
    
    if command -v cargo &> /dev/null; then
        echo -e "${GREEN}✅ Rust installé avec succès${NC}"
    else
        echo -e "${RED}❌ Échec installation Rust${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Rust/Cargo disponible${NC}"
fi

# Vérifier les dépendances système nécessaires
echo "🔍 Vérification des dépendances système..."

# Pour Ubuntu/Debian
if command -v apt &> /dev/null; then
    missing_deps=()
    
    # Vérifier les dépendances de songrec
    for dep in libasound2-dev libssl-dev pkg-config; do
        if ! dpkg -l | grep -q "^ii.*$dep"; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${YELLOW}📦 Installation des dépendances manquantes...${NC}"
        sudo apt update
        sudo apt install -y "${missing_deps[@]}"
    fi
    
    echo -e "${GREEN}✅ Dépendances système OK${NC}"
fi

# Installation de songrec-rename
echo -e "${YELLOW}📦 Installation de songrec-rename...${NC}"
echo "Cela peut prendre plusieurs minutes..."

if cargo install songrec-rename; then
    echo -e "${GREEN}✅ songrec-rename installé avec succès${NC}"
else
    echo -e "${RED}❌ Échec installation songrec-rename${NC}"
    echo "Essayez manuellement :"
    echo "cargo install songrec-rename"
    exit 1
fi

# Vérifier l'installation
echo -e "\n${YELLOW}🧪 Test de l'installation...${NC}"

if command -v songrec-rename &> /dev/null; then
    echo -e "${GREEN}✅ songrec-rename fonctionne${NC}"
    songrec-rename --version
else
    echo -e "${RED}❌ songrec-rename non trouvé dans le PATH${NC}"
    echo "Ajout au PATH..."
    
    # Ajouter cargo/bin au PATH si pas déjà fait
    if ! echo "$PATH" | grep -q "$HOME/.cargo/bin"; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/.cargo/bin:$PATH"
        echo -e "${GREEN}✅ PATH mis à jour${NC}"
    fi
fi

# Configuration pour le workflow Plex
echo -e "\n${YELLOW}⚙️ Configuration pour le workflow Plex...${NC}"

# Créer les répertoires de queue s'ils n'existent pas
mkdir -p "$HOME/songrec_queue"
mkdir -p "$HOME/logs/songrec"

# Créer un script de test
TEST_SCRIPT="$HOME/songrec_queue/test_songrec.sh"
cat > "$TEST_SCRIPT" << 'EOF'
#!/bin/bash
# Script de test pour songrec-rename

echo "🧪 Test de songrec-rename"
echo "========================="

# Vérifier que songrec-rename est disponible
if command -v songrec-rename &> /dev/null; then
    echo "✅ songrec-rename trouvé : $(which songrec-rename)"
    songrec-rename --version
else
    echo "❌ songrec-rename non trouvé"
    echo "Vérifiez votre PATH : $PATH"
    exit 1
fi

echo
echo "📝 Pour tester sur un fichier :"
echo "songrec-rename /chemin/vers/fichier.mp3"
echo
echo "📚 Aide complète :"
echo "songrec-rename --help"
EOF

chmod +x "$TEST_SCRIPT"

echo -e "${GREEN}✅ Configuration terminée${NC}"

# Afficher les instructions d'usage
echo -e "\n${BLUE}📋 Utilisation avec le workflow Plex${NC}"
echo "====================================="
echo
echo "1. 🎵 Évaluez vos morceaux dans PlexAmp :"
echo "   - 1 ⭐ = suppression automatique"
echo "   - 2 ⭐ = scan avec songrec-rename"
echo
echo "2. 🔄 Le workflow mensuel :"
echo "   - Se lance automatiquement fin de mois"
echo "   - Supprime les fichiers 1 ⭐"
echo "   - Prépare les queues pour les fichiers 2 ⭐"
echo
echo "3. 🔍 Traiter les queues songrec-rename :"
echo "   cd ~/songrec_queue/YYYYMMDD_HHMMSS/"
echo "   ./process_2_stars.sh"
echo
echo "4. 🧪 Tester l'installation :"
echo "   $TEST_SCRIPT"

# Configuration du cron
echo -e "\n${YELLOW}📅 Configuration du cron (optionnel)${NC}"
echo "===================================="
echo
echo "Pour automatiser le workflow mensuel :"
echo "1. crontab -e"
echo "2. Ajouter la ligne :"
echo "   0 2 28-31 * * [ \"\$(date -d tomorrow +%d)\" -eq 1 ] && $HOME/bin/audio/plex_monthly_workflow.sh"
echo "3. Sauvegarder"

# Vérifier l'espace disque
echo -e "\n${YELLOW}💾 Vérification espace disque${NC}"
echo "============================="
df -h /mnt/mybook 2>/dev/null || df -h $HOME

echo -e "\n${GREEN}🎉 Installation terminée !${NC}"
echo "Songrec-rename est prêt pour le workflow Plex."
echo
echo -e "${BLUE}Prochaines étapes :${NC}"
echo "1. Configurez le cron pour le workflow mensuel"
echo "2. Évaluez quelques morceaux dans PlexAmp (2 ⭐)"
echo "3. Testez le workflow : $HOME/bin/audio/plex_monthly_workflow.sh"
echo
echo -e "${YELLOW}💡 Conseil :${NC}"
echo "songrec-rename utilise la reconnaissance audio en ligne."
echo "Assurez-vous d'avoir une bonne connexion internet."