#!/usr/bin/env bash
# unified_audio_manager.sh — minimal, safe audio helper

set -euo pipefail
IFS=$'\n\t'

ROOT_DEFAULT="$HOME/Downloads/YouTube"
QUARANTINE_DIR="${ROOT_DEFAULT%/}/quarantine"

choose_root() {
  read -e -p "Chemin du dossier à traiter [${ROOT_DEFAULT}]: " root
  root=${root:-$ROOT_DEFAULT}
  if [ ! -d "$root" ]; then
    echo "Le répertoire n'existe pas : $root"
    return 1
  fi
  ROOT="$root"
}

nice_print() { echo -e "\n==> $*"; }

report() {
  nice_print "Génération du rapport non destructif pour: $ROOT"
  total=$(find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.opus" \) | wc -l)
  echo "Total audio: $total"
  echo "Top 5 récents:"
  find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.opus" \) -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2- | head -5
  echo "Top 5 par taille:"
  find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.opus" \) -printf '%s %p\n' | sort -nr | head -5 | awk '{printf "%s bytes %s\n", $1, substr($0, index($0,$2))}'
}

organize_by_tags() {
  nice_print "Organisation par tags (déplace les fichiers vers Artiste/Album si tags trouvés)."
  read -p "Confirmez-vous (o/N) ? " confirm
  if [[ ! "$confirm" =~ ^[oO] ]]; then
    echo "Annulé."
    return 0
  fi

  count=0
  find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" \) -print0 |
  while IFS= read -r -d '' f; do
    if command -v eyeD3 >/dev/null 2>&1; then
      artist=$(eyeD3 --no-color "$f" 2>/dev/null | grep -i "artist:" | sed 's/.*artist: //' | head -n1 || true)
      album=$(eyeD3 --no-color "$f" 2>/dev/null | grep -i "album:" | sed 's/.*album: //' | head -n1 || true)
    else
      artist=""
      album=""
    fi

    if [ -n "$artist" ] && [ -n "$album" ]; then
      safe_artist=$(echo "$artist" | sed 's/[\\/:*?"<>|]/_/g')
      safe_album=$(echo "$album" | sed 's/[\\/:*?"<>|]/_/g')
      target="$ROOT/$safe_artist/$safe_album"
      mkdir -p "$target"
      mv -n "$f" "$target/" && echo "Déplacé: $(basename "$f") -> $safe_artist/$safe_album" && count=$((count+1))
    fi
  done
  echo "Fichiers déplacés: $count"
}

clean_secure() {
  nice_print "Nettoyage sécurisé: corrompus et fichiers <60s seront déplacés vers $QUARANTINE_DIR"
  read -p "Confirmez-vous (o/N) ? " confirm
  if [[ ! "$confirm" =~ ^[oO] ]]; then
    echo "Annulé."
    return 0
  fi

  mkdir -p "$QUARANTINE_DIR"
  dcount=0
  scount=0

  find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.opus" -o -iname "*.wav" \) -print0 |
  while IFS= read -r -d '' f; do
    if ! timeout 6s ffmpeg -v error -i "$f" -f null - >/dev/null 2>&1; then
      mv -n "$f" "$QUARANTINE_DIR/" && echo "Corrompu -> quarantine: $(basename "$f")" && dcount=$((dcount+1))
    fi
  done

  find "$ROOT" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.m4a" -o -iname "*.opus" -o -iname "*.wav" \) -print0 |
  while IFS= read -r -d '' f; do
    dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f" 2>/dev/null || echo 0)
    dur=${dur%%.*}
    if [ -n "$dur" ] && [ "$dur" -lt 60 ] 2>/dev/null; then
      mv -n "$f" "$QUARANTINE_DIR/" && echo "Court -> quarantine: $(basename "$f") (${dur}s)" && scount=$((scount+1))
    fi
  done

  echo "Déplacés vers quarantine: fichiers corrompus: $dcount, fichiers courts: $scount"
}

main_menu() {
  echo "\n=== GESTION AUDIO (simplifié) ==="
  echo "Répertoire par défaut: $ROOT_DEFAULT"
  echo "1) Rapport non destructif"
  echo "2) Organiser par tags (déplacer)"
  echo "3) Nettoyage sécurisé (déplacer corrompus/courts -> quarantine)"
  echo "0) Quitter"
  read -p "Votre choix: " choice
  case "$choice" in
    1) choose_root && report ;;
    2) choose_root && organize_by_tags ;;
    3) choose_root && clean_secure ;;
    0) echo "Au revoir."; exit 0 ;;
    *) echo "Choix invalide." ;;
  esac
}

# Vérification syntaxe rapide
if ! bash -n "$0" 2>/dev/null; then
  echo "Erreur de syntaxe dans le script."; exit 1
fi

# Boucle principale
while true; do
  main_menu
  echo "\nAppuyez Entrée pour continuer..."
  read -r
  break
done
