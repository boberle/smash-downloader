import time
from dataclasses import dataclass
from pathlib import Path

import typer

from client import Client, FileWriter, SmashClient
from database import Database, Site
from downloader import Downloader
from updater import Updater

BASE_URL = "http://smashcustommusic.net"


app = typer.Typer()


@app.command()
def download_musics(
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the music files"
    ),
) -> None:
    client = SmashClient(base_url=BASE_URL)
    with db_file.open() as fh:
        db = Database.build_from_file(fh)
    app = App(client=client, db=db)
    app.download_musics(
        output_dir=output_dir, max_count=max_count, db_output_file=db_file
    )


@app.command()
def update_game_list(
    db_file: Path = typer.Option(..., help="json database file"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
) -> None:
    client = SmashClient(
        base_url=BASE_URL,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
    )
    db = _get_db(db_file)
    app = App(client=client, db=db)
    app.update_game_list(db_file)


@app.command()
def update_game_song_lists(
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
) -> None:
    client = SmashClient(
        base_url=BASE_URL,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
    )
    db = _get_db(db_file)
    app = App(client=client, db=db)
    app.update_game_song_lists(max_count=max_count, db_output_file=db_file)


def _get_db(db_file: Path) -> Database:
    if db_file.exists():
        with db_file.open() as fh:
            return Database.build_from_file(fh)
    else:
        return Database(
            site=Site(
                base_url=BASE_URL,
            )
        )


@dataclass
class App:
    client: Client
    db: Database

    def update_game_list(self, db_output_file: Path) -> None:
        updater = Updater(client=self.client, db=self.db)
        updater.update_game_list()
        with db_output_file.open("w") as fh:
            self.db.save(writer=fh)

    def update_game_song_lists(self, max_count: int, db_output_file: Path) -> None:
        updater = Updater(client=self.client, db=self.db)
        updater.update_game_song_lists(max_count=max_count)
        with db_output_file.open("w") as fh:
            self.db.save(writer=fh)

    def download_musics(
        self, output_dir: Path, max_count: int, db_output_file: Path
    ) -> None:
        downloader = Downloader(client=self.client, db=self.db, output_dir=output_dir)
        downloader.download_brstm_files(max_count=max_count)
        with db_output_file.open("w") as fh:
            self.db.save(writer=fh)


if __name__ == "__main__":
    app()
