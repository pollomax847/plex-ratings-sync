import requests
import os

LASTFM_API_KEY = "4cecf26d70998e5bb4238e37a1408db7"
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"

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

def main():
    # Exemple d'utilisation
    artist = "2 Be 3"
    track = "Don't Say Goodbye"
    info = get_track_info(artist, track)
    if info:
        print(info)
    else:
        print("Aucune info trouvée.")

if __name__ == "__main__":
    main()
