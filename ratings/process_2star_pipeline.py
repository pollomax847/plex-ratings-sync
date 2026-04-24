#!/usr/bin/env python3
"""
Pipeline complet pour les tracks 2★ dans Plex :
  1. Récupère les fichiers notés 2★ via l'API Plex (avec chemins réels)
  2. Lance `songrec-rename -i <fichier>` pour identifier et taguer en ID3
  3. Lance `beet import <fichier>` pour classer dans la bibliothèque Music
  4. Efface le rating 2★ via l'API Plex (la playlist [Auto] 2★ disparaît)

Usage (sur l'hôte) :
    python3 ratings/process_2star_pipeline.py              # mode réel
    python3 ratings/process_2star_pipeline.py --dry-run    # simulation (affiche les fichiers)
    python3 ratings/process_2star_pipeline.py --no-beet    # songrec-rename seulement
    python3 ratings/process_2star_pipeline.py --no-clear   # ne pas effacer le rating après

IMPORTANT : songrec-rename et beet doivent être installés sur la machine qui exécute ce script.
"""

import os
import sys
import argparse
import subprocess
import shutil
import json
import re
from pathlib import Path
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from mutagen import File as MutagenFile

PLEX_URL   = os.environ.get("PLEX_URL",   "http://localhost:32400").rstrip("/")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")

# Correspondance étoiles → valeur interne Plex (0-10 : 2★ = 4)
STARS_TO_PLEX = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}

# Chemin de remontée vers les fichiers réels (si exécuté depuis Docker, adapter via env)
# Sur l'hôte le chemin Plex retourne les chemins réels → aucune remontée nécessaire.
PLEX_PATH_PREFIX = os.environ.get("PLEX_PATH_PREFIX", "")   # ex. /home/paulceline/Musiques
DOCKER_PATH_PREFIX = os.environ.get("DOCKER_PATH_PREFIX", "")  # ex. /music


def _candidate_mappings() -> list[tuple[str, str]]:
    """Mappings connus entre chemins hôte Plex et chemins montés dans le conteneur."""
    pairs: list[tuple[str, str]] = []

    # Mapping explicite prioritaire (rétrocompatibilité)
    if PLEX_PATH_PREFIX and DOCKER_PATH_PREFIX:
        pairs.append((PLEX_PATH_PREFIX, DOCKER_PATH_PREFIX))

    # Mappings les plus fréquents sur cette stack Docker
    pairs.extend([
        ("/mnt/MyBook/itunes", "/itunes"),
        ("/mnt/MyBook/Musiques/iTunes", "/itunes"),
        ("/home/paulceline/Musiques", "/music"),
        ("/mnt/ssd/Musiques", "/music"),
        ("/media/paulceline/Music/music", "/music"),
        ("/mnt/MyBook/playlists", "/playlists"),
    ])
    return pairs


def _resolve_file_path(original: str) -> tuple[str, str]:
    """Résout un chemin de track Plex vers un fichier réellement accessible.

    Retourne (path, source) où source décrit la stratégie utilisée.
    """
    if not original:
        return original, "empty"

    p = Path(original)
    if p.exists():
        return original, "as-is"

    # 1) mappings explicites / connus
    for src, dst in _candidate_mappings():
        if original.startswith(src.rstrip("/") + "/") or original == src:
            cand = original.replace(src, dst, 1)
            if Path(cand).exists():
                return cand, f"mapped:{src}->{dst}"

    # 2) heuristiques Plex/iTunes usuelles
    heuristics: list[str] = []
    if "/iTunes/" in original:
        heuristics.append("/itunes/" + original.split("/iTunes/", 1)[1].lstrip("/"))
    if "/itunes/" in original:
        heuristics.append("/itunes/" + original.split("/itunes/", 1)[1].lstrip("/"))
    if "/Music/" in original:
        heuristics.append("/itunes/Music/" + original.split("/Music/", 1)[1].lstrip("/"))

    for cand in heuristics:
        if Path(cand).exists():
            return cand, "heuristic"

    # 3) fallback par nom de fichier dans les volumes montés (plus coûteux)
    name = Path(original).name
    if name:
        for root in ("/itunes", "/music"):
            if not Path(root).exists():
                continue
            try:
                found = subprocess.run(
                    ["find", root, "-type", "f", "-name", name, "-print", "-quit"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                match = found.stdout.strip().splitlines()
                if match:
                    return match[0], f"basename:{root}"
            except Exception:
                pass

    return original, "unresolved"

# ─── helpers Plex API ────────────────────────────────────────────────────────

def _plex_req(method: str, path: str, extra: dict | None = None) -> ET.Element | int:
    params: dict[str, str] = {"X-Plex-Token": PLEX_TOKEN}
    if extra:
        params.update(extra)
    # Construire l'URL sans double-encoding des params déjà dans path
    if "?" in path:
        url = f"{PLEX_URL}{path}&" + urllib.parse.urlencode(params)
    else:
        url = f"{PLEX_URL}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            if method == "GET" and data:
                return ET.fromstring(data)
            return r.status
    except urllib.error.HTTPError as e:
        print(f"  ⚠️  HTTP {e.code} sur {path}", file=sys.stderr)
        return e.code


def plex_get(path: str) -> ET.Element:
    result = _plex_req("GET", path)
    assert isinstance(result, ET.Element), f"Réponse inattendue pour GET {path}"
    return result


def plex_put(path: str, params: dict | None = None) -> int:
    result = _plex_req("PUT", path, params)
    return result if isinstance(result, int) else 200


def get_audio_sections() -> list[dict]:
    root = plex_get("/library/sections")
    return [
        {"key": s.get("key"), "title": s.get("title", "?")}
        for s in root.findall(".//Directory")
        if s.get("type") == "artist"
    ]


def get_2star_tracks(section_key: str) -> list[dict]:
    """Retourne les tracks 2★ avec leur chemin de fichier."""
    plex_rating = STARS_TO_PLEX[2]
    root = plex_get(f"/library/sections/{section_key}/all?type=10&userRating={plex_rating}")
    tracks = []
    for t in root.findall(".//Track"):
        rk = t.get("ratingKey")
        if not rk:
            continue
        # Récupérer le chemin du fichier dans Media/Part
        file_path = None
        for part in t.findall(".//Part"):
            fp = part.get("file")
            if fp:
                file_path = fp
                break
        if not file_path:
            # Fallback : appel individuel sur la piste
            try:
                detail = plex_get(f"/library/metadata/{rk}")
                for part in detail.findall(".//Part"):
                    fp = part.get("file")
                    if fp:
                        file_path = fp
                        break
            except Exception:
                pass

        tracks.append({
            "ratingKey": rk,
            "title":     t.get("title", "?"),
            "artist":    t.get("grandparentTitle", "?"),
            "album":     t.get("parentTitle", "?"),
            "file":      file_path,
        })
    return tracks


def clear_rating(rating_key: str) -> bool:
    status = plex_put(
        "/:/rate",
        {"key": rating_key, "identifier": "com.plexapp.plugins.library", "rating": "0"},
    )
    return status in (200, 201, 204)


# ─── étapes du pipeline ──────────────────────────────────────────────────────

def run_songrec(file_path: str, dry_run: bool) -> bool:
    """Lance songrec-rename si disponible, sinon fallback songrec + tags/rename simple."""
    songrec_rename_bin = shutil.which("songrec-rename")
    songrec_bin = shutil.which("songrec")

    if dry_run:
        if songrec_rename_bin:
            print(f"  [sim] songrec-rename -i '{file_path}'")
        elif songrec_bin:
            print(f"  [sim] songrec audio-file-to-recognized-song '{file_path}'")
            print("  [sim] fallback: mise à jour tags (artist/title) + renommage simple")
        else:
            print("  [sim] ❌ ni songrec-rename ni songrec n'est disponible")
        return True

    if songrec_rename_bin:
        cmd = [songrec_rename_bin, "-i", file_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    print(f"    {line}")
            if result.stderr:
                for line in result.stderr.strip().splitlines():
                    print(f"    ⚠️  {line}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("  ❌ Timeout songrec-rename (>120s)", file=sys.stderr)
            return False

    if not songrec_bin:
        print(
            "  ❌ ni songrec-rename ni songrec n'est disponible dans le conteneur "
            "(vérifiez les montages SONGREC_* dans docker-compose/.env)",
            file=sys.stderr,
        )
        return False

    # Fallback: reconnaissance + tags/rename basique sans dépendre de songrec-rename.
    cmd = [songrec_bin, "audio-file-to-recognized-song", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            if result.stderr:
                for line in result.stderr.strip().splitlines():
                    print(f"    ⚠️  {line}")
            return False

        payload = (result.stdout or "").strip()
        if not payload:
            print("  ⚠️  songrec n'a renvoyé aucune sortie exploitable")
            return False

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print("  ⚠️  sortie songrec non JSON, impossible de mettre à jour tags")
            return False

        track = data.get("track") or {}
        title = (track.get("title") or "").strip()
        artist = (track.get("subtitle") or "").strip()
        if not title and not artist:
            print("  ⚠️  songrec n'a pas identifié de métadonnées utiles")
            return False

        audio = MutagenFile(file_path, easy=True)
        if audio is None:
            print("  ⚠️  fichier reconnu mais format de tags non supporté par mutagen")
            return False

        if title:
            audio["title"] = [title]
        if artist:
            audio["artist"] = [artist]
        audio.save()
        print("    ✅ Tags mis à jour (fallback songrec)")

        # Renommage simple: <Artist> - <Title>.<ext>
        if title and artist:
            parent = Path(file_path).parent
            ext = Path(file_path).suffix
            safe = f"{artist} - {title}"
            safe = re.sub(r"[\\/:*?\"<>|]", "_", safe).strip()
            safe = re.sub(r"\s+", " ", safe)
            new_path = parent / f"{safe}{ext}"
            src_path = Path(file_path)
            if new_path != src_path and not new_path.exists():
                src_path.rename(new_path)
                print(f"    ✅ Renommé: {new_path.name}")

        return True
    except subprocess.TimeoutExpired:
        print("  ❌ Timeout songrec (>120s)", file=sys.stderr)
        return False


def run_beet(file_path: str, dry_run: bool) -> bool:
    """Lance `beet import -q <fichier>`. Retourne True si succès."""
    if dry_run:
        print(f"  [sim] beet import -q '{file_path}'")
        return True
    # -q = quiet (non-interactif), utilise les réglages du config.yaml
    cmd = ["beet", "import", "-q", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                print(f"    {line}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"    ⚠️  {line}")
        return result.returncode == 0
    except FileNotFoundError:
        print("  ❌ beet introuvable — installez-le avec : pip install beets",
              file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("  ❌ Timeout beet import (>300s)", file=sys.stderr)
        return False


# ─── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline 2★ : songrec-rename -i → beet import → effacement rating Plex"
    )
    parser.add_argument("--dry-run",  action="store_true",
                        help="Simulation : affiche les actions sans les exécuter")
    parser.add_argument("--no-beet",  action="store_true",
                        help="Sauter l'étape beet import")
    parser.add_argument("--no-clear", action="store_true",
                        help="Ne pas effacer le rating 2★ après traitement")
    args = parser.parse_args()

    if not PLEX_TOKEN:
        print("❌ PLEX_TOKEN non défini (variable d'environnement manquante)", file=sys.stderr)
        sys.exit(1)

    mode = "SIMULATION" if args.dry_run else "RÉEL"
    print(f"🎵 Pipeline 2★ Plex [{mode}]")
    print(f"   URL Plex : {PLEX_URL}")
    steps = ["1. songrec-rename -i", "2. beet import"]
    if not args.no_beet:
        pass
    else:
        steps = ["1. songrec-rename -i"]
    if not args.no_clear:
        steps.append("→ effacement rating 2★")
    print(f"   Étapes   : {' → '.join(steps)}")
    print("=" * 60)

    sections = get_audio_sections()
    if not sections:
        print("❌ Aucune section audio trouvée dans Plex.")
        sys.exit(1)

    all_tracks: list[dict] = []
    for section in sections:
        tracks = get_2star_tracks(section["key"])
        if tracks:
            print(f"\n📚 Section «{section['title']}» : {len(tracks)} track(s) 2★")
            all_tracks.extend(tracks)

    if not all_tracks:
        print("\n✅ Aucun track 2★ trouvé — rien à faire.")
        return

    print(f"\n🔍 Total : {len(all_tracks)} track(s) 2★ à traiter\n")

    ok = 0
    errors = 0
    skipped = 0

    for i, track in enumerate(all_tracks, 1):
        title  = track["title"]
        artist = track["artist"]
        fpath  = track["file"]
        rk     = track["ratingKey"]

        print(f"[{i}/{len(all_tracks)}] {artist} — {title}")
        if fpath:
            print(f"  📄 {fpath}")
        else:
            print("  ⚠️  Chemin de fichier introuvable, passage en skip")
            skipped += 1
            continue

        resolved, source = _resolve_file_path(fpath)
        if resolved != fpath:
            print(f"  🔁 Chemin résolu ({source})")
            print(f"     → {resolved}")
        fpath = resolved

        if not args.dry_run and not os.path.exists(fpath):
            print(f"  ⚠️  Fichier absent sur disque : {fpath}")
            skipped += 1
            continue

        # Étape 1 : songrec-rename -i
        print("  🎵 songrec-rename -i …")
        songrec_ok = run_songrec(fpath, args.dry_run)
        if not songrec_ok:
            print("  ❌ songrec-rename a échoué — track ignoré pour beet/clear")
            errors += 1
            continue

        # Étape 2 : beet import
        if not args.no_beet:
            print("  📚 beet import -q …")
            beet_ok = run_beet(fpath, args.dry_run)
            if not beet_ok:
                print("  ⚠️  beet import a échoué — rating NON effacé (traitement manuel requis)")
                errors += 1
                continue

        # Étape 3 : effacement du rating 2★
        if not args.no_clear:
            if args.dry_run:
                print(f"  [sim] API Plex PUT /:/rate?key={rk}&rating=0")
            else:
                cleared = clear_rating(rk)
                if cleared:
                    print("  🧹 Rating 2★ effacé dans Plex")
                else:
                    print("  ⚠️  Impossible d'effacer le rating via API")
                    errors += 1
                    continue

        print("  ✅ OK")
        ok += 1

    print()
    print("=" * 60)
    print(f"📊 Résultats du pipeline 2★ [{mode}]")
    print(f"   ✅ Traités avec succès : {ok}")
    print(f"   ❌ Erreurs             : {errors}")
    print(f"   ⏭️  Ignorés (pas de fichier) : {skipped}")


if __name__ == "__main__":
    main()
