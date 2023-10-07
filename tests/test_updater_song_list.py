import time
from pathlib import Path

import pytest
from conftest import build_site_with_games_and_songs

from client import Client
from database import Database, Game, Site, Song
from updater import Updater


@pytest.mark.parametrize(
    "source,target,removed,not_found_games",
    [
        (
            [(1726, [96613, 32272, 93397]), (4126, [77724, 96008]), (5063, [])],
            [(1726, [96613, 32272, 93397]), (4126, [77724, 96008]), (5063, [])],
            [],
            [],
        ),
        (
            [(1726, [93397]), (4126, []), (5063, [])],
            [(1726, [96613, 32272, 93397]), (4126, [77724, 96008]), (5063, [])],
            [],
            [],
        ),
        (
            [
                (1726, [96613, 93397, 111]),
                (4126, [222, 77724, 96008]),
                (5063, [333]),
                (999, [444]),
            ],
            [
                (1726, [96613, 32272, 93397, 111]),
                (4126, [77724, 96008, 222]),
                (5063, [333]),
                (999, [444]),
            ],
            [111, 222, 333],
            [999],
        ),
    ],
)
def test_song_list_updater(
    testdata_directory: Path,
    fake_client: Client,
    source: list[tuple[int, list[int]]],
    target: list[tuple[int, list[int]]],
    removed: list[int],
    not_found_games: list[int],
) -> None:
    site = build_site_with_games_and_songs(testdata_directory, source)
    updater = Updater(client=fake_client, db=Database(site=site))

    for game in site.games:
        if game.is_deleted_from_site:
            continue

        assert len(game.download_timestamps) == 0

        updater.update_game_song_list(game_id=game.id)
        if game.id not in not_found_games:
            assert len(game.download_timestamps) == 1
            assert game.download_timestamps[-1] >= int(time.time())

    total_songs_in_target = sum([len(x[1]) for x in target])
    total_songs_in_db = sum([len(g.songs) for g in site.games])
    assert total_songs_in_target == total_songs_in_db

    assert len(target) == len(site.games)
    for got_game, (want_game_id, want_game_songs) in zip(site.games, target):
        for song in got_game.songs:
            assert song.id in want_game_songs
            assert song.is_deleted_from_site == (song.id in removed)


def test_song_list_updater__reappearing_removed_songs_are_not_marked_as_removed(
    testdata_directory: Path,
    fake_client: Client,
) -> None:
    site = Site(
        base_url="http://idontexist.net/",
        games=[
            Game(
                id=1726,
                title="foo",
                songs=[
                    Song(
                        id=93397,
                        title="bar",
                        is_deleted_from_site=True,
                    )
                ],
            )
        ],
    )
    assert site.games[0].songs[0].is_deleted_from_site is True
    updater = Updater(client=fake_client, db=Database(site=site))

    for game in site.games:
        updater.update_game_song_list(game_id=game.id)

    assert all([s.is_deleted_from_site is False for s in site.games[0].songs])
