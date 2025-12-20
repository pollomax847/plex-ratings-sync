from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

file_path = "/mnt/mybook/Musiques/George_Clinton/10_Things_I_Hate_About_You_Music_From_the_Motion_Picture/5-Atomic_Dog.mp3"

try:
    audio = MP3(file_path, ID3=EasyID3)
    print("ID3v2 tags:")
    for key, value in audio.items():
        print(f"{key}: {value}")
except Exception as e:
    print(f"Error: {e}")