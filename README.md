# Download brstm files from the smashcustommusic.net website

This is a crawler that finds video games and songs on the smashcustommusic.net website, and download the brstm file (the audio file) so it can be played in loop.

## Main usages

(1) get the list of all video games available on the site:

    ./smash_download.py update-game-list

This will read the site home page and create a json database in the `db.json` file, containing the list of all video games available on the site.

(2) update the song list for one or more video games:

The previous command just downloaded the video game titles, not the associated song information.  Use:

    ./smash_download.py update-song-list --game 123

to download the song information for a the game with id `123` (the id is found in the url: http://www.smashcustommusic.net/game/123.

Usually, you download the song information for several game at once, randomly:

    ./smash_download.py update-song-list --random 50

where 50 is the number of games you want to download the song information for (put whatever you want).

This command update the databse.

(3) download the brstm file for a specific song:

    ./smash_download.py download-song --song 456 -o output_dir [-f]

where `123` is the id of the song (to be found in the url: http://www.smashcustommusic.net/song/456) and `output_dir` is the directory where to store the song.  The song is store in `output_directory/123_game_title_slug/456_song_title_slug.brstm`.  The directories are created as necessary.

Use the `-f` switch to force download (when you download a song, it is marked as downloaded in the database, and will be normally downloaded again).

(4) download randomly songs:

    ./smash_download.py download-song --random 50 -o output_dir [-f]

will download 50 songs randomly chosen among the songs discovered with the `update-song-list` command.

To summarize:

    ./smash_download.py update-game-list  # once at the beginning and to update
    ./smash_download.py update-song-list --random 50  # as many times as you want
    ./smash_download.py download-song --random 50 -o output_dir   # idem

To get help on a specific command, run:

    ./smash_download.py COMMAND --help

for example:

    ./smash_download.py download-song --help

## License

MIT -- see the `LICENSE` file.
