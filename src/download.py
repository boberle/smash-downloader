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
from util import compute_md5_hash, url_parser

app = typer.Typer(add_completion=False)


@app.command()
def download_musics(
    base_url: str = typer.Option(
        ...,
        help="the base url of the site, for example 'http://www.smashcustommusic.com'",
        parser=url_parser,
    ),
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the music files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    client = SmashClient(base_url=base_url, nap_time=nap_time)
    db = _get_db(db_file, base_url=base_url)
    app = App(client=client, db=db)
    app.download_musics(output_dir=output_dir, max_count=max_count)


@app.command()
def update_game_list(
    base_url: str = typer.Option(
        ...,
        help="the base url of the site, for example 'http://www.smashcustommusic.com'",
        parser=url_parser,
    ),
    db_file: Path = typer.Option(..., help="json database file"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    client = SmashClient(
        base_url=base_url,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
        nap_time=nap_time,
    )
    db = _get_db(db_file, base_url=base_url)
    app = App(client=client, db=db)
    app.update_game_list()


@app.command()
def update_game_song_lists(
    base_url: str = typer.Option(
        ...,
        help="the base url of the site, for example 'http://www.smashcustommusic.com'",
        parser=url_parser,
    ),
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    """Select --max-count games to be updated, starting with the ones that have
    been visited a long time ago.
    """
    client = SmashClient(
        base_url=base_url,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
        nap_time=nap_time,
    )
    db = _get_db(db_file, base_url=base_url)
    app = App(client=client, db=db)
    app.update_game_song_lists(max_count=max_count)


@app.command()
def update_game_song_lists_by_using_homepage(
    base_url: str = typer.Option(
        ...,
        help="the base url of the site, for example 'http://www.smashcustommusic.com'",
        parser=url_parser,
    ),
    db_file: Path = typer.Option(..., help="json database file"),
    max_count: int = typer.Option(..., help="maximum number of file to download"),
    output_dir: Path = typer.Option(
        ..., help="directory in which to save the html files"
    ),
    nap_time: tuple[int, int] = typer.Option(
        (60, 120), help="min/max nap time between two downloads"
    ),
) -> None:
    """Select --max-count games to be updated, choosing at random among the
    games that have fewer songs in the db than shown in the homepage.
    """
    client = SmashClient(
        base_url=base_url,
        writer=FileWriter(
            output_dir=output_dir,
            timestamp=int(time.time()),
        ),
        nap_time=nap_time,
    )
    db = _get_db(db_file, base_url=base_url)
    app = App(client=client, db=db)
    app.update_game_song_lists_by_using_homepage(max_count=max_count)


@app.command()
def statistics(
    db_file: Path = typer.Option(..., help="json database file"),
) -> None:
    db = Database.build_from_file(db_file)
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


@app.command()
def check_md5(
    db_file: Path = typer.Option(..., help="json database file"),
    song_dir: Path = typer.Option(
        ..., help="directory in which the music files are saved"
    ),
) -> None:
    db = Database.build_from_file(db_file)
    count = 0
    for game in db.site.games:
        for song in game.songs:
            if song.brstm_download_info is None:
                continue
            path = song_dir / song.brstm_download_info.location
            computed = compute_md5_hash(path)

            count += 1
            if count % 1000 == 0:
                print("done:", count)
            if computed != song.brstm_download_info.file_md5:
                print("failed:", path, computed, song.brstm_download_info.file_md5)


def _get_db(db_file: Path, base_url: str) -> Database:
    if db_file.exists():
        db = Database.build_from_file(db_file)
        return db
    else:
        logging.info("New database created.")
        return Database(
            site=Site(
                base_url=base_url,
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

    def update_game_song_lists_by_using_homepage(self, max_count: int) -> None:
        updater = Updater(client=self.client, db=self.db)
        updater.update_game_song_lists_by_using_home_page(max_count=max_count)

    def download_musics(self, output_dir: Path, max_count: int) -> None:
        downloader = Downloader(client=self.client, db=self.db, output_dir=output_dir)
        downloader.download_brstm_files(max_count=max_count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app()
