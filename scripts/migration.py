import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pydantic
import typer
from pydantic import BaseModel

from src.database import Database, FileDownloadInfo, Game, Site, Song  # type:ignore


class OldSong(BaseModel):
    id: int
    path: Path
    title: str
    download_time: datetime
    retries: int | None = None


class OldGame(BaseModel):
    id: int
    path: Path
    title: str
    songs: dict[str, OldSong]


class OldDatabase(BaseModel):
    games: dict[str, OldGame]


@dataclass
class MD5Data:
    md5: str
    game_id: int
    song_id: int
    path: Path


app = typer.Typer()


@app.command()
def migrate(
    old_db_file: Path = typer.Option(..., help="old db file"),
    new_db_file: Path = typer.Option(..., help="new db file"),
    md5_file: Path = typer.Option(
        ..., help="md5 file containing hashes and paths of downloaded songs"
    ),
) -> None:
    md5_data = load_md5_data(md5_file)
    old_db = _load_old_db(old_db_file)
    new_db = Database(site=Site(base_url="https://smashcustommusic.net"))

    for old_game in old_db.games.values():
        new_songs: list[Song] = []
        for old_song in old_game.songs.values():
            md5_info = md5_data.get((old_game.id, old_song.id))
            if md5_info:
                download_info = FileDownloadInfo(
                    location=Path(md5_info.path),
                    timestamp=int(old_song.download_time.timestamp()),
                    file_md5=md5_info.md5,
                )
            else:
                print(f"No download for {old_game.id}.{old_song.id}")
                download_info = None

            new_song = Song(
                id=old_song.id,
                title=old_song.title,
                brstm_download_info=download_info,
            )
            new_songs.append(new_song)

        new_game = Game(
            id=old_game.id,
            title=old_game.title,
            songs=new_songs,
            download_timestamps=[int(time.time())],
        )
        new_db.site.games.append(new_game)

    new_db.save(new_db_file.open("w"))


def _load_old_db(file: Path) -> OldDatabase:
    with file.open() as fh:
        data = json.load(fh)

    for _, game in data.items():
        for _, song in game["songs"].items():
            time: str = song["download_time"]
            song["download_time"] = time[::-1].replace("-", ":", 2)[::-1]

    games = pydantic.TypeAdapter(dict[str, OldGame]).validate_python(data)
    return OldDatabase(games=games)


def load_md5_data(file: Path) -> dict[tuple[int, int], MD5Data]:
    pat = re.compile(r"([0-9a-f]{32}) [* ].*?(/(\d+)(?:_[^/]*)?/(\d+)(?:_[^/]*)?\.brstm)")
    rv: dict[tuple[int, int], MD5Data] = dict()
    for line in file.open():
        m = pat.fullmatch(line.strip())
        if not m:
            continue
        md5 = m.group(1)
        path = m.group(2)
        game_id = int(m.group(3))
        song_id = int(m.group(4))
        rv[(game_id, song_id)] = MD5Data(
            md5=md5,
            game_id=game_id,
            song_id=song_id,
            path=Path(path),
        )
    return rv


if __name__ == "__main__":
    app()
