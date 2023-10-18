from dataclasses import dataclass
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from client import Client, GameInfo, Parser, SongInfo
from database import Database, Game, Site, Song

# from downloader import DownloadError, Requester


@pytest.fixture
def testdata_directory() -> Path:
    return Path(__file__).parent / "testdata"


@dataclass
class FakeClient(Client):
    testdata_dir: Path

    def get_game_list(self) -> list[GameInfo]:
        home_page_html = (self.testdata_dir / "home.html").read_text()
        return Parser.get_game_list_from_home_page(home_page_html)

    def get_song_list(self, game_id: int) -> list[SongInfo]:
        html = (self.testdata_dir / f"game_{game_id}.html").read_text()
        return Parser.get_song_list_from_game_page(html)

    def get_brstm_file(self, song_id: int) -> bytes:
        return (self.testdata_dir / f"brstm_{song_id}.brstm").read_bytes()


@pytest.fixture
def fake_client(testdata_directory: Path) -> FakeClient:
    return FakeClient(testdata_dir=testdata_directory)


@pytest.fixture
def fake_database(testdata_directory: Path) -> Database:
    games = Parser.get_game_list_from_home_page(
        (testdata_directory / "home.html").read_text()
    )
    site = Site(base_url="idontexist.net")
    for game in games:
        songs = [
            Song(
                id=s.id,
                title=s.title,
            )
            for s in Parser.get_song_list_from_game_page(
                (testdata_directory / f"game_{game.id}.html").read_text()
            )
        ]
        site.games.append(
            Game(
                id=game.id,
                title=game.title,
                songs=songs,
            )
        )
    return Database(site=site).with_random(Random(123))


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as tmp:
        yield Path(tmp)


def build_site_with_games_and_songs(
    testdata_dir: Path,
    source: list[tuple[int, list[int]]],
) -> Site:
    games: list[Game] = []
    for game_id, song_ids in source:
        songs: list[Song] = []
        for song_id in song_ids:
            songs.append(
                Song(
                    id=song_id,
                    title=str(song_id),
                )
            )
        game = Game(
            id=game_id,
            title=str(game_id),
            songs=songs,
            is_deleted_from_site=not (testdata_dir / f"game_{game_id}.html").exists(),
        )
        games.append(game)

    site = Site(base_url="http://idontexist.net/", games=games)
    return site
