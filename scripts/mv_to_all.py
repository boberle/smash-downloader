import os
import sys

dest_dir = "all"
source_dir = sys.argv[1]
force = True

buf = input(f"Move songs from {source_dir} to {dest_dir}? (type yes)")

if buf.lower() == "yes":

    for root, dirnames, filenames in os.walk(source_dir):
        for filename in filenames:
            if filename.endswith('.brstm'):
                game = os.path.basename(root)
                dest_game_dir = os.path.join(dest_dir, game)
                dest_song_file = os.path.join(dest_game_dir, filename)
                source_song_file = os.path.join(root, filename)
                print(f"{source_song_file} -> {dest_song_file}")
                if os.path.exists(dest_song_file):
                    if force:
                        print(f"File {dest_song_file} exists.  Overwriting.")
                    else:
                        raise FileExistsError(dest_song_file)
                if os.path.exists(dest_game_dir):
                    assert os.path.isdir(dest_game_dir)
                else:
                    os.mkdir(dest_game_dir)
                os.rename(source_song_file, dest_song_file)


