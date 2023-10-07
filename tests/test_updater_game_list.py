import time
from pathlib import Path

import pytest

from client import Client
from database import Database, Game, Site
from updater import Updater


@pytest.mark.parametrize(
    "source,target,removed",
    [
        ([], [1726, 4126, 5063], []),
        ([4126], [1726, 4126, 5063], []),
        ([1726, 4126], [1726, 4126, 5063], []),
        ([1726, 4126, 5063], [1726, 4126, 5063], []),
        ([1726, 5063, 1111], [1726, 4126, 5063, 1111], [1111]),
        ([1111, 2222], [1111, 2222, 1726, 4126, 5063], [1111, 2222]),
    ],
)
def test_game_list_updater(
    testdata_directory: Path,
    fake_client: Client,
    source: list[int],
    target: list[int],
    removed: list[int],
) -> None:
    site = Site(
        base_url="http://idontexist.net/",
        games=[Game(id=id, title=str(id)) for id in source],
    )
    updater = Updater(client=fake_client, db=Database(site=site))
    updater.update_game_list()

    assert len(site.games) == len(target)
    assert len(site.download_timestamps) == 1
    assert site.download_timestamps[-1] >= int(time.time())

    for game in site.games:
        assert game.id in target
        assert game.is_deleted_from_site == (game.id in removed)


def test_game_list_updater__reappearing_removed_games_are_not_marked_as_removed(
    testdata_directory: Path,
    fake_client: Client,
) -> None:
    site = Site(
        base_url="http://idontexist.net/",
        games=[
            Game(
                id=1726,
                title="foo",
                is_deleted_from_site=True,
            )
        ],
    )
    assert site.games[0].is_deleted_from_site is True

    updater = Updater(client=fake_client, db=Database(site=site))
    updater.update_game_list()

    assert site.games[0].is_deleted_from_site is False
