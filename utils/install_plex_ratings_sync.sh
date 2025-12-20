#!/bin/bash
# Installation et configuration rapide du synchronisateur Plex Ratings

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎵 Installation du Synchronisateur Plex Ratings${NC}"
echo "================================================="

# Vérifier les prérequis
echo -e "\n${YELLOW}🔍 Vérification des prérequis...${NC}"

# Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 requis mais non trouvé${NC}"
    echo "Installez Python 3 : sudo apt install python3"
    exit 1
fi

# SQLite (normalement inclus avec Python)
if ! python3 -c "import sqlite3" 2>/dev/null; then
    echo -e "${RED}❌ Module SQLite3 manquant${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 et SQLite OK${NC}"

# Vérifier si Plex Media Server est installé
echo -e "\n${YELLOW}🔍 Recherche de Plex Media Server...${NC}"

plex_found=false
plex_db_path=""

# Chemins possibles pour la base Plex
possible_paths=(
    "$HOME/.config/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
    "$HOME/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
)

for path in "${possible_paths[@]}"; do
    if [ -f "$path" ]; then
        plex_db_path="$path"
        plex_found=true
        break
    fi
done

if [ "$plex_found" = true ]; then
    echo -e "${GREEN}✅ Plex Media Server trouvé${NC}"
    echo "   📁 Base de données: $plex_db_path"
else
    echo -e "${YELLOW}⚠️  Plex Media Server non détecté automatiquement${NC}"
    echo "   Vous devrez spécifier le chemin manuellement lors de l'utilisation."
fi

# Vérifier les permissions d'accès à la base Plex
if [ "$plex_found" = true ]; then
    if [ -r "$plex_db_path" ]; then
        echo -e "${GREEN}✅ Permissions de lecture OK${NC}"
    else
        echo -e "${YELLOW}⚠️  Permissions de lecture limitées${NC}"
        echo "   Vous pourriez avoir besoin de sudo pour accéder à la base Plex"
    fi
fi

# Vérifier la structure du répertoire audio
echo -e "\n${YELLOW}🔍 Vérification de la bibliothèque audio...${NC}"

audio_dirs=(
    "/mnt/mybook/itunes/Music"
    "/mnt/mybook/Musiques"
    "$HOME/Musiques"
    "$HOME/Music"
    "/home/music"
)

audio_found=false
audio_path=""

for dir in "${audio_dirs[@]}"; do
    if [ -d "$dir" ] && [ "$(find "$dir" -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" 2>/dev/null | head -1)" ]; then
        audio_path="$dir"
        audio_found=true
        break
    fi
done

if [ "$audio_found" = true ]; then
    echo -e "${GREEN}✅ Bibliothèque audio trouvée${NC}"
    echo "   📁 Répertoire: $audio_path"
    
    # Compter les fichiers audio
    audio_count=$(find "$audio_path" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.wma" -o -name "*.aac" \) 2>/dev/null | wc -l)
    echo "   🎵 Fichiers audio détectés: $audio_count"
else
    echo -e "${YELLOW}⚠️  Bibliothèque audio non détectée automatiquement${NC}"
    echo "   Assurez-vous que vos fichiers audio sont accessibles"
fi

# Créer un fichier de configuration
echo -e "\n${YELLOW}📝 Création du fichier de configuration...${NC}"

config_file="$HOME/.plex_ratings_sync.conf"
cat > "$config_file" << EOF
# Configuration du synchronisateur Plex Ratings
# Généré automatiquement le $(date)

# Chemin vers la base de données Plex
PLEX_DB_PATH="$plex_db_path"

# Répertoire de la bibliothèque audio
AUDIO_LIBRARY_PATH="/mnt/mybook/itunes/Music"

# Rating cible pour suppression (1-5)
TARGET_RATING=1

# Répertoire de sauvegarde (laissez vide pour désactiver)
BACKUP_DIR="$HOME/plex_backup"

# Mode verbeux (true/false)
VERBOSE=false

# Vérifier l'existence des fichiers avant suppression
VERIFY_FILES=true
EOF

echo -e "${GREEN}✅ Configuration créée: $config_file${NC}"

# Rendre les scripts exécutables
script_dir="$(dirname "$0")"
chmod +x "$script_dir"/*.sh 2>/dev/null || true
chmod +x "$script_dir"/*.py 2>/dev/null || true

echo -e "${GREEN}✅ Scripts rendus exécutables${NC}"

# Test rapide
echo -e "\n${YELLOW}🧪 Test rapide du système...${NC}"

if [ "$plex_found" = true ]; then
    echo "Test de connexion à la base Plex..."
    if python3 "$script_dir/plex_ratings_sync.py" --plex-db "$plex_db_path" --stats >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Connexion Plex réussie${NC}"
    else
        echo -e "${YELLOW}⚠️  Problème de connexion Plex (normal si aucun rating)${NC}"
    fi
fi

# Afficher les instructions d'utilisation
echo -e "\n${GREEN}🎉 Installation terminée !${NC}"
echo "================================="
echo
echo -e "${BLUE}📋 Prochaines étapes:${NC}"
echo
echo "1. 📊 Voir les statistiques de vos ratings:"
if [ "$plex_found" = true ]; then
    echo "   ./plex_ratings_helper.sh stats"
else
    echo "   python3 plex_ratings_sync.py --plex-db /chemin/vers/plex.db --stats"
fi

echo
echo "2. 🎭 Faire une simulation de suppression:"
if [ "$plex_found" = true ]; then
    echo "   ./plex_ratings_helper.sh simulate"
else
    echo "   python3 plex_ratings_sync.py --plex-db /chemin/vers/plex.db"
fi

echo
echo "3. 🗑️ Suppression réelle (avec sauvegarde):"
if [ "$plex_found" = true ]; then
    echo "   ./plex_ratings_helper.sh delete"
else
    echo "   python3 plex_ratings_sync.py --plex-db /chemin/vers/plex.db --delete --backup ~/backup"
fi

echo
echo -e "${BLUE}📚 Ressources:${NC}"
echo "   📖 Documentation: cat PLEX_RATINGS_README.md"
echo "   🔧 Configuration: $config_file"
echo "   🎮 Assistant interactif: ./plex_ratings_helper.sh"

# Proposer une démonstration
echo
read -p "🎮 Voulez-vous lancer l'assistant interactif maintenant ? (o/N): " launch_demo

if [[ "$launch_demo" =~ ^[Oo]$ ]]; then
    echo -e "\n${BLUE}🚀 Lancement de l'assistant...${NC}"
    exec "$script_dir/plex_ratings_helper.sh"
fi

echo -e "\n${GREEN}✅ Installation complète ! Bon nettoyage de votre bibliothèque ! 🎵${NC}"