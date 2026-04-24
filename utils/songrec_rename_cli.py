#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mutagen import File as MutagenFile


AUDIO_EXTS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".mp4", ".wav"}


def _sanitize(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]', '_', value).strip()
    value = re.sub(r'\s+', ' ', value)
    return value[:180] or "unknown"


def _songrec_bin() -> str | None:
    for candidate in ("songrec", "/usr/local/bin/songrec", "/usr/bin/songrec"):
        found = shutil.which(candidate) if "/" not in candidate else (candidate if Path(candidate).exists() else None)
        if found:
            return found
    return None


def _recognize(file_path: Path) -> tuple[str, str] | None:
    songrec = _songrec_bin()
    if not songrec:
        print("❌ songrec introuvable", file=sys.stderr)
        return None
    try:
        result = subprocess.run(
            [songrec, "audio-file-to-recognized-song", str(file_path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout songrec: {file_path}", file=sys.stderr)
        return None
    if result.returncode != 0:
        if result.stderr.strip():
            print(f"❌ songrec: {result.stderr.strip()}", file=sys.stderr)
        return None
    try:
        data = json.loads((result.stdout or "").strip())
    except json.JSONDecodeError:
        print("❌ sortie songrec non JSON", file=sys.stderr)
        return None
    track = data.get("track") or {}
    title = (track.get("title") or "").strip()
    artist = (track.get("subtitle") or "").strip()
    if not title and not artist:
        return None
    return artist, title


def _write_tags(file_path: Path, artist: str, title: str) -> bool:
    audio = MutagenFile(file_path, easy=True)
    if audio is None:
        print(f"⚠️ Format non supporté pour tags: {file_path}", file=sys.stderr)
        return False
    if artist:
        audio["artist"] = [artist]
    if title:
        audio["title"] = [title]
    audio.save()
    return True


def _target_name(src: Path, artist: str, title: str) -> Path:
    name = _sanitize(f"{artist} - {title}" if artist and title else title or artist or src.stem)
    target = src.with_name(f"{name}{src.suffix}")
    if target == src or not target.exists():
        return target
    index = 1
    while True:
        candidate = src.with_name(f"{name} ({index}){src.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def process_file(file_path: Path, add_tags: bool) -> bool:
    if not file_path.is_file():
        print(f"❌ Fichier introuvable: {file_path}", file=sys.stderr)
        return False
    match = _recognize(file_path)
    if not match:
        print(f"❌ Échec: {file_path.name}", file=sys.stderr)
        return False
    artist, title = match
    print(f"✅ Identifié: {artist} - {title}")
    if add_tags and not _write_tags(file_path, artist, title):
        return False
    target = _target_name(file_path, artist, title)
    if target != file_path:
        file_path.rename(target)
        print(f"✅ Renommé: {target.name}")
    return True


def iter_inputs(paths: list[str], recurse: bool):
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            yield path
            continue
        if path.is_dir() and recurse:
            for child in path.rglob("*"):
                if child.is_file() and child.suffix.lower() in AUDIO_EXTS:
                    yield child


def main() -> int:
    parser = argparse.ArgumentParser(prog="songrec-rename")
    parser.add_argument("-i", action="store_true", help="Ajoute les tags ID3/metadata")
    parser.add_argument("-r", action="store_true", help="Parcourt récursivement les dossiers")
    parser.add_argument("paths", nargs="+", help="Fichier(s) ou dossier(s) audio")
    args = parser.parse_args()

    files = list(iter_inputs(args.paths, args.r))
    if not files:
        print("❌ Aucun fichier audio à traiter", file=sys.stderr)
        return 1

    failures = 0
    for file_path in files:
        if not process_file(file_path, add_tags=args.i):
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())