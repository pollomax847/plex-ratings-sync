#!/usr/bin/env python3
import os
import subprocess
import sys
import argparse


def transcode_to_aac(input_file, output_file):
    tmp_output = output_file + '.tmp'
    if os.path.exists(output_file):
        print(f"Skipping (output exists): {output_file}")
        return True
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', input_file,
        '-vn',
        '-c:a', 'libopus',
        '-b:a', '128k',
        tmp_output,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as exc:
        print(f"Error running ffmpeg for {input_file}: {exc}")
        return False
    if result.returncode == 0 and os.path.exists(tmp_output):
        try:
            os.replace(tmp_output, output_file)
            os.remove(input_file)
            print(f"Transcoded and deleted: {input_file} -> {output_file}")
            return True
        except Exception as exc:
            print(f"Post-process error for {input_file}: {exc}")
            return False
    else:
        err = result.stderr if result is not None else 'no result'
        print(f"Failed to transcode {input_file}: {err}")
        try:
            if os.path.exists(tmp_output):
                os.remove(tmp_output)
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description='Scan and transcode audio files to Opus (.opus)')
    parser.add_argument('root_dir', help='Root music directory to scan')
    args = parser.parse_args()
    root_dir = args.root_dir
    print(f"Root dir: {root_dir}")
    print(f"Absolute path: {os.path.abspath(root_dir)}")
    if not os.path.exists(root_dir):
        print(f"Path does not exist: {root_dir}")
        sys.exit(1)
    if not os.path.isdir(root_dir):
        print(f"Path is not a directory: {root_dir}")
        sys.exit(1)
    opus_exts = {'.opus'}
    audio_exts = {'.mp3', '.flac', '.wav', '.ogg', '.aiff', '.bak', '.m4a', '.aac'}
    matches = []
    total_files = 0
    print('Scanning tree (this may take a while for large collections)...')
    for dirpath, dirnames, filenames in os.walk(root_dir):
        total_files += len(filenames)
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in audio_exts and ext not in opus_exts:
                matches.append(os.path.join(dirpath, filename))
    print(f"Scanned files: {total_files}, candidates found: {len(matches)}")
    if matches:
        print('First 20 candidate files:')
        for m in matches[:20]:
            print(' -', m)
    else:
        print('No matching audio files found. Check extensions or permissions.')
        return
    print('\nStarting transcoding pass...')
    success = 0
    failed = 0
    for input_file in matches:
        output_file = os.path.splitext(input_file)[0] + '.opus'
        ok = transcode_to_aac(input_file, output_file)
        if ok:
            success += 1
        else:
            failed += 1
    print(f"Transcoding finished. Success: {success}, Failed: {failed}")


if __name__ == '__main__':
    main()
