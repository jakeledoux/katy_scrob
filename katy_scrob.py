import configparser
import hashlib
import os
import requests
import time
import xml.etree.ElementTree as et

# I normally wouldn't hardcode this sort of thing
# but Last.fm has shut down the developer management
# pages so screw it. If they ever revamp the API I'll
# start using better practices.
LAST_KEY = "050d6b3af78ac5618183f89cfb0f9d02"
LAST_SECRET = "2588ebf9883ca76ee70671bbda0c5fc7"

base_path = os.path.dirname(os.path.realpath(__file__))

# Load options
options = configparser.ConfigParser()
options.read(f'{base_path}\\options.ini')

# Creates the MD5 hash according to the Last.fm
# mobile authentication guide.
def sign(parameters):
    param_string = ""
    for key in sorted(list(parameters.keys())):
        param_string += f"{key}{parameters[key]}"
    param_string += LAST_SECRET
    hash_browns = hashlib.md5(param_string.encode()).hexdigest()
    return hash_browns # Writing about hashes is making me hungry

# Takes parameters and creates the URL to send requests
# to, including the signature and JSON formatting params.
def getURL(parameters, signed=True):
    param_string = ""
    for key in parameters:
        param_string += f"{key}={parameters[key]}&"
    if signed:
        param_string += f"api_sig={sign(parameters)}&"
    return f"https://ws.audioscrobbler.com/2.0/?{param_string}format=json"

# Authenticates and returns session key.
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

# Scrobbles using song dictionary created with get_song()
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

# Returns song dictionary either from an XML file
# or a blank template if blank == True.
def get_song(path='', blank=False):
    if not blank:
        # Load XML file
        tree = et.parse(path)
        root = tree.getroot()
        
        # Time conversion
        pattern = "%d/%m/%Y %I:%M:%S %p"
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

if __name__ == "__main__":

    # Assign username/password to variables so I don't
    # have to paste that whole spiel every time
    username = options['Last.fm']['username']
    password = options['Last.fm']['password']
    # Authenticate with Last.fm
    session_key = getMobileSession(username, password)
    
    # Either load from XML or create blank song dictionary
    # to force a scrobble on startup
    if options['File']['scrobbleonstart'] == "1":
        last_song = get_song(blank=True)
    else:
        last_song = get_song(options['File']['pathtofile'])

    # If authentication was successful
    if session_key:
        print("Successfully authenticated.")
        
        # Loop until closed
        while True:
            # Read song info from file
            song = get_song(options['File']['pathtofile'])
            
            # Song is different from the last time we checked
            if any([song[key] != last_song[key] for key in song]):
                # Try to scrobble song and print whether it worked
                if scrobble(song, session_key):
                    print(f"Scrobbled: {song['artist']} - {song['title']}")
                else:
                    print(f"FAILED TO SCROBBLE: {song['artist']} - {song['title']}")
            # Update last song for next loop iteration
            last_song = song
            # Wait for the amount of seconds specified in the INI
            time.sleep(int(options['File']['refreshinterval']))
    else:
        print("Failed to authenticate.")
        print("Double check your username, password, and internet connection.")
        input("\nPress enter to close...")
