#!/bin/bash
# Script d'installation automatique pour Plex Ratings Sync
# Ce script installe toutes les dépendances nécessaires

set -e  # Arrêter en cas d'erreur

echo "🎵 Installation de Plex Ratings Sync"
echo "===================================="

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Détection du système d'exploitation
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "❌ Système d'exploitation non supporté: $OSTYPE"
    exit 1
fi

echo "🔍 Système détecté: $OS"

# Installation de Python 3 et pip
echo ""
echo "🐍 Vérification de Python 3..."
if ! command_exists python3; then
    echo "❌ Python 3 n'est pas installé."
    if [[ "$OS" == "linux" ]]; then
        echo "📦 Installation sur Ubuntu/Debian:"
        echo "   sudo apt update && sudo apt install python3 python3-pip"
    else
        echo "📦 Installation sur macOS:"
        echo "   brew install python3"
    fi
    exit 1
else
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION trouvé"
fi

# Installation de pip si nécessaire
if ! command_exists pip3; then
    echo "❌ pip3 n'est pas installé."
    if [[ "$OS" == "linux" ]]; then
        echo "📦 Installation: sudo apt install python3-pip"
    fi
    exit 1
else
    echo "✅ pip3 trouvé"
fi

# Installation de songrec
echo ""
echo "🎵 Installation de songrec (identification audio)..."
if ! command_exists songrec; then
    echo "📦 Installation de songrec..."
    pip3 install songrec
    if [ $? -eq 0 ]; then
        echo "✅ songrec installé avec succès"
    else
        echo "❌ Échec de l'installation de songrec"
        echo "💡 Vous pouvez l'installer manuellement avec: pip3 install songrec"
    fi
else
    SONGREC_VERSION=$(songrec --version 2>/dev/null || echo "version inconnue")
    echo "✅ songrec trouvé ($SONGREC_VERSION)"
fi

# Installation des dépendances Python
echo ""
echo "📦 Installation des dépendances Python..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✅ Dépendances Python installées"
else
    echo "⚠️ Fichier requirements.txt non trouvé"
fi

# Vérification de l'installation
echo ""
echo "🔍 Vérification de l'installation..."

# Test du script principal
if [ -f "plex_ratings_sync.py" ]; then
    echo "🧪 Test du script principal..."
    if python3 -m py_compile plex_ratings_sync.py; then
        echo "✅ Script plex_ratings_sync.py : OK"
    else
        echo "❌ Script plex_ratings_sync.py : ERREUR de compilation"
    fi
else
    echo "❌ Script plex_ratings_sync.py non trouvé"
fi

# Test du script de notifications
if [ -f "plex_notifications.sh" ]; then
    echo "🧪 Test du script de notifications..."
    if [ -x "plex_notifications.sh" ]; then
        echo "✅ Script plex_notifications.sh : OK (exécutable)"
    else
        chmod +x plex_notifications.sh
        echo "✅ Script plex_notifications.sh : OK (rendu exécutable)"
    fi
else
    echo "❌ Script plex_notifications.sh non trouvé"
fi

echo ""
echo "🎉 Installation terminée !"
echo ""
echo "🚀 Utilisation rapide :"
echo "   Simulation: python3 plex_ratings_sync.py --auto-find-db"
echo "   Suppression: python3 plex_ratings_sync.py --auto-find-db --delete --backup ./backup"
echo "   Statistiques: python3 plex_ratings_sync.py --auto-find-db --stats"
echo ""
echo "📖 Consultez README_PLEX.md pour plus d'informations"
echo ""
echo "🛡️ CONSEIL: Testez toujours en mode simulation d'abord !"