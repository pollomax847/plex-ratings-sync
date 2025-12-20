# ⭐ SYNCHRONISATION PLEX - GUIDE RAPIDE

## 🎯 Que s'est-il passé ?

Vous aviez une synchronisation des étoiles (ratings) Plex **une fois par mois**.  
Nous l'avons changée en synchronisation **chaque soir à 22h00**.

## 📋 Fichiers créés

| Fichier | Description |
|---------|-------------|
| `plex_daily_ratings_sync.sh` | Le script exécuté chaque soir |
| `crontab_daily_ratings_sync.conf` | Configuration cron avec tous les détails |
| `PLEX_DAILY_SYNC_INSTALLATION.md` | Guide complet d'installation |
| `PLEX_SYNC_SUMMARY.sh` | Résumé des changements |

## ⚡ Installation RAPIDE (2 minutes)

### Étape 1: Ouvrir cron
```bash
crontab -e
```

### Étape 2: Ajouter cette ligne
```
0 22 * * * /home/paulceline/bin/audio/plex_daily_ratings_sync.sh >> /home/paulceline/logs/plex_ratings/daily.log 2>&1
```

### Étape 3: Sauvegarder
Appuyez sur `Ctrl+X`, puis `Y`

### Étape 4: Vérifier
```bash
crontab -l | grep plex_daily
```

Vous devriez voir la ligne que vous venez d'ajouter ✅

## 🧪 Tester maintenant

```bash
# Test du script
/home/paulceline/bin/audio/plex_daily_ratings_sync.sh

# Voir les logs
tail -20 /home/paulceline/logs/plex_ratings/daily_sync_*.log
```

## 📊 Résumé

✅ **Fait:**
- Script de synchronisation quotidienne créé
- Configuration cron préparée
- Documentation complète fournie
- Tous les fichiers sont exécutables

🔄 **Prochaine étape:**
- Installer la cron (voir Étape 1 ci-dessus)
- Tester le script

⏰ **Calendrier:**
- Chaque soir à 22h00 = synchronisation automatique
- Logs dans: `/home/paulceline/logs/plex_ratings/`

---

**Questions ?** Consultez `PLEX_DAILY_SYNC_INSTALLATION.md` pour plus de détails.
