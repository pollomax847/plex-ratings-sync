# Script Python avancé pour surveiller les playlists
import requests
import time
import json
from datetime import datetime

def check_playlist_updates(playlist_url, check_interval=1800):  # 30 minutes
    # Extraire l'ID de la playlist depuis l'URL
    playlist_id = playlist_url.split('/')[-1]
    
    # Utiliser l'API Deezer (nécessite une clé API)
    api_url = f'https://api.deezer.com/playlist/{playlist_id}'
    
    last_tracks = None
    
    while True:
        try:
            response = requests.get(api_url)
            data = response.json()
            
            current_tracks = [track['title'] for track in data.get('tracks', {}).get('data', [])]
            
            if last_tracks is not None and current_tracks != last_tracks:
                new_tracks = set(current_tracks) - set(last_tracks)
                print(f'🎵 {len(new_tracks)} nouveaux titres détectés:')
                for track in new_tracks:
                    print(f'  • {track}')
                
                # Télécharger automatiquement les nouveaux titres
                # os.system(f'freyr-music "{playlist_url}"')
            
            last_tracks = current_tracks
            print(f'{datetime.now()}: Surveillance active... ({len(current_tracks)} titres)')
            
        except Exception as e:
            print(f'Erreur: {e}')
        
        time.sleep(check_interval)

# Utilisation:
# check_playlist_updates('https://www.deezer.com/fr/playlist/1995808222')

