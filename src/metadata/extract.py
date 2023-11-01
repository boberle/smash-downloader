import json
import logging
import os
import time
from pathlib import Path

import typer
from pydantic.json import pydantic_encoder

from metadata.checker import FFMPEGChecker
from metadata.counters import Counters
from metadata.entry import Entry, read_entries
from metadata.identifier import MplayerIdentifier
from smashdown.database import Database, Game, Song

app = typer.Typer(add_completion=False)


@app.command()
def extract_brstm_data(
    root_dir: Path = typer.Option(
        ...,
        help="root dir where to recursively look for brstm files. Paths will be relative to this dir",
    ),
    db_file: Path = typer.Option(
        ...,
        help="database file (read only)",
    ),
    output_file: Path = typer.Option(
        ...,
        help="output file. If already exists, metadata will not be extracted again for file already present, except if --force is set",
    ),
    max_count: int = typer.Option(
        0,
        help="maximum of file to process. Default is 0, which infinite",
    ),
    force: bool = typer.Option(
        False,
        help="re-extract data even if metadata are already extracted for the file",
    ),
) -> None:
    if output_file.exists():
        logging.info(f"Reading entries from '{output_file}")
        entries = read_entries(file=output_file)
    else:
        logging.info(f"Creating a new entry list (file '{output_file}' doesn't exist')")
        entries = []
    db = Database.build_from_file(file=db_file)
    entries, counters = extract(
        root_dir=root_dir,
        db=db,
        entry_list=entries,
        force=force,
        max_count=max_count,
    )
    with open(output_file, "w") as fh:
        logging.info(f"Writing entries into '{output_file}'")
        json.dump(entries, fh, default=pydantic_encoder)
    counters.print()


def extract(
    root_dir: Path,
    db: Database,
    entry_list: list[Entry],
    force: bool,
    max_count: int = 0,
) -> tuple[list[Entry], Counters]:
    entries = {entry.path: entry for entry in entry_list}

    logging.debug(f"Getting files from {root_dir}.")
    files = get_files(root_dir=root_dir)
    logging.info(f"Got {len(files)} file(s) from {root_dir}")

    file_set = set(files)
    files2songs: dict[Path, tuple[Game, Song]] = dict()
    for game in db.site.games:
        for song in game.songs:
            if song.brstm_download_info is not None:
                if song.brstm_download_info.location in file_set:
                    files2songs[song.brstm_download_info.location] = (game, song)

    counters = Counters()
    for entry_path in entries.keys():
        if entry_path not in file_set:
            logging.warning(f"Entry path '{entry_path}' not found on file system.")
            counters.not_found_files.append(entry_path)

    checker = FFMPEGChecker()
    identifier = MplayerIdentifier()

    processed_count = 0
    for i, file in enumerate(files, start=1):
        if max_count and processed_count >= max_count:
            logging.info(f"Reached max count {max_count}. Quitting.")
            break

        logging.debug(f"Processing file '{file}' ({i}/{len(files)})")
        if not force and file in entries:
            logging.debug(
                f"File '{file}' find in entry list. Left untouched (use --force to update)."
            )
            counters.left_untouched.append(file)
            continue

        processed_count += 1
        full_path = root_dir / file
        entry = Entry(
            path=file, timestamp=int(time.time()), size=os.path.getsize(full_path)
        )
        entries[file] = entry

        checker_results = checker.check(full_path)
        if not checker_results.success:
            logging.warning(f"Checker error for '{file}'.")
            counters.checker_errors.append(file)
            entry.error = True
            continue

        identifier_results = identifier.extract_metadata(full_path)
        if identifier_results is None:
            logging.warning(f"Identifier error for '{file}'.")
            counters.identifier_errors.append(file)
            entry.error = True
            continue
        else:
            entry.loop_start = identifier_results.loop_start
            entry.loop_end = identifier_results.loop_end
            entry.duration = identifier_results.duration
            game, song = files2songs[file]
            entry.title = song.title
            entry.game_title = game.title
            logging.debug(f"File '{file}' successfully identified.")
            counters.successes.append(full_path)

    return list(entries.values()), counters


def get_files(root_dir: Path) -> set[Path]:
    paths: set[Path] = set()
    for root, dnames, fnames in os.walk(root_dir):
        for fname in fnames:
            full_path = Path(os.path.join(root, fname))
            if full_path.suffix != ".brstm":
                continue
            path = Path(os.path.relpath(full_path, root_dir))
            paths.add(path)
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app()
