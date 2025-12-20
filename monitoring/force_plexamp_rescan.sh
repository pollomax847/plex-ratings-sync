#!/bin/bash
# Script pour forcer Plexamp à relire les métadonnées mises à jour

echo "🔄 Force Plexamp à rescanner les métadonnées..."
echo ""

# Fonction pour vérifier si Plexamp est en cours d'exécution
check_plexamp_running() {
    if pgrep -f "plexamp" > /dev/null; then
        echo "⚠️ Plexamp semble être en cours d'exécution"
        echo "Fermez Plexamp avant de continuer (appuyez sur Entrée quand c'est fait)"
        read -r
    fi
}

# Méthode 1: Nettoyer le cache
echo "🗑️ Méthode 1: Nettoyage du cache Plexamp..."
CACHE_LOCATIONS=(
    "$HOME/.config/plexamp"
    "$HOME/.plexamp"
    "$HOME/.config/Plexamp"
    "$HOME/Library/Application Support/Plexamp"  # macOS
    "$HOME/AppData/Local/Plexamp"  # Windows
)

for cache_dir in "${CACHE_LOCATIONS[@]}"; do
    if [ -d "$cache_dir" ]; then
        echo "Nettoyage: $cache_dir"
        # Supprimer seulement les fichiers de cache, pas la config
        find "$cache_dir" -name "*cache*" -type f -delete 2>/dev/null || true
        find "$cache_dir" -name "*.db*" -type f -delete 2>/dev/null || true
        rm -rf "$cache_dir/cache" 2>/dev/null || true
        rm -rf "$cache_dir/Cache" 2>/dev/null || true
    fi
done

# Méthode 2: Créer un fichier de trigger pour forcer le rescan
echo ""
echo "🔧 Méthode 2: Création de triggers de rescan..."
TRIGGER_FILE="$HOME/.plexamp_rescan_trigger"
touch "$TRIGGER_FILE"
echo "Trigger créé: $TRIGGER_FILE"

# Méthode 3: Instructions pour l'utilisateur
echo ""
echo "✅ Cache nettoyé!"
echo ""
echo "📋 Actions à faire maintenant:"
echo "1. Ouvrez Plexamp"
echo "2. Allez dans Paramètres > Bibliothèque"
echo "3. Cliquez sur 'Rescanner la bibliothèque' ou 'Recharger métadonnées'"
echo "4. Les nouveaux ratings devraient apparaître!"
echo ""
echo "💡 Si ça ne marche pas, essayez de:"
echo "   - Redémarrer complètement Plexamp"
echo "   - Vérifier que les fichiers sont accessibles"
echo "   - Attendre quelques minutes pour que Plexamp analyse les changements"

# Nettoyer le trigger après 1 heure
(sleep 3600 && rm -f "$TRIGGER_FILE") &

echo ""
echo "🎵 Prêt! Ouvrez Plexamp et rescanner votre bibliothèque."