#!/usr/bin/env python3

"""Download brstm files from the smashcustommusic.net website.

This is a crawler that find video games and songs on the smashcustommusic.net
website, and download the brstm file (the audio file) so it can be played in loop.

Main usages are:

(1) get the list of all video games available on the site:

    ./smash_download.py update-game-list

This will read the site home page and create a json database in the `db.json` file,
containing the list of all video games available on the site.

(2) update the song list for one or more video games:

The previous command just downloaded the video game titles, not the associated song
information.  Use:

    ./smash_download.py update-song-list --game 123

to download the song information for a the game with id `123` (the id is found in the
url: http://www.smashcustommusic.net/game/123.

Usually, you download the song information for several game at once, randomly:

    ./smash_download.py update-song-list --random 50

where 50 is the number of games you want to download the song information for (put
whatever you want).

This command update the databse.

(3) download the brstm file for a specific song:

    ./smash_download.py download-song --song 456 -o output_dir [-f]

where `123` is the id of the song (to be found in the url:
http://www.smashcustommusic.net/song/456) and `output_dir` is the directory where
to store the song.  The song is store in
`output_directory/123_game_title_slug/456_song_title_slug.brstm`.  The directories
are created as necessary.

Use the `-f` switch to force download (when you download a song, it is marked as
downloaded in the database, and will be normally downloaded again).

(4) download randomly songs:

    ./smash_download.py download-song --random 50 -o output_dir [-f]

will download 50 songs randomly chosen among the songs discovered with the
`update-song-list` command.

To summarize:

    ./smash_download.py update-game-list  # once at the beginning and to update
    ./smash_download.py update-song-list --random 50  # as many times as you want
    ./smash_download.py download-song --random 50 -o output_dir   # idem

To get help on a specific command, run:

    ./smash_download.py COMMAND --help

for example:

    ./smash_download.py download-song --help
"""

# copyright Bruno Oberle 2021 -- MIT License, see the LICENSE file

import argparse
import datetime
import json
import os
import random
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
import http.client

from bs4 import BeautifulSoup

__version__ = "1.0.0"

# where the database is stored
DATABASE_FILE = "db.json"
"""The format of the databse is as follows:
    {
        GAME_ID_AS_INT = {
            'path': PATH,  # eg /game/123
            'id': GAME_ID_AS_INT,
            'title': TITLE,
            'songs': [  # only when running update-song-list
                SONG_ID_AS_INT: {
                    'id': SONG_ID_AS_INT,
                    'path': PATH,  # eg /song/456
                    'title': TITLE,
                    'download_time': DOWNLOAD_TIME_OR_NONE,
                }
            ]
        }
    }
"""

# urls
SITE_URL = "http://www.smashcustommusic.net"
BRSTM_URL = "http://www.smashcustommusic.net/brstm/%d"


def parse_args():
    """Specification and parsing of the command line arguments."""
    # definition
    parser = argparse.ArgumentParser(prog=os.path.basename(__file__),
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    game = (["--game"], dict(type=int, help="game id"))
    song = (["--song"], dict(type=int, help="song id"))
    output = (["-o", "--output-directory"],
              dict(metavar="PATH", help="output directory", required=True))
    force = (["-f", "--force"], dict(default=False, action="store_true",
        help="force download even if song already marked as downloaded"))
    random_arg = (["--random"], dict(type=int, help="random number"))

    subparsers = parser.add_subparsers(title="command", dest="command")

    subparsers.add_parser("update-game-list", help="update the game list")

    update_song_list = subparsers.add_parser("update-song-list",
                                             help="update the song list")
    group = update_song_list.add_mutually_exclusive_group(required=True)
    group.add_argument(*game[0], **game[1])
    group.add_argument(*random_arg[0], **random_arg[1])

    download_song = subparsers.add_parser("download-song",
                                          help="download a specifc song")
    download_song.add_argument(*song[0], **song[1], required=True)
    download_song.add_argument(*output[0], **output[1])
    download_song.add_argument(*force[0], **force[1])

    download_songs = subparsers.add_parser("download-songs",
                                           help="download some random songs")
    group = download_songs.add_mutually_exclusive_group(required=True)
    group.add_argument(*game[0], **game[1])
    group.add_argument(*random_arg[0], **random_arg[1])
    download_songs.add_argument(*output[0], **output[1])
    download_songs.add_argument(*force[0], **force[1])

    repair_db = subparsers.add_parser("repair-db", help="mark songs that are "
                                                        "downloaded as such")
    repair_db.add_argument(*output[0], **output[1])

    args = parser.parse_args()

    return args


def snap():
    """Snapping between download to avoid DOSing the site."""
    n = random.choice(list(range(15)))
    print("[I]", f"Snap: {n}")
    time.sleep(n)


def load_database():
    """Read the json database file and return a dictionary.

    If the file dosn't exist, return an empty dictionary.
    """
    if os.path.exists(DATABASE_FILE):
        print("[I]", f"Loading database from {DATABASE_FILE}")
        with open(DATABASE_FILE) as fh:
            db = json.load(fh)
        return {
            int(game_id): {
                attr_name: (attr_value if attr_name != 'songs' else {
                    int(song_id): song for song_id, song in attr_value.items()
                })
                for attr_name, attr_value in game.items()
            }
            for game_id, game in db.items()
        }
    print("[I]", "No database found. Creating one")
    return dict()


def save_database(data: dict):
    """Save the dictionary `data` into a json file."""
    print("[I]", f"Saving database into {DATABASE_FILE}")
    with open(DATABASE_FILE, 'w') as fh:
        json.dump(data, fh)


def update_game_list(db):
    """Update the `db` dictionary with the list of all game available on the site.

    All games are on the home page.  Read only that page to get the basic game info
    (id, title, path).
    """
    print("[I] Updating game list")
    response = urllib.request.urlopen(SITE_URL)
    home_page_content = response.read().decode()
    soup = BeautifulSoup(home_page_content, "lxml")
    for anchor in soup.find_all('a'):
        if anchor['href'].startswith('/game/'):
            game_path = anchor['href']
            game_id = int(re.fullmatch(r'/game/(\d+)', game_path).group(1))
            game_title = anchor.get_text()
            print(f"[I] Found game {game_id} ({game_title}).")
            if game_id in db:
                print("[I] Game is already in the database.")
                if db[game_id]['title'] != game_title:
                    print("[I] Title has changed. Updating.")
                    db[game_id]['title'] = game_title
            else:
                print("[I] Adding to database.")
                db[game_id] = dict(
                    path=game_path,
                    id=game_id,
                    title=game_title,
                )


def update_song_list(db, game_id):
    """Retrieve the song list for the given game and update the databse.

    All the songs are on the game page (/game/ID).

    Download information (download time) is preserved.
    """
    if game_id not in db:
        raise RuntimeError(f"game {game_id} not found")
    game_dic = db[game_id]
    print(f"[I] Getting songs for game {game_id} ('{game_dic['title']}')")
    game_page_url = urllib.parse.urljoin(SITE_URL, game_dic['path'])
    response = urllib.request.urlopen(game_page_url)
    game_page_content = response.read().decode()
    soup = BeautifulSoup(game_page_content, "lxml")
    songs = dict()
    for anchor in soup.find_all('a'):
        if anchor['href'].startswith('/song/'):
            song_path = anchor['href']
            song_id = int(re.fullmatch(r'/song/(\d+)', song_path).group(1))
            song_title = anchor.get_text()
            download_time = (
                game_dic['songs'][song_id]['download_time']
                if song_id in game_dic.get('songs', dict())
                else None
            )
            print(f"[I] Found song {song_id} ({song_title}).")
            song = dict(
                id=song_id,
                path=song_path,
                title=song_title,
                download_time=download_time,
            )
            songs[song_id] = song
    game_dic['songs'] = songs


def get_song_dic_from_id(db, song_id):
    """Find the game and song dictionary in the databse.

    Return a tuple with the game dict and the song dict.

    Return `(None, None)` if not found.
    """
    for game_id, game_dic in db.items():
        for song_id_, song_dic in game_dic.get('songs', dict()).items():
            if song_id_ == song_id:
                return game_dic, song_dic
    return None, None


def get_all_song_ids(db, include_downloaded=True):
    """Return a list with all song ids."""
    return {
        song_id
        for game_id, game_dic in db.items()
        for song_id, song_dic in game_dic.get('songs', dict()).items()
        if include_downloaded or song_dic['download_time'] is None
    }


def remove_diacritics(text):
    """Return the `text` string without any diacritics."""
    return ''.join(char for char in unicodedata.normalize('NFD', text) if
                   unicodedata.category(char) != "Mn")


def _slugify(text):
    """Return a slugified version of the given text."""
    text = remove_diacritics(text)
    text = re.sub(r'[^a-z0-9]+', '_', text.lower())
    text = re.sub(r'_+', '_', text)
    text = text.strip("_")
    if text:
        text = f"_{text}"
    return text


def _slugify_path(game_id, game_title, song_id, song_title):
    """Return the path to store the song at."""
    game_title = _slugify(game_title)
    song_title = _slugify(song_title)
    return f"{game_id}{game_title}/{song_id}{song_title}"


def _get_song_path(game_dic, song_dic, output_directory):
    slugified_path = _slugify_path(
        game_id=game_dic['id'],
        game_title=game_dic['title'],
        song_id=song_dic['id'],
        song_title=song_dic['title'],
    )
    path = os.path.join(output_directory, slugified_path + ".brstm")
    return path


def download_song(db, song_id, output_directory, force=False):
    """Download the brstm file of the given file.

    The database is updated with the download time.  Song with a download time set
    are not downloaded except if `force` is `True`.
    """
    print(f"[I] Preparing to download song {song_id}")
    game_dic, song_dic = get_song_dic_from_id(db, song_id)
    if not song_dic:
        raise RuntimeError(f"Unknown song: {song_id}")
    if not force and song_dic['download_time'] is not None:
        print("[I] Song already downloaded. Skipping")
        return
    path = _get_song_path(game_dic=game_dic, song_dic=song_dic, output_directory=output_directory)
    if os.path.exists(path):
        print(
            "[W]",
            f"Song {game_dic['title']} -- {song_dic['title']} "
            f"already downloaded into {path}.",
            "I won't download it twice but I will mark it as downloaded."
        )
    else:
        url = BRSTM_URL % song_id
        print(f"[I] Downloading '{url}'")
        max_retries = 10
        for i in range(max_retries):
            try:
                response = urllib.request.urlopen(url)
            except (urllib.error.URLError, http.client.IncompleteRead) as e:
                print(
                    "[E]", "Error when downloading the file:", str(e) + ".",
                    f"Try {i+1}/{max_retries}"
                )
            else:
                break
        else:
            print("[E]", "I can't download the song.  Skipping")
            return
        binary_content = response.read()
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        with open(path, 'wb') as fh:
            fh.write(binary_content)
        print(f"[I] Song saved into {path}")
    song_dic['download_time'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")


def repair_db(db, output_directory):
    """Mark songs with a file present on the file system as downloaded.

    This function doesn't "unmark" songs if they aren't present on the file system.
    """
    print("[I]", "Checking for downloaded songs")
    for game_id, game_dic in db.items():
        for song_id_, song_dic in game_dic.get('songs', dict()).items():
            path = _get_song_path(game_dic=game_dic, song_dic=song_dic, output_directory=output_directory)
            if os.path.exists(path) and not song_dic['download_time']:
                print(
                    "[I]",
                    f"Song {game_dic['title']} -- {song_dic['title']} "
                    f"downloaded into {path} but not marked as downloaded.",
                    "Marking it as downloaded."
                )
                song_dic['download_time'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")


def main():
    """Program starts here."""
    args = parse_args()
    db = load_database()
    if args.command == "update-game-list":
        update_game_list(db)
    elif args.command == "update-song-list":
        if args.game:
            update_song_list(db, args.game)
        else:
            for i, game in enumerate(random.sample(db.keys(), args.random)):
                print(f"[I] Progress: {i+1}/{args.random}")
                update_song_list(db, game)
                if args.random > 1 and i < args.random - 1:
                    snap()
    elif args.command == "download-song":
        download_song(db, args.song, args.output_directory, force=args.force)
    elif args.command == "download-songs":
        if args.game:
            game_dic = db[args.game]
            if 'songs' not in game_dic:
                update_song_list(db, args.game)
            length = len(game_dic['songs'])
            for i, song_id in enumerate(game_dic['songs'].keys()):
                print(f"[I] Progress: {i+1}/{length}")
                download_song(db, song_id, args.output_directory, force=args.force)
                if length and i < length - 1:
                    snap()
        else:
            for i, song_id in enumerate(random.sample(get_all_song_ids(db,
                                                                       include_downloaded=False), args.random)):
                print(f"[I] Progress: {i+1}/{args.random}")
                download_song(db, song_id, args.output_directory, force=args.force)
                if args.random > 1 and i < args.random - 1:
                    snap()
    elif args.command == "repair-db":
        repair_db(db, args.output_directory)
    save_database(db)


if __name__ == "__main__":
    main()
