#!/bin/bash

# Vérifier que yad est installé
if ! command -v yad &> /dev/null; then
  echo "yad n'est pas installé. Installez-le avec : sudo apt install yad"
  exit 1
fi

# TEST_MODE: if set to 1, skip all yad dialogs and read configuration from env vars:
#   SRC_DIR, DST_DIR, FORMATS (csv), OUT_FMT, BITRATE
# This is non-destructive and only activated when TEST_MODE=1.
TEST_MODE=${TEST_MODE:-0}
# Note: songrec-rename removed — not used here

# Sélection dossier source
ask_retry() {
  local msg="$1"
  yad --question --title="Annulation" --text="$msg\n\nVoulez-vous réessayer ?" --button="Réessayer":0 --button="Quitter":1
  return $?
}

if [ "$TEST_MODE" -eq 1 ]; then
  if [ -z "$SRC_DIR" ]; then
    echo "TEST_MODE: SRC_DIR must be set in environment" >&2
    exit 1
  fi
  echo "TEST_MODE: using SRC_DIR=$SRC_DIR"
else
  while true; do
    SRC_DIR=$(yad --file-selection --directory --title="Choisir le dossier source contenant les fichiers audio")
    [ -n "$SRC_DIR" ] && break
    if ask_retry "Aucun dossier source sélectionné."; then
      continue
    else
      exit 1
    fi
  done
fi
# Normaliser le chemin source en absolu et sans slash final
if command -v realpath >/dev/null 2>&1; then
  SRC_DIR=$(realpath "$SRC_DIR")
else
  SRC_DIR="${SRC_DIR%/}"
fi

# Sélection dossier destination
if [ "$TEST_MODE" -eq 1 ]; then
  if [ -z "$DST_DIR" ]; then
    echo "TEST_MODE: DST_DIR must be set in environment" >&2
    exit 1
  fi
  echo "TEST_MODE: using DST_DIR=$DST_DIR"
else
  while true; do
    DST_DIR=$(yad --file-selection --directory --title="Choisir le dossier de destination pour les fichiers convertis")
    [ -n "$DST_DIR" ] && break
    if ask_retry "Aucun dossier de destination sélectionné."; then
      continue
    else
      exit 1
    fi
  done
fi
# Normaliser le chemin de destination en absolu et sans slash final
if command -v realpath >/dev/null 2>&1; then
  DST_DIR=$(realpath "$DST_DIR")
else
  DST_DIR="${DST_DIR%/}"
fi

# Choix des formats audio à inclure
if [ "$TEST_MODE" -eq 1 ]; then
  if [ -z "$FORMATS" ]; then
    echo "TEST_MODE: FORMATS must be set in environment (csv of checkboxes)" >&2
    exit 1
  fi
  echo "TEST_MODE: using FORMATS=$FORMATS"
else
  while true; do
    FORMATS=$(yad --form --separator="," --title="Formats à inclure" \
      --field="MP3:CHK" TRUE \
      --field="WAV:CHK" TRUE \
      --field="FLAC:CHK" TRUE \
      --field="AAC:CHK" FALSE \
      --field="M4A:CHK" FALSE \
      --field="OGG:CHK" FALSE \
      --field="Autres (tous):CHK" FALSE)
    [ -n "$FORMATS" ] && break
    if ask_retry "Aucun format sélectionné."; then
      continue
    else
      exit 1
    fi
  done
fi

# Choix du format de sortie
if [ "$TEST_MODE" -eq 1 ]; then
  if [ -z "$OUT_FMT" ]; then
    echo "TEST_MODE: OUT_FMT must be set in environment" >&2
    exit 1
  fi
  echo "TEST_MODE: using OUT_FMT=${OUT_FMT:-mp3}"
else
  while true; do
    OUT_FMT=$(yad --list --radiolist --title="Format de sortie" --column="Choix" --column="Format" TRUE "mp3" FALSE "opus" FALSE "ogg" FALSE "flac" --separator="|" --height=200 --width=300)
    OUT_FMT=$(echo "$OUT_FMT" | cut -d'|' -f2)
    [ -n "$OUT_FMT" ] && break
    if ask_retry "Aucun format de sortie sélectionné."; then
      continue
    else
      exit 1
    fi
  done
fi

# Info sur les débits
INFO_DEBIT="Débits recommandés :\n\nOpus : 96-128 kbps (musique), 64 kbps (voix)\nOgg : 128-192 kbps\nMP3 : 128-192 kbps (musique), 192-320 kbps (qualité CD)"
yad --info --title="Aide sur le débit" --text="$INFO_DEBIT"

# Menu déroulant pour le débit
if [ "$TEST_MODE" -eq 1 ]; then
  if [ -z "$BITRATE" ]; then
    echo "TEST_MODE: BITRATE must be set in environment" >&2
    exit 1
  fi
  echo "TEST_MODE: using BITRATE=${BITRATE}k"
else
  BITRATE=$(yad --list --title="Choisir le débit (kbps)" --column="Choix" --column="Débit" --column="Description" \
    TRUE "64" "Voix, très léger" \
    FALSE "96" "Musique légère, Opus recommandé" \
    FALSE "128" "Bonne qualité générale" \
    FALSE "160" "Très bonne qualité" \
    FALSE "192" "Qualité élevée" \
    FALSE "256" "Qualité quasi-CD" \
    FALSE "320" "Qualité maximale MP3" \
    FALSE "Autre..." "Entrer une valeur personnalisée" --separator="|" --height=300 --width=400)

  while true; do
    BITRATE=$(echo "$BITRATE" | cut -d'|' -f2)
    if [ "$BITRATE" = "Autre..." ]; then
      BITRATE=$(yad --entry --title="Débit personnalisé (en kbps)" --entry-text="128")
    fi
    BITRATE=$(echo "$BITRATE" | grep -oE '^[0-9]+' || true)
    [ -n "$BITRATE" ] && break
    if ask_retry "Aucun débit sélectionné."; then
      BITRATE=$(yad --list --title="Choisir le débit (kbps)" --column="Choix" --column="Débit" --column="Description" \
        TRUE "64" "Voix, très léger" \
        FALSE "96" "Musique légère, Opus recommandé" \
        FALSE "128" "Bonne qualité générale" \
        FALSE "160" "Très bonne qualité" \
        FALSE "192" "Qualité élevée" \
        FALSE "256" "Qualité quasi-CD" \
        FALSE "320" "Qualité maximale MP3" \
        FALSE "Autre..." "Entrer une valeur personnalisée" --separator="|" --height=300 --width=400)
      continue
    else
      exit 1
    fi
  done
fi

# Option pour supprimer les originaux
if [ "$TEST_MODE" -eq 1 ]; then
  DELETE_ORIGINALS=${DELETE_ORIGINALS:-FALSE}
  PARALLEL=${PARALLEL:-4}
  echo "TEST_MODE: using DELETE_ORIGINALS=$DELETE_ORIGINALS"
  echo "TEST_MODE: using PARALLEL=$PARALLEL"
else
  OPTIONS=$(yad --form --separator="," --title="Options supplémentaires" \
    --field="Supprimer les originaux après conversion:CHK" FALSE \
    --field="Nombre de conversions en parallèle (1-8, 4=par défaut):NUM" 4!1..8!1)
  DELETE_ORIGINALS=$(echo "$OPTIONS" | cut -d',' -f1)
  PARALLEL=$(echo "$OPTIONS" | cut -d',' -f2)
fi

# Parser les formats sélectionnés
IFS=',' read -r mp3 wav flac aac m4a ogg autres <<< "$FORMATS"

exts=()
[ "$mp3" = "TRUE" ] && exts+=("mp3")
[ "$wav" = "TRUE" ] && exts+=("wav")
[ "$flac" = "TRUE" ] && exts+=("flac")
[ "$aac" = "TRUE" ] && exts+=("aac")
[ "$m4a" = "TRUE" ] && exts+=("m4a")
[ "$ogg" = "TRUE" ] && exts+=("ogg")
if [ "$autres" = "TRUE" ]; then
  # "Autres (tous)" -> parcourir toutes les extensions audio communes
  exts=("mp3" "wav" "flac" "m4a" "m4b" "aac" "ogg" "opus" "aiff" "alac")
fi

# Conversion
count=0
repaired=0
failed=0

# When set, MAX_SCAN limits number of files processed (useful for testing).
MAX_SCAN=${MAX_SCAN:-}

# Parallélisation
max_parallel=${PARALLEL:-4}
running=0
pids=()

echo "Début de la conversion... (parallèle: $max_parallel)"

# Fichier temporaire pour les résultats
results_file=$(mktemp)

# Fonction pour traiter un fichier
process_file() {
  local file_abs="$1"
  local rel_path="${file_abs#$SRC_DIR/}"
  local dest_file="$DST_DIR/${rel_path%.*}.$OUT_FMT"
  local dest_dir="$(dirname "$dest_file")"
  mkdir -p "$dest_dir"
  echo "Conversion de : $file_abs -> $dest_file"
  # Vérifier si le fichier est déjà au format de sortie (par extension seulement pour rapidité)
  local file_ext="${file_abs##*.}"
  if [ "${file_ext,,}" = "$OUT_FMT" ]; then
    echo "  -> Fichier déjà au format $OUT_FMT, ignoré."
    echo "SKIPPED" >> "$results_file"
    return
  fi
  local ARTIST TITLE AUDIO_CODEC
  ARTIST=$(ffprobe -v error -show_entries format_tags=artist -of default=noprint_wrappers=1:nokey=1 "$file_abs" 2>/dev/null || true)
  TITLE=$(ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$file_abs" 2>/dev/null || true)
  if { [ -z "$ARTIST" ] || [ -z "$TITLE" ]; }; then
    echo "  -> Métadonnées manquantes. Tentative de renommage depuis les tags..."
    local newfile=$(rename_by_tags "$file_abs" 2>/dev/null || true)
    if [ -n "$newfile" ]; then
      echo "  -> Fichier renommé en: $newfile"
      file_abs="$newfile"
      ARTIST=$(ffprobe -v error -show_entries format_tags=artist -of default=noprint_wrappers=1:nokey=1 "$file_abs" 2>/dev/null || true)
      TITLE=$(ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$file_abs" 2>/dev/null || true)
    else
      echo "  -> Renommage par tags impossible, continuer sans renommage."
    fi
  fi
  AUDIO_CODEC=$(get_audio_codec "$OUT_FMT")
  if ffmpeg -nostdin -loglevel error -y -i "$file_abs" -vn -c:a "$AUDIO_CODEC" -b:a "${BITRATE}k" "$dest_file"; then
    echo "  -> Conversion réussie."
    if [ "$DELETE_ORIGINALS" = "TRUE" ] && [ "$file_abs" != "$dest_file" ]; then
      rm "$file_abs"
      echo "  -> Original supprimé."
    fi
    echo "SUCCESS" >> "$results_file"
  else
    echo "  !! Erreur lors de la conversion de $file_abs. Tentative de réparation..."
    if ffmpeg -nostdin -loglevel error -y -err_detect ignore_err -i "$file_abs" -vn -c:a "$AUDIO_CODEC" -b:a "${BITRATE}k" "$dest_file"; then
      echo "  -> Réparation réussie."
      if [ "$DELETE_ORIGINALS" = "TRUE" ] && [ "$file_abs" != "$dest_file" ]; then
        rm "$file_abs"
        echo "  -> Original supprimé."
      fi
      echo "REPAIRED" >> "$results_file"
    else
      echo "  !! Échec de la réparation de $file_abs. Fichier ignoré."
      rm -f "$dest_file"
      echo "FAILED" >> "$results_file"
    fi
  fi
}

# Choisir le codec audio selon le format de sortie
get_audio_codec() {
  case "$1" in
    opus)
      echo "libopus" ;;
    ogg)
      echo "libvorbis" ;;
    mp3)
      echo "libmp3lame" ;;
    aac)
      echo "aac" ;;
    flac)
      echo "flac" ;;
    wav)
      echo "pcm_s16le" ;;
    m4a)
      echo "aac" ;;
    *)
      echo "libopus" ;;
  esac
}

# Renommer un fichier d'après ses tags (artist - title). Retourne le nouveau chemin si renommé.
rename_by_tags() {
  local file="$1"
  [ -z "$file" ] && return 1
  command -v ffprobe >/dev/null 2>&1 || return 1
  local artist title
  artist=$(ffprobe -v error -show_entries format_tags=artist -of default=noprint_wrappers=1:nokey=1 "$file")
  title=$(ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$file")
  [ -z "$artist" -a -z "$title" ] && return 1
  local dir ext safe_artist safe_title newname newpath i
  dir=$(dirname "$file")
  ext="${file##*.}"
  safe_artist=$(echo "${artist:-Unknown Artist}" | tr '/:' '_' | sed 's/[^[:alnum:][:space:]._,-]/_/g' | sed 's/  */ /g' | sed 's/^ //; s/ $//')
  safe_title=$(echo "${title:-Unknown Title}" | tr '/:' '_' | sed 's/[^[:alnum:][:space:]._,-]/_/g' | sed 's/  */ /g' | sed 's/^ //; s/ $//')
  newname="${safe_artist} - ${safe_title}.${ext}"
  newpath="$dir/$newname"
  i=1
  while [ -e "$newpath" ]; do
    newpath="$dir/${safe_artist} - ${safe_title} ($i).${ext}"
    i=$((i+1))
  done
  if mv -n -- "$file" "$newpath"; then
    printf '%s' "$newpath"
    return 0
  fi
  return 1
}

# Construire une recherche find unique via regex pour les extensions sélectionnées
ext_regex=$(printf "%s|" "${exts[@]}" | sed 's/|$//')
# Counter for MAX_SCAN tests
scanned=0
while IFS= read -r -d '' file; do
    # Assurer un chemin absolu pour le fichier (gère chemins absolus, relatifs, et relatifs à SRC_DIR)
    file_abs="$file"
    if [ -e "$file_abs" ]; then
      : # file_abs is fine
    else
      # try with SRC_DIR prefix (handles relative paths emitted by some find variants)
      if [ -e "$SRC_DIR/$file" ]; then
        file_abs="$SRC_DIR/$file"
      elif command -v realpath >/dev/null 2>&1; then
        # canonicalize (non-fatal)
        file_abs=$(realpath -m -- "$file" 2>/dev/null || printf '%s' "$file")
        # If realpath produced an absolute path under the current cwd because $file was relative
        # but actually starts with the SRC_DIR without leading slash (e.g. "tmp/..."), try prefixing '/'
        src_noslash=${SRC_DIR#/}
        if [ ! -e "$file_abs" ] && [ -n "$src_noslash" ] && case "$file" in "$src_noslash"* ) true;; *) false;; esac; then
          if [ -e "/$file" ]; then
            file_abs="/$file"
          fi
        fi
      else
        file_abs="$file"
      fi
    fi
    # Ignorer si le fichier n'existe pas
    if [ ! -f "$file_abs" ]; then
      echo "  -> Ignorer (missing): $file_abs"
      continue
    fi
    # (Accept filenames with newlines — find -print0 + read -d '' handles them)
    # Ignorer chemins trop longs
    if [ ${#file_abs} -gt 300 ]; then
      echo "  -> Ignorer (path too long): $file_abs"
      continue
    fi
    # Ignorer les fichiers non-audio (images, url, thm, etc.) en vérifiant le type MIME
    # Note: vérification MIME supprimée pour accélérer sur gros volumes
    :
    # Lancer la conversion en parallèle
    if [ $running -ge $max_parallel ]; then
      wait -n 2>/dev/null || wait
      running=$((running-1))
    fi
    process_file "$file_abs" &
    pids+=($!)
    running=$((running+1))
    scanned=$((scanned+1))
    if [ -n "$MAX_SCAN" ] && [ "$scanned" -ge "$MAX_SCAN" ]; then
      break
    fi
  done < <(find "$SRC_DIR" -type f -regextype posix-extended -iregex ".*\.(${ext_regex})$" -print0)

# Attendre la fin de toutes les conversions
for pid in "${pids[@]}"; do
  wait "$pid" 2>/dev/null
done

# Compter les résultats
count=$(grep -c "SUCCESS" "$results_file")
repaired=$(grep -c "REPAIRED" "$results_file")
failed=$(grep -c "FAILED" "$results_file")
skipped=$(grep -c "SKIPPED" "$results_file")

echo "Conversion terminée."
echo "Fichiers convertis : $count"
echo "Fichiers réparés : $repaired"
echo "Fichiers échoués : $failed"
echo "Fichiers ignorés : $skipped"

# Afficher un résumé final
if [ "$TEST_MODE" -eq 1 ]; then
  echo "TEST_MODE: Résumé - Convertis: $count, Réparés: $repaired, Échoués: $failed, Ignorés: $skipped"
else
  yad --info --title="Conversion terminée" --text="Résumé de la conversion :\n\nFichiers convertis : $count\nFichiers réparés : $repaired\nFichiers échoués : $failed\nFichiers ignorés : $skipped" --button="OK":0
fi

# Supprimer les dossiers vides
find "$DST_DIR" -type d -empty -delete