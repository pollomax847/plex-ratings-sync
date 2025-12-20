# 🚀 PLEX RATINGS - AUTOMATION COMPLÈTE

## ⚡ Installation en UNE seule commande

```bash
./auto_install_everything.sh
```

**Et c'est TOUT !** Plus rien à faire manuellement, JAMAIS.

---

## 🎯 Système entièrement automatique

### 🎧 Vous (utilisateur)
- Écoutez vos morceaux dans PlexAmp
- Évaluez avec des étoiles selon vos goûts
- **C'est tout !** Le reste est automatique

### 🤖 Le système (automatique)
- **Fin de mois** → Analyse Plex + Suppression 1⭐ + Scan 2⭐
- **Sauvegarde** → Tout avant suppression
- **Nettoyage** → Anciens logs et sauvegardes
- **Rapport** → Statistiques JSON + logs

---

## ⭐ Logique simple

| Étoiles | Action automatique |
|---------|-------------------|
| 1⭐ | 🗑️ Suppression définitive (avec sauvegarde) |
| 2⭐ | 🔍 Scan songrec-rename (correction métadonnées) |
| 3⭐ | ✅ Conservation |
| 4⭐ | ✅ Conservation |
| 5⭐ | ✅ Conservation |

---

## 📅 Planning automatique

- **Dernier jour du mois à 2h** → Traitement complet
- **Lundi à 1h** → Vérification système
- **Quotidien** → Logs automatiques
- **Vous** → Aucune action requise !

---

## 🛠️ Fichiers créés

### Scripts d'installation
- `auto_install_everything.sh` - Installation complète en une commande
- `auto_maintenance.sh` - Maintenance automatique 
- `demo_automatic_workflow.sh` - Démonstration du fonctionnement

### Scripts de workflow
- `plex_monthly_workflow.sh` - Workflow mensuel automatique
- `plex_ratings_sync.py` - Moteur de synchronisation
- Tous les autres scripts de support

### Documentation
- `AUTO_README.md` - Guide d'utilisation automatique
- `WORKFLOW_README.md` - Documentation complète
- Configuration automatique dans `~/.plex_ratings_config`

---

## 🔧 Commandes utiles

```bash
# Installation complète (une seule fois)
./auto_install_everything.sh

# Voir la démonstration
./demo_automatic_workflow.sh

# Vérifier les logs en temps réel
tail -f ~/logs/plex_auto.log

# Voir le résumé du mois
cat ~/logs/monthly_summary_$(date +%Y%m).json

# Maintenance manuelle (si besoin)
./auto_maintenance.sh

# Test manuel (simulation)
./plex_monthly_workflow.sh
```

---

## 🎯 Configuration de Paul

- **Bibliothèque** : `/mnt/mybook/itunes/Music`
- **Automatisation** : Fin de mois (cron)
- **1⭐** → Suppression auto
- **2⭐** → songrec-rename auto
- **Aucune intervention manuelle** required

---

## ✨ Avantages de l'automation complète

✅ **Zéro maintenance** - Tout se fait automatiquement  
✅ **Sécurité maximale** - Sauvegardes avant suppressions  
✅ **Optimisation continue** - Bibliothèque toujours propre  
✅ **Tranquillité d'esprit** - Logs et vérifications auto  
✅ **Temps libre** - Plus de gestion manuelle !  

---

## 🎵 Résultat

**Vous évaluez → Le système optimise → Votre bibliothèque s'améliore automatiquement !**

*Installation : 5 minutes*  
*Maintenance : 0 minute/mois*  
*Résultat : Bibliothèque parfaitement optimisée en permanence*

---

**🚀 Un seul script, une installation, une vie plus simple ! 🎵**