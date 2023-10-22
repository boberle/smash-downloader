# Smash downloader

## The downloader

This is a small script to scrape music files (in [brstm](https://www.lifewire.com/brstm-file-2619975) format) from the smashcustommusic.com website (or its spin-offs). Don't download music files you don't have the right to.

In order to download the music files, we need:

- the list of games,
- the list of songs (music) for each game,
- the file themselves.

The website is pretty simple. The home page (path `/`) contains the list of games, each identified by a numerical id. Then, each game is located at the path `/game/GAME_ID`, and is easily parsed to get the list of songs, each identified by another numerical id. Each song has a page at `/song/SONG_ID`, but we don't need this page because we can directly download the brstm file at `/brstm/SONG_ID`.

The script has thus 3 commands:

- one to download the list of game ids (in order to get access to the game pages to get the list of song ids),
- one to download the list of song ids for each game,
- one to download the brstm files.

The general state is stored in a json database (one file), that looks like:

```json
{
  "site": {
    "base_url": "http://thewebsite.com",
    "games": [
      {
        "id": 123,
        "title": "Game Title",
        "songs": [
          {
            "id": 456,
            "title": "Song title",
            "is_deleted_from_site": false,
            "brstm_download_info": {
              "location": "123_game_title/456_song_title.brstm",
              "timestamp": 1624333875,
              "file_md5": "f3bdb0434bc53ca4e0562c9ef014cb8d"
            }
          }
        ]
      }
    ]
  }
}
```

In order to run the script, you need to install the dependencies in the `requirements.txt` file.

To download the home page and scrape the list of game from it, run:

```bash
python# src/download.py update-game-list --base-url http://thewebsite.com --db-file db.json --output-dir html_output
```

If the database file already exists, it will be updated (new games will be added, and games that are not available anymore on the website will be marked with a `is_deleted_from_site` flag).

The `--output-dir` directory is where the html file are downloaded (eg. for troubleshooting).

To update the list of songs from the game pages, use:

```bash
python3 src/download.py update-game-song-lists --base-url http://thewebsite.com --db-file db.json --output-dir html_output --max-count 100
```

The games that were never visited are updated first, then in order of visit (the game with the oldest visit timestamp is visited first).  Because there are thousands of games, you can limit the number of visits with `--max-count`.  New songs are added to the list, and the ones that are not available anymore are marked with a `is_deleted_from_site` flag).

You can also specify a sleep between each network request with `--nap-time MIN MAX` (the script will sleep for a time chosen at random between MIN and MAX seconds).

Then, to download the brstm files, run:

```bash
python3 src/download.py download-musics --base-url http://thewebsite.com --db-file db.json --output-dir song_files --max-count 100
```

Songs are downloaded in a random order.

There commands are intended to be run several times (the website been updated frequently).

You can also show some statistics with:

```bash
python3 src/download.py statistics --db-file db.json
```

The output will be like:

```
games: 2000
games visited: 1000
games not visited: 1000
games deleted from site: 1
game oldest visit: 2000-01-01T00:00:00
songs: 5000
songs downloaded: 4000
songs not downloaded: 1000
songs deleted from site: 2
```

Use `--help` to get help.

## The migrator

There is a script `src/migrator/migrate.py` to migrate from the previous database format to the new one.


## Extracting the metadata

This script reads each brstm file, and run `mplayer -identify` for each in order to extract the loop start and end, alongside the duration. It gets the game and song titles from the json database (see above). `ffmpeg` is used to check for potential errors. It produces a list of metadata like this:

```json
[
  {
    "path": "123_game_title/456_song_title.brstm",
    "timestamp": 1697965054,
    "loop_start": 19313000,
    "loop_end": 0,
    "duration": 134.55,
    "size": 4374230,
    "title": "Song title",
    "game_title": "Game title",
    "error": false
  }
]
```

```bash
python3 src/metadata/extract.py --root-dir ROOT_DIR --db-file db.json --output-file metadata.json
```

The `--root-dir` is where the songs are saved. The `--output-file` is the json file that is produces by the script.  If it already exists, then the script will update it, not running `mplayer` on files that are already present (unless the `--force` option is used).

Use `--help` to get some help.

This file can be used with my `vgsplay` or `vgosplay` scripts to loop over the songs and rate them.
