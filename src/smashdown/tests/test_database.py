import random
from pathlib import Path

from smashdown.database import Database, FileDownloadInfo, Game, Site, Song


def test_get_game_by_id() -> None:
    db = Database(site=Site(base_url="http://idontexist.net"))
    db.site.games = [
        Game(id=1, title="1"),
        Game(id=2, title="2"),
        Game(id=3, title="3"),
    ]
    found = db.get_game_from_id(2)
    assert found is not None
    assert found.id == 2


def test_get_song_by_id() -> None:
    db = Database(site=Site(base_url="http://idontexist.net"))
    db.site.games = [
        Game(
            id=1,
            title="1",
            songs=[
                Song(id=1, title="1"),
                Song(id=2, title="2"),
                Song(id=3, title="3"),
            ],
        ),
        Game(id=2, title="2", songs=[]),
        Game(
            id=3,
            title="3",
            songs=[
                Song(id=4, title="4"),
                Song(id=5, title="5"),
            ],
        ),
    ]
    found = db.get_song_from_id(4)
    assert found is not None
    assert found.id == 4


def test_get_game_from_song_id() -> None:
    db = Database(site=Site(base_url="http://idontexist.net"))
    db.site.games = [
        Game(
            id=1,
            title="1",
            songs=[
                Song(id=1, title="1"),
                Song(id=2, title="2"),
                Song(id=3, title="3"),
            ],
        ),
        Game(id=2, title="2", songs=[]),
        Game(
            id=3,
            title="3",
            songs=[
                Song(id=4, title="4"),
                Song(id=5, title="5"),
            ],
        ),
    ]
    found = db.get_game_from_song_id(4)
    assert found is not None
    assert found.id == 3


def test_get_games_by_last_checked() -> None:
    db = Database(site=Site(base_url="http://idontexist.net"))
    db.site.games = [
        Game(id=1, title="1", download_timestamps=[1, 5]),
        Game(id=2, title="2"),
        Game(id=3, title="3", download_timestamps=[3, 2]),
        Game(id=4, title="4"),
        Game(id=5, title="5", is_deleted_from_site=True),
    ]

    games = db.get_games_by_last_checked(2)
    assert len(games) == 2
    assert list(map(lambda g: g.id, games)) == [4, 2]

    games = db.get_games_by_last_checked(None)
    assert len(games) == 4
    assert list(map(lambda g: g.id, games)) == [4, 2, 3, 1]


def test_get_songs_with_no_brstm_downloaded() -> None:
    db = Database(site=Site(base_url="http://idontexist.net")).with_random(
        random=random.Random(123)
    )
    song1 = Song(
        id=1,
        title="1",
        brstm_download_info=FileDownloadInfo(
            location=Path("foo"), timestamp=2, file_md5="md5"
        ),
    )
    song2 = Song(id=2, title="2")
    song3 = Song(id=3, title="3")
    song4 = Song(
        id=4,
        title="4",
        brstm_download_info=FileDownloadInfo(
            location=Path("foo"), timestamp=1, file_md5="md5"
        ),
    )
    song5 = Song(id=5, title="5")
    song6 = Song(
        id=6,
        title="6",
        brstm_download_info=FileDownloadInfo(
            location=Path("foo"), timestamp=3, file_md5="md5"
        ),
    )
    song7 = Song(id=7, title="7", is_deleted_from_site=True)

    db.site.games = [
        Game(id=1, title="1", songs=[song1, song6, song7]),
        Game(id=2, title="2"),
        Game(id=3, title="3", songs=[song5, song4, song3]),
        Game(id=4, title="5", songs=[song2]),
    ]

    musics = db.get_songs_with_no_brstm_downloaded(2)
    assert len(musics) == 2
    assert list(map(lambda m: m.id, musics)) == [2, 3]

    musics = db.get_songs_with_no_brstm_downloaded(None)
    assert len(musics) == 3
    assert list(map(lambda m: m.id, musics)) == [2, 3, 5]
