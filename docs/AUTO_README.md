# 🚀 Plex Ratings - Système 100% Automatique

## ⚡ Installation en une commande

```bash
./auto_install_everything.sh
```

**C'est tout !** Rien d'autre à faire manuellement.

## 🎯 Comment ça marche

1. **🎧 Vous écoutez** dans PlexAmp et notez vos morceaux
2. **🤖 Le système fait tout** automatiquement chaque fin de mois :
   - Supprime les fichiers 1⭐ (avec sauvegarde)
   - Scanne les fichiers 2⭐ avec songrec-rename
   - Nettoie et archive automatiquement

## ⭐ Logique des étoiles

- **1⭐** → 🗑️ Suppression automatique
- **2⭐** → 🔍 Scan automatique songrec-rename  
- **3-5⭐** → ✅ Conservation

## 📅 Automatisation

- **Fin de mois** (dernier jour à 2h) → Traitement automatique complet
- **Lundi** (1h) → Vérification automatique du système
- **Logs automatiques** → `~/logs/plex_auto.log`
- **Sauvegardes automatiques** → `~/plex_backup/`

## 🎵 Utilisation

1. **Évaluez dans PlexAmp** selon votre ressenti
2. **Laissez faire le système** - tout est automatique !
3. **Vérifiez occasionnellement** les logs si vous voulez

```bash
# Voir les logs en temps réel
tail -f ~/logs/plex_auto.log

# Voir le résumé du dernier mois
cat ~/logs/monthly_summary_$(date +%Y%m).json
```

## 🛡️ Sécurité

- ✅ **Sauvegarde automatique** avant toute suppression
- ✅ **Logs détaillés** de toutes les opérations
- ✅ **Vérifications automatiques** du système
- ✅ **Aucune suppression** sans evaluation préalable

## 🏗️ Architecture

```
Vous → PlexAmp (évaluation) → Plex Database
                                    ↓
Fin de mois → Cron → Workflow automatique
                           ↓
              Suppression 1⭐ + Scan 2⭐
                           ↓
                   Sauvegarde + Logs
```

## 📊 Monitoring

Le système génère automatiquement :
- **Logs mensuels** avec statistiques
- **Résumés JSON** pour analyse
- **Rapports email** (optionnel)
- **Vérifications système** hebdomadaires

## 🔧 Maintenance

**Aucune maintenance manuelle requise !**

Le système s'auto-maintient :
- Nettoie les anciens logs automatiquement
- Supprime les anciennes sauvegardes (>3 mois)
- Vérifie son bon fonctionnement
- Répare les problèmes mineurs

## ❓ En cas de problème

```bash
# Vérification automatique du système
./auto_maintenance.sh

# Test manuel (sans suppression)
./plex_monthly_workflow.sh  # puis Ctrl+C avant les suppressions

# Réinstallation complète
./auto_install_everything.sh
```

---

**✨ Système entièrement automatisé - Aucune intervention manuelle requise ! 🎵**