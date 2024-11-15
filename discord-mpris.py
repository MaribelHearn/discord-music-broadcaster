import pympris
import gobject
import time
import dbus
import configparser

from dbus.mainloop.glib import DBusGMainLoop
from pypresence import Presence

# Settings
# --------------------

# read your application ID from config.
configParser = configparser.RawConfigParser()   
configFilePath = r'config.ini'
configParser.read(configFilePath)
config = dict(configParser.items('config'))
app_id = config["app_id"]

# various customizable text.
# available variables are {title} {artist} and {album}
top_text = "{title}"
bottom_text = "{artist}"

large_image_playing_text = "{album}"
large_image_paused_text =  "{album}"
small_image_playing_text = ""
small_image_paused_text =  ""

# names of the images you used for your application.
# (can be empty if you don't want to use them.)
large_image_paused  = "strawberry"
large_image_playing = "strawberry"
small_image_paused  = "pause"
small_image_playing = "play"

# The amount of time waited before your music stops being broadcasted after being paused.
# Set to 0 to disable.
pause_timeout = 300

# Set this to True if you'd prefer to display the albumartist instead of the artist on a track when possible.
# (if only the artist or only the albumartist is available for a track it will use what its got regardless of this setting.)
prefer_album_artist = True

# List of allowed music players, add your preferred player here.
# Spotify is disabled by default because Discord
# already features Spotify integration.
whitelist = [
        "Cantata",
        "Quod Libet",
        "Clementine",
    #   "Spotify",
        "Strawberry",
]

# --------------------

large_image_paused  = None if not large_image_paused else large_image_paused
large_image_playing = None if not large_image_playing else large_image_playing
small_image_paused  = None if not small_image_paused else small_image_paused
small_image_playing = None if not small_image_playing else small_image_playing
large_image_paused_text = None if not large_image_paused_text else large_image_paused_text
large_image_playing_text = None if not large_image_playing_text else large_image_playing_text
small_image_playing_text = None if not small_image_playing_text else small_image_playing_text
small_image_paused_text = None if not small_image_paused_text else small_image_paused_text
top_text = None if not top_text else top_text
bottom_text = None if not bottom_text else bottom_text
# ---


class Song:
    title = ""
    artist = ""
    album = ""
    playing = False

    length = 0
    position = 0

# in:  a MediaPlayer
# out: the current Song
def get_song(mp):
    song = Song()
    md = mp.player.Metadata
    if not md: return song

    song.title = md["xesam:title"]
    song.album = md["xesam:album"]

    artist = md["xesam:artist"][0] if "xesam:artist" in md else ""
    albumartist = md["xesam:albumArtist"][0] if "xesam:albumArtist" in md else ""
    if artist and albumartist and prefer_album_artist: song.artist = albumartist
    elif artist: song.artist = artist
    elif albumartist: song.artist = albumartist

    song.playing = mp.player.PlaybackStatus == "Playing"
    song.position = mp.player.Position / 1_000_000
    song.length = md["mpris:length"] / 1_000_000
    return song



dbus_loop = DBusGMainLoop()
bus = dbus.SessionBus(mainloop=dbus_loop)
presence = Presence(app_id)
presence.connect()

time_passed = pause_timeout
started_playing = True

while True:
    pids = list(pympris.available_players())
    mps = [pympris.MediaPlayer(pid, bus) for pid in pids]
    mps = [mp for mp in mps if mp.root.Identity in whitelist]
    mps.sort(key=lambda x: x.player.PlaybackStatus != "Playing")

    if mps:
        song = get_song(mps[0]) # 0th mp is most likely to be active.
        if started_playing:
            start_time = time.time()

        if song.playing:
            time_passed = 0
            started_playing = False
        else:
            started_playing = True

        lt = large_image_playing_text if song.playing else large_image_paused_text
        st = small_image_playing_text if song.playing else small_image_paused_text

        if song.title and (pause_timeout == 0 or time_passed < pause_timeout):
            presence.update(
                details = top_text.format(artist=song.artist, title=song.title, album=song.album) if top_text else top_text,
                state = bottom_text.format(artist=song.artist, title=song.title, album=song.album) if bottom_text else bottom_text,
                start = start_time if song.playing else None,
                end = start_time + song.position if song.playing else None,

                #large_image = large_image_playing if song.playing else large_image_paused,
                large_image = song.album.lower().replace(".","").replace(" ","_").replace("&","and"),
                small_image = small_image_playing if song.playing else small_image_paused,
                large_text = lt.format(artist=song.artist, title=song.title, album=song.album) if lt else lt,
                small_text = st.format(artist=song.artist, title=song.title, album=song.album) if st else st,
            )
        else:
            presence.clear()

    time.sleep(1)
    time_passed += 1
