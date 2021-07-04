import json
import os
import sys

import smash_download


def get_paths_from_db(include_all_songs=False):
    paths = []
    with open('db.json-20210704') as fh:
        data = json.load(fh)
        for game, game_data in data.items():
            if 'songs' in game_data:
                for song_id, song_data in game_data['songs'].items():
                    if (include_all_songs
                            or song_data['download_time'] is not None):
                        path = smash_download._get_song_path(
                            game_data, song_data, 'songs'
                        )
                        paths.append(path)
    return paths


def get_paths_from_fs(*directories):
    paths = []
    for directory in directories:
        for root, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                assert filename.endswith(".brstm")
                path = os.path.join(root, filename)
                paths.append(path)
    return paths


def _truncate_path(path):
    song_name = os.path.basename(path)
    game_name = os.path.basename(os.path.dirname(path))
    return os.path.join(game_name, song_name)


def compare(fs_paths, db_paths):
    fs_paths = set(map(_truncate_path, fs_paths))
    db_paths = set(map(_truncate_path, db_paths))
    for fs_path in fs_paths:
        if fs_path not in db_paths:
            print("Song in fs but not in db: %s" % fs_path)
    for db_path in db_paths:
        if db_path not in fs_paths:
            print("Song in db but not in fs: %s" % db_path)


if __name__ == "__main__":
    fs_paths = get_paths_from_fs(*sys.argv[1:])
    db_paths = get_paths_from_db(include_all_songs=True)
    compare(fs_paths, db_paths)

