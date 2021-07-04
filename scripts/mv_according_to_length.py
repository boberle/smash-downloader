import os
import sys
import json
import argparse


def get_songs(*paths, min_length):
    ignored_song_paths = set()
    included_song_paths = set()
    for path in paths:
        with open(path) as fh:
            data = json.load(fh)
            for song_path, song_data in data.items():
                length = song_data.get('length', song_data.get("ID_LENGTH"))
                if not length:
                    raise RuntimeError(
                        f"No length for song {song_path}."
                    )
                if not isinstance(length, float):
                    length = float(length)
                if length >= min_length:
                    included_song_paths.add(song_path)
                else:
                    ignored_song_paths.add(song_path)
    return included_song_paths, ignored_song_paths


def move_songs(source_dir, dest_dir, included_song_paths, ignored_song_paths):
    moving = []
    for root, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            if filename.endswith('.brstm'):
                game = os.path.basename(root)
                song_path = os.path.join(game, filename)
                if (song_path not in included_song_paths
                        and song_path not in ignored_song_paths):
                    raise RuntimeError(f"song {song_path} not in metadata")
                if (song_path not in included_song_paths):
                    print(f"Ignoring {song_path}")
                    continue
                dest_game_dir = os.path.join(dest_dir, game)
                dest_song_file = os.path.join(dest_game_dir, filename)
                source_song_file = os.path.join(root, filename)
                if os.path.exists(dest_song_file):
                    raise FileExistsError(dest_song_file)
                if os.path.exists(dest_game_dir):
                    assert os.path.isdir(dest_game_dir)
                moving.append((source_song_file, dest_song_file))

    for source, dest in moving:
        game_dir = os.path.dirname(dest)
        if not os.path.exists(game_dir):
            os.mkdir(game_dir)
        print(f"Moving {source} to {dest}")
        os.rename(source, dest)


def parse_args():
    # definition
    parser = argparse.ArgumentParser(prog="progname",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # arguments (not options)
    parser.add_argument("source_dir", help="source directory")
    # options
    parser.add_argument("--dest-dir", required=True,
        help="destination directory")
    parser.add_argument("--min-length", required=True, type=float,
        help="destination directory")
    parser.add_argument("--metadata", required=True, default=list(),
        action="append", help="metadata file (json)")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    source_dir = args.source_dir
    dest_dir = args.dest_dir
    min_length = args.min_length
    metadata_files = args.metadata

    if not os.path.isdir(source_dir):
        raise RuntimeError(f"{source_dir} is not a directory")
    if not os.path.isdir(dest_dir):
        raise RuntimeError(f"{dest_dir} is not a directory")
    if min_length < 0:
        raise RuntimeError(f"invalid min length: {min_length}")
    if not metadata_files:
        raise RuntimeError(f"no metadata files")

    buf = input(f"Move songs longer than {min_length} from {source_dir} to {dest_dir}? (type 'yes')")
    if buf.lower() != "yes":
        print("aborting")
        sys.exit()

    included_song_paths, ignored_song_paths = get_songs(
        *metadata_files,
        min_length=min_length,
    )
    move_songs(source_dir, dest_dir, included_song_paths, ignored_song_paths)
    

if __name__ == "__main__":
    main()
