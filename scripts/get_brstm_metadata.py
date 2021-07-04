import os
import subprocess
import sys
import re
import json

#MIDENTIFY_COMMAND = "/usr/share/mplayer/midentify.sh"

# NOTE: some file are misidentified as TIVO:
#   TiVo file format detected.
# instead of:
#   libavformat file format detected.
# We force the libavformat with -demuxer 35 (see mplayer -demuxer help for the
# complete list).
MIDENTIFY_COMMAND = "mplayer -demuxer 35 -noconfig all -cache-min 0 -vo null -ao null -frames 0 -identify".split()
BATCH_LENGTH = 1000

def parse_metadata(lines):
    metadata = dict()
    for line in lines:
        key, value = line.split("=")
        metadata[key] = value
    if "ID_CLIP_INFO_N" in metadata:
        n = int(metadata["ID_CLIP_INFO_N"])
        for i in range(n):
            key = metadata["ID_CLIP_INFO_NAME%d" % i]
            value = metadata["ID_CLIP_INFO_VALUE%d" % i]
            metadata[key] = value
    return metadata


def get_file_list(*directories):
    print("Getting file list")
    paths = []
    for directory in directories:
        for root, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                assert filename.endswith(".brstm")
                # TODO
                path = os.path.join(root, filename)
                if os.path.getsize(path) == 0:
                    continue
                paths.append(path)
    return paths


def run_midentify(paths):
    # NOTE:
    # Some file have non utf-8 metadata in them, for example:
    #   ...
    #   Playing all/6_metroid_prime_2_echoes/342_ing_hive_main_theme.brstm.
    #   libavformat version 58.45.100 (external)
    #   ...
    #   ID_FILENAME=all/6_metroid_prime_2_echoes/342_ing_hive_main_theme.brstm
    #   ID_DEMUXER=nsv
    #   ID_AUDIO_FORMAT=�3▒�
    # 
    # This is why we don't use `universal_newlines` and make the utf8
    # conversion ourselves.

    print("Running midentify for %d files" % len(paths))
    args = [*MIDENTIFY_COMMAND, *paths]
    proc = subprocess.run(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    lines = proc.stdout.decode(errors="replace").splitlines()
    lines = list(filter(
        lambda x: x.startswith("ID_")
        or x.startswith("Playing ")
        or 'no sound' in x,
    lines))
    return lines, proc.stderr.decode(errors="replace")


def find_errors(lines, stderr, paths):
    # it's possible that, for some reason, mplayer crash.  For example:
    # [bruno from_vm]$ mplayer all/3728_team_sonic_racing/92268_mother_s_canyon_goal.brstm
    # MPlayer 1.3.0 (Debian), built with gcc-10 (C) 2000-2016 MPlayer Team
    # do_connect: could not connect to socket
    # connect: No such file or directory
    # Failed to open LIRC support. You will not be able to use your remote control.
    # 
    # Playing all/3728_team_sonic_racing/92268_mother_s_canyon_goal.brstm.
    # libavformat version 58.45.100 (external)
    # TiVo file format detected.
    # MPEG: No audio stream found -> no sound.
    # MPEG: FATAL: EOF while searching for sequence header.
    # Video: Cannot read properties.
    # Load subtitles in all/3728_team_sonic_racing/
    # 
    # 
    # MPlayer interrupted by signal 11 in module: read_subtitles_file
    # - MPlayer crashed by bad usage of CPU/FPU/RAM.
    #   Recompile MPlayer with --enable-debug and make a 'gdb' backtrace and
    #   disassembly. Details in DOCS/HTML/en/bugreports_what.html#bugreports_crash.
    #  [ This binary of MPlayer in Debian is currently compiled with
    #    '--enable-debug'; the debugging symbols are in the package
    #    'mplayer-dbgsym'.]
    #
    # In this situation, we return the last played song: you should remove it
    # and try again!

    count = 0
    last_played_song = None
    for line in lines:
        if line.startswith("Playing "):
            m = re.fullmatch(r"Playing (.*?)\.", line)
            last_played_song = m.group(1)
            count += 1
    if count < len(paths) and 'MPlayer interrupted by signal 11' in stderr:
        return last_played_song
    assert count == len(paths), last_playing_line
    return None


def get_metadata(paths):
    data = dict()
    for i in range(0, len(paths), BATCH_LENGTH):
        print("Batch %d-%d" % (i, i+BATCH_LENGTH))
        path_set = paths[i:i+BATCH_LENGTH]
        # TODO
        with open('/tmp/list', 'w') as fh:
            fh.write(str(path_set))
        while True:
            lines, stderr = run_midentify(path_set)
            error_song = find_errors(lines, stderr, path_set)
            if error_song is None:
                break
            print(
                f"Song {error_song} lead mplayer to crash. "
                "Will remove it and try again."
            )
            path_set.remove(error_song)
        print("Parsing results")
        index = 0
        searched = "Playing %s." % path_set[0]
        while index < len(lines): 
            if lines[index] == searched:
                break
            index += 1
        for p, path in enumerate(path_set):
            start = index
            assert lines[start] == "Playing %s." % path
            while (index := index + 1) < len(lines): 
                if lines[index].startswith("Playing "):
                    break
            song_lines = lines[start+1:index]
            if any("no sound" in x for x in song_lines):
                parsed = dict(__ERROR__=True)
            else:
                parsed = parse_metadata(song_lines)
                if "ID_FILENAME" not in parsed:
                    parsed.update(dict(__ERROR__=True))
                else:
                    assert parsed["ID_FILENAME"] == path, (parsed["ID_FILENAME"], path)
            song_path = (
                os.path.join(
                    os.path.basename(os.path.dirname(path)),
                    os.path.basename(path),
                )
            )
            data[song_path] = parsed
    return data


if __name__ == "__main__":
    paths = get_file_list(*sys.argv[1:])
    data = get_metadata(paths)
    #print(len(paths))
    #print(len(data))
    #import pprint
    #pprint.pprint(data)
    for path, metadata in data.items():
        if "__ERROR__" in metadata:
            print(path)

    with open('metadata.json', 'w') as fh:
        json.dump(data, fh)

