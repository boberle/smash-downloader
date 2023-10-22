import datetime
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import typer

from smashdown.client import Client, FileWriter, SmashClient
from smashdown.database import Database, Site
from smashdown.downloader import Downloader
from smashdown.updater import Updater

BASE_URL = "http://smashcustommusic.net"


app = typer.Typer(add_completion=False)


@app.command()
def download_musics(
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the music files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    client = SmashClient(base_url=BASE_URL, nap_time=nap_time)
    db = _get_db(db_file)
    app = App(client=client, db=db)
    app.download_musics(output_dir=output_dir, max_count=max_count)


@app.command()
def update_game_list(
    db_file: Path = typer.Option(..., help="json database file"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    client = SmashClient(
        base_url=BASE_URL,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
        nap_time=nap_time,
    )
    db = _get_db(db_file)
    app = App(client=client, db=db)
    app.update_game_list()


@app.command()
def update_game_song_lists(
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    client = SmashClient(
        base_url=BASE_URL,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
        nap_time=nap_time,
    )
    db = _get_db(db_file)
    app = App(client=client, db=db)
    app.update_game_song_lists(max_count=max_count)


@app.command()
def statistics(
    db_file: Path = typer.Option(..., help="json database file"),
) -> None:
    db = _get_db(db_file)
    stats = db.get_statistics()
    print(f"games: {stats.games}")
    print(f"games visited: {stats.games_visited}")
    print(f"games not visited: {stats.games_not_visited}")
    print(f"games deleted from site: {stats.games_deleted_from_site}")
    print(
        f"game oldest visit: {datetime.datetime.fromtimestamp(stats.game_oldest_visit).isoformat()}"
    )
    print(f"songs: {stats.songs}")
    print(f"songs downloaded: {stats.songs_downloaded}")
    print(f"songs not downloaded: {stats.songs_not_downloaded}")
    print(f"songs deleted from site: {stats.songs_deleted_from_site}")


def _get_db(db_file: Path) -> Database:
    if db_file.exists():
        db = Database.build_from_file(db_file)
        return db
    else:
        logging.info("New database created.")
        return Database(
            site=Site(
                base_url=BASE_URL,
            )
        ).with_output_file(db_file)


@dataclass
class App:
    client: Client
    db: Database

    def update_game_list(self) -> None:
        updater = Updater(client=self.client, db=self.db)
        updater.update_game_list()

    def update_game_song_lists(self, max_count: int) -> None:
        updater = Updater(client=self.client, db=self.db)
        updater.update_game_song_lists(max_count=max_count)

    def download_musics(self, output_dir: Path, max_count: int) -> None:
        downloader = Downloader(client=self.client, db=self.db, output_dir=output_dir)
        downloader.download_brstm_files(max_count=max_count)


if __name__ == "__main__":
    app()
