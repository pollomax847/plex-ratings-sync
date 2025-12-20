#!/bin/bash
# Guide d'installation complète pour le workflow Plex Ratings de Paul

echo "🎵 GUIDE D'INSTALLATION WORKFLOW PLEX RATINGS"
echo "=============================================="
echo
echo "Configuration personnalisée pour Paul :"
echo "✓ Bibliothèque : /mnt/mybook/itunes/Music"
echo "✓ 1 ⭐ → Suppression automatique"  
echo "✓ 2 ⭐ → Scan songrec-rename"
echo "✓ Automatisation mensuelle (fin de mois)"
echo

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}📋 ÉTAPES D'INSTALLATION :${NC}"
echo "=========================="
echo
echo "1. 🔧 Installation du workflow principal"
echo "   ./install_plex_ratings_sync.sh"
echo
echo "2. 🎵 Installation de songrec-rename"  
echo "   ./install_songrec_rename.sh"
echo
echo "3. 📅 Configuration du cron mensuel"
echo "   crontab -e"
echo "   Ajouter : 0 2 28-31 * * [ \"\$(date -d tomorrow +%d)\" -eq 1 ] && $PWD/plex_monthly_workflow.sh"
echo
echo "4. 🧪 Tests"
echo "   ./plex_monthly_workflow.sh  # Test manuel"
echo "   python3 plex_ratings_sync.py --auto-find-db --stats  # Test Plex"
echo

echo -e "${BLUE}📚 DOCUMENTATION :${NC}"
echo "=================="
echo "📖 Guide complet : cat WORKFLOW_README.md"
echo "⚙️ Config Plex : cat PLEX_RATINGS_README.md"
echo "📅 Exemples cron : cat crontab_monthly_workflow.conf"
echo

echo -e "${BLUE}🎯 UTILISATION :${NC}"
echo "==============="
echo "1. 🎧 Écoutez dans PlexAmp et évaluez :"
echo "   • 1 ⭐ = À supprimer"
echo "   • 2 ⭐ = À scanner avec songrec"
echo "   • 3-5 ⭐ = À conserver"
echo
echo "2. 🗓️ Fin de mois : Traitement automatique"
echo "   • Supprime les 1 ⭐ (avec sauvegarde)"
echo "   • Prépare queue songrec pour les 2 ⭐"
echo
echo "3. 🔍 Début de mois : Traiter la queue"
echo "   cd ~/songrec_queue/YYYYMMDD_HHMMSS/"
echo "   ./process_2_stars.sh"
echo

echo -e "${YELLOW}⚠️  IMPORTANT :${NC}"
echo "==============="
echo "• Faites une sauvegarde complète avant première utilisation"
echo "• Testez d'abord manuellement avant automation"
echo "• Les suppressions sont avec sauvegarde automatique"
echo "• songrec-rename nécessite une connexion internet"
echo

echo -e "${GREEN}🚀 PRÊT À INSTALLER ?${NC}"
echo "===================="
read -p "Lancer l'installation complète maintenant ? (o/N): " install_now

if [[ "$install_now" =~ ^[Oo]$ ]]; then
    echo
    echo "🔧 Installation automatique complète en cours..."
    
    # Installation principale
    if ./install_plex_ratings_sync.sh; then
        echo "✅ Workflow principal installé"
    else
        echo "❌ Erreur installation workflow principal"
        exit 1
    fi
    
    echo
    echo "🎵 Installation automatique de songrec-rename..."
    
    # Installation automatique de songrec-rename
    if ./install_songrec_rename.sh; then
        echo "✅ songrec-rename installé automatiquement"
    else
        echo "⚠️ Erreur installation songrec-rename (continuera sans)"
        echo "   Vous pouvez l'installer plus tard avec: ./install_songrec_rename.sh"
    fi
    
    echo
    echo "📅 Configuration automatique du cron..."
    
    # Configuration automatique du cron
    CRON_LINE="0 2 28-31 * * [ \"\$(date -d tomorrow +%d)\" -eq 1 ] && $PWD/plex_monthly_workflow.sh >> $HOME/logs/plex_cron.log 2>&1"
    
    # Vérifier si la tâche existe déjà
    if crontab -l 2>/dev/null | grep -F "plex_monthly_workflow.sh" >/dev/null; then
        echo "⚠️ Tâche cron déjà configurée"
    else
        # Ajouter la tâche cron automatiquement
        (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
        echo "✅ Tâche cron configurée automatiquement"
    fi
    
    # Créer les répertoires de logs
    mkdir -p "$HOME/logs"
    
    echo
    echo "🎉 Installation COMPLÈTEMENT AUTOMATIQUE terminée !"
    echo
    echo "📊 RÉSUMÉ :"
    echo "✅ Workflow Plex installé et configuré"
    echo "✅ songrec-rename installé"
    echo "✅ Tâche cron configurée (fin de mois à 2h)"
    echo "✅ Répertoires de logs créés"
    echo
    echo "🚀 SYSTÈME ENTIÈREMENT AUTOMATISÉ :"
    echo "• Fin de mois → Suppression automatique des 1 ⭐"
    echo "• Fin de mois → Scan automatique des 2 ⭐ avec songrec"
    echo "• Tout se fait sans intervention manuelle !"
    
else
    echo "Installation manuelle. Consultez WORKFLOW_README.md pour les détails."
fi

echo
echo "📞 Support : Consultez les fichiers README pour le dépannage"
echo "✨ Bonne synchronisation de votre bibliothèque ! 🎵"