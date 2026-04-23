# 🎵 scripts — Suite d'automatisation Plex / iTunes / Audio

Collection de scripts Python et Bash pour gérer une bibliothèque musicale
**Plex Media Server** (+ iTunes XML historique) sous Linux : notes, playlists,
nettoyage, identification SongRec, synchronisation vers disques externes,
le tout orchestré par des **timers systemd**.

> 📖 **Démarrage rapide** : [TUTO.md](TUTO.md)
> 📘 **Guide iTunes XML** : [GUIDE_COMPLET.md](GUIDE_COMPLET.md)

---

## 🚀 Installation express

```bash
git clone <ton-repo> scripts && cd scripts
./install.sh
source .venv/bin/activate
```

Le script [install.sh](install.sh) détecte ton OS, installe les paquets apt
nécessaires (`python3-venv`, `sqlite3`, `ffmpeg`, `libnotify-bin`, `jq`…),
crée le virtualenv, installe [requirements.txt](requirements.txt), rend les
scripts exécutables et propose d'activer les timers systemd.

Options :

```bash
./install.sh --yes          # Non-interactif
./install.sh --no-apt       # Skip apt
./install.sh --no-systemd   # Skip systemd
./install.sh --help
```

---

## 🗂️ Organisation du dépôt

```
scripts/
├── install.sh              # Mise en place complète du projet
├── README.md               # Ce fichier
├── TUTO.md                 # Tutoriel pas-à-pas
├── GUIDE_COMPLET.md        # Guide iTunes XML détaillé
├── requirements.txt        # Dépendances Python (mutagen, plexapi, requests)
│
├── audio/                  # Tri, filtrage et renommage de fichiers audio
├── data/                   # Rapports, exports, JSON, sauvegardes
├── diagnostics/            # Inspections de la DB Plex (schéma, ratings…)
├── itunes/                 # Manipulation de la bibliothèque iTunes XML
├── maintenance/            # Rotation de logs, reload systemd
├── notifications/          # notify-send, sons, presets desktop
├── playlists/              # Export/import, M3U, Plexamp, sync MyBook
├── ratings/                # Sync ratings Plex ↔ tags ID3 (POPM)
├── systemd/                # Units .service + .timer (mode --user)
├── utils/                  # Petits utilitaires divers
└── workflows/              # Scripts chapeaux orchestrant plusieurs étapes
```

---

## 🧩 Composants principaux

### ⭐ Ratings Plex ↔ ID3 (POPM)

| Script | Rôle |
|---|---|
| [ratings/plex_rating_sync_complete.py](ratings/plex_rating_sync_complete.py) | Sync complète Plex → fichiers (MP3/MP4/FLAC/Ogg) |
| [ratings/plex_ratings_sync.py](ratings/plex_ratings_sync.py) | Sync incrémentale |
| [ratings/sync_ratings_to_id3.py](ratings/sync_ratings_to_id3.py) | Export vers tags ID3 uniquement |
| [ratings/plex_daily_ratings_sync.sh](ratings/plex_daily_ratings_sync.sh) | Wrapper quotidien (systemd) |
| [ratings/plex_ratings_helper.sh](ratings/plex_ratings_helper.sh) | Aperçu interactif |

### 🎶 Workflows 1⭐ / 2⭐

| Script | Rôle |
|---|---|
| [workflows/plex_daily_workflow.sh](workflows/plex_daily_workflow.sh) | Pipeline complet : 1⭐ → suppression, 2⭐ → queue SongRec |
| [audio/auto_cleanup_2_stars.sh](audio/auto_cleanup_2_stars.sh) | Traite les queues SongRec terminées |
| [audio/rename_1_star_with_songrec.py](audio/rename_1_star_with_songrec.py) | Réidentification acoustique |
| [audio/find_1_star_audios.py](audio/find_1_star_audios.py) | Liste les 1⭐ dans la DB |
| [audio/filter_audio_by_genre.py](audio/filter_audio_by_genre.py) | Filtrage par genre ID3 |

### 📝 Playlists

| Script | Rôle |
|---|---|
| [playlists/export_plex_playlist.py](playlists/export_plex_playlist.py) | Export Plex → M3U |
| [playlists/sync_m3u_playlists.py](playlists/sync_m3u_playlists.py) | Sync bidirectionnelle M3U |
| [playlists/auto_playlists_plexamp.py](playlists/auto_playlists_plexamp.py) | Génération intelligente (Plexamp) |
| [playlists/import_itunes_playlists_to_plex.py](playlists/import_itunes_playlists_to_plex.py) | Import depuis iTunes XML |
| [playlists/sync_plex_playlists_to_mybook.sh](playlists/sync_plex_playlists_to_mybook.sh) | Copie vers disque MyBook |

### 💿 iTunes XML

| Script | Rôle |
|---|---|
| [itunes/itunes_complete_manager.py](itunes/itunes_complete_manager.py) | Interface menu interactive |
| [itunes/itunes_analyzer.py](itunes/itunes_analyzer.py) | Stats, formats, genres, chemins |
| [itunes/itunes_path_updater.py](itunes/itunes_path_updater.py) | Correction chemins Windows → Linux |
| [itunes/itunes_editor.py](itunes/itunes_editor.py) | Modifications en masse (regex, replace) |

Voir [GUIDE_COMPLET.md](GUIDE_COMPLET.md) pour le détail.

### 🔍 Diagnostics

Petits scripts de lecture seule pour auditer la DB Plex : schéma, présence
d'items, structure des ratings, etc. — voir le dossier [diagnostics](diagnostics).

### 🔔 Notifications

[notifications/audio_notifications.sh](notifications/audio_notifications.sh) — système unifié (desktop + console + son)
utilisé par les workflows. Configurable via variables d'environnement
(`NOTIFICATION_APP_NAME`, `NOTIFICATION_ENABLE_DESKTOP`, …). Voir
[notifications/audio_notifications_README.md](notifications/audio_notifications_README.md).

---

## ⏰ Automatisation (systemd --user)

Les units dans [systemd/](systemd/) sont copiées par `install.sh` dans
`~/.config/systemd/user/`.

| Timer | Fréquence | Service |
|---|---|---|
| `plex-ratings-sync.timer` | Quotidien 22h | Sync ratings Plex → ID3 |
| `plex-daily-workflow.timer` | Quotidien 02h | Workflow 1⭐/2⭐ |
| `plex-auto-playlists.timer` | Hebdomadaire | Playlists Plexamp |
| `plex-export-playlists.timer` | Quotidien | Export M3U |
| `plex-playlists-mybook-sync.timer` | Après export | Copie MyBook |

Activation typique :

```bash
systemctl --user enable --now plex-ratings-sync.timer
systemctl --user enable --now plex-daily-workflow.timer
systemctl --user list-timers
sudo loginctl enable-linger "$USER"   # pour rester actif hors session
```

---

## 📦 Dépendances

**Système** (apt) : `python3 python3-venv sqlite3 ffmpeg libnotify-bin jq curl rsync git`
+ [songrec](https://github.com/marin-m/SongRec) (optionnel, workflow 2⭐).

**Python** (voir [requirements.txt](requirements.txt)) : `mutagen`, `plexapi`, `requests`.

---

## ⚙️ Configuration

Certaines variables sont à ajuster une seule fois :

```bash
# Dans ~/.bashrc ou ~/.zshrc
export PLEX_DB="$HOME/.var/app/tv.plex.PlexMediaServer/data/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
export AUDIO_LIBRARY="$HOME/Musiques"
```

Voir [TUTO.md](TUTO.md#3-configuration) pour tous les chemins possibles.

---

## 🛟 Sécurité & bonnes pratiques

- **Aucune écriture directe** dans la DB Plex : les scripts travaillent sur une
  copie temporaire (Plex verrouille sa DB quand il tourne).
- **Sauvegardes automatiques** avant toute modification d'un fichier
  (`.backup_YYYYMMDD_HHMMSS`).
- **Mode `--dry-run`** disponible sur les scripts modifiants — **toujours
  l'utiliser la première fois**.
- **Logs centralisés** dans `~/.plex/logs/` et `~/logs/plex_ratings/`.

---

## 🆘 Dépannage

Voir la section dédiée : [TUTO.md § 7](TUTO.md#7-dépannage).

Commandes utiles :

```bash
# Vérifier un timer
systemctl --user status plex-ratings-sync.timer
journalctl --user -u plex-ratings-sync.service -n 200

# Relancer l'installation
./install.sh --yes
```

---

## 📄 Licence

Usage personnel. Adapte les chemins et configs à ton environnement.
