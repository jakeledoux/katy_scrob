import configparser
import hashlib
import os
import requests
import time
import xml.etree.ElementTree as et

LAST_KEY = "050d6b3af78ac5618183f89cfb0f9d02"
LAST_SECRET = "2588ebf9883ca76ee70671bbda0c5fc7"

base_path = os.path.dirname(os.path.realpath(__file__))

options = configparser.ConfigParser()
options.read(f'{base_path}\\options.ini')
# options['File']['pathtofile']

def sign(parameters):
    param_string = ""
    for key in sorted(list(parameters.keys())):
        param_string += f"{key}{parameters[key]}"
    param_string += LAST_SECRET
    hash_browns = hashlib.md5(param_string.encode()).hexdigest()
    return hash_browns # Writing about hashes is making me hungry

def getURL(parameters, signed=True):
    param_string = ""
    for key in parameters:
        param_string += f"{key}={parameters[key]}&"
    if signed:
        param_string += f"api_sig={sign(parameters)}&"
    return f"https://ws.audioscrobbler.com/2.0/?{param_string}format=json"

def getMobileSession(username, password):
    r = requests.post(
        getURL({
            "method": "auth.getMobileSession",
            "username": username,
            "password": password,
            "api_key": LAST_KEY
        })
    )
    if r.ok:
        return r.json()['session']['key']
    else:
        return False

def scrobble(song, session_key):
    r = requests.post(getURL({
        'method': 'track.scrobble',
        'artist': song['artist'],
        'track': song['title'],
        'album': song['album'],
        'timestamp': song['timestamp'],
        'api_key': LAST_KEY,
        'sk': session_key
    }))
    return r.ok

def get_song(path='', blank=False):
    if not blank:
        # Load XML file
        tree = et.parse(path)
        root = tree.getroot()
        
        # Time conversion
        pattern = "%d/%m/%Y %H:%M:%S %p"
        epoch = int(time.mktime(
            time.strptime(root.find('startTime').text, pattern)
        ))

        # Create dictionary from info
        song = {
            'artist': root.find('artist').text,
            'title': root.find('title').text,
            'album': root.find('album').text,
            'timestamp': epoch
        }
    else:
        # Create blank song dictionary
        song = {
            'artist': "",
            'title': "",
            'album': "",
            'timestamp': 0
        }
    return(song)

def test():
    return getMobileSession(options['Last.fm']['username'], options['Last.fm']['password'])

if __name__ == "__main__":
    username = options['Last.fm']['username']
    password = options['Last.fm']['password']
    session_key = getMobileSession(username, password)
    
    if options['File']['scrobbleonstart'] == "1":
        last_song = get_song(blank=True)
    else:
        last_song = get_song(options['File']['pathtofile'])

    if session_key:
        print("Successfully authenticated.")
        while True:
            song = get_song(options['File']['pathtofile'])
            if any([song[key] != last_song[key] for key in song]):
                if scrobble(song, session_key):
                    print(f"Scrobbled: {song['artist']} - {song['title']}")
                else:
                    print(f"FAILED TO SCROBBLE: {song['artist']} - {song['title']}")
            last_song = song
            time.sleep(int(options['File']['refreshinterval']))
    else:
        print("Failed to authenticate.")
        print("Double check your username, password, and internet connection.")
