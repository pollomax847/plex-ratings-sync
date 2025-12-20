import requests
import os
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import concurrent.futures
import re
from translatepy import Translator
from langdetect import detect

LASTFM_API_KEY = "4cecf26d70998e5bb4238e37a1408db7"
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

translator = Translator()

def translate_text(text):
    try:
        lang = detect(text)
        if lang not in ['fr', 'en']:
            return translator.translate(text, "French").result
        else:
            return text
    except:
        return text

def get_track_info(artist, track):
    params = {
        "method": "track.getInfo",
        "api_key": LASTFM_API_KEY,
        "artist": artist,
        "track": track,
        "format": "json"
    }
    response = requests.get(LASTFM_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

def update_id3_tags(file_path, artist, album, title):
    try:
        audio = MP3(file_path, ID3=EasyID3)
        audio["artist"] = artist
        audio["album"] = album
        audio["title"] = title
        audio.save()
        print(f"Tags updated for {file_path}")
    except Exception as e:
        print(f"Error updating tags for {file_path}: {e}")

def process_file(file_path, directory):
    try:
        parts = os.path.relpath(file_path, directory).split(os.sep)
        if len(parts) >= 3:
            artist = parts[0]
            album = parts[1]
            title = os.path.splitext(parts[2])[0]
            info = get_track_info(artist, title)
            album_name = album
            year = None
            if info and "track" in info:
                album_info = info["track"].get("album", {})
                album_name = album_info.get("title", album)
                year = album_info.get("date") if "date" in album_info else None
            if year:
                album_name = f"{album_name} ({year})"
            
            # Translate to English
            artist = translate_text(artist)
            album_name = translate_text(album_name)
            title = translate_text(title)
            
            update_id3_tags(file_path, artist, album_name, title)
            
            # Format title with track number if present
            match = re.match(r'^(\d+)[-_](.*)$', title)
            if match:
                track_num = match.group(1).zfill(2)
                track_title = match.group(2)
                formatted_title = f"{track_num} - {track_title}"
            else:
                formatted_title = title
            
            # Rename the file
            new_dir = os.path.join(directory, artist, album_name)
            os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, formatted_title + ".mp3")
            if file_path != new_path:
                os.rename(file_path, new_path)
                print(f"Renamed {file_path} to {new_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_directory(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".mp3"):
                file_path = os.path.join(root, file)
                file_list.append(file_path)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_file, fp, directory) for fp in file_list]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # Wait for completion

def main():
    directories = [
        "/mnt/mybook/Musiques",
        "/mnt/mybook/itunes/Music",
        "/home/paulceline/Musiques"
    ]
    for directory in directories:
        if os.path.exists(directory):
            print(f"Processing directory: {directory}")
            process_directory(directory)
        else:
            print(f"Directory not found: {directory}")

if __name__ == "__main__":
    main()
