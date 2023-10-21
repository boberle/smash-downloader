from pathlib import Path

import requests_mock

from smashdown.client import FileWriter, SmashClient


def test_get_game_list(testdata_directory: Path, tmp_dir: Path) -> None:
    writer = FileWriter(output_dir=tmp_dir, timestamp=123)
    client = SmashClient(base_url="http://idontexist.net", writer=writer)

    with requests_mock.Mocker() as m:
        m.get(
            "http://idontexist.net/",
            text=(testdata_directory / "home.html").read_text(),
        )
        games = client.get_game_list()
        assert len(games) == 3
        assert {g.id for g in games} == {1726, 4126, 5063}

        assert (tmp_dir / "home_123.html").exists()


def test_get_game_song_list(testdata_directory: Path, tmp_dir: Path) -> None:
    writer = FileWriter(output_dir=tmp_dir, timestamp=123)
    client = SmashClient(base_url="http://idontexist.net", writer=writer)

    with requests_mock.Mocker() as m:
        m.get(
            "http://idontexist.net/game/1726",
            text=(testdata_directory / "game_1726.html").read_text(),
        )
        songs = client.get_song_list(game_id=1726)
        assert len(songs) == 3
        assert {s.id for s in songs} == {96613, 32272, 93397}

        assert (tmp_dir / "game_1726_123.html").exists()


def test_get_brstm_file(testdata_directory: Path) -> None:
    client = SmashClient(base_url="http://idontexist.net")

    with requests_mock.Mocker() as m:
        content = (testdata_directory / "brstm_32272.brstm").read_bytes()
        m.get("http://idontexist.net/brstm/32272", content=content)
        res = client.get_brstm_file(song_id=32272)
        assert res == content
