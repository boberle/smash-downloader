import time
from pathlib import Path

import pytest

from smashdown.client import Client
from smashdown.database import Database, Game, Song
from smashdown.downloader import Downloader


def test_downloader(
    fake_database: Database,
    fake_client: Client,
    tmp_dir: Path,
) -> None:
    downloader = Downloader(client=fake_client, db=fake_database, output_dir=tmp_dir)
    song = fake_database.get_song_from_id(96613)
    downloader.download_brstm_file(song)
    exp = tmp_dir / "1726_3d_dot_game_heroes" / "96613_block_destruction.brstm"
    assert exp.exists()
    assert song.brstm_download_info is not None
    assert song.brstm_download_info.timestamp >= int(time.time())
    assert song.brstm_download_info.location == Path(
        "1726_3d_dot_game_heroes/96613_block_destruction.brstm"
    )
    assert song.brstm_download_info.file_md5 == "f8e1eb9b3294c2c0f0f0eda10f6cadb5"


def test_downloader_multiple_files(
    fake_database: Database,
    fake_client: Client,
    tmp_dir: Path,
) -> None:
    downloader = Downloader(client=fake_client, db=fake_database, output_dir=tmp_dir)
    downloader.download_brstm_files(max_count=4)
    assert (tmp_dir / "1726_3d_dot_game_heroes/32272_main_theme.brstm").exists()
    assert (tmp_dir / "1726_3d_dot_game_heroes/93397_the_lost_forest.brstm").exists()
    assert (
        tmp_dir
        / "4126_ape_escape_big_mission_sarugetchu_daisakusen/77724_kessen_specter.brstm"
    ).exists()
    assert (
        tmp_dir
        / "4126_ape_escape_big_mission_sarugetchu_daisakusen/96008_sun_sun_beach.brstm"
    ).exists()


def test_downloader_no_slug(
    fake_database: Database,
    fake_client: Client,
    tmp_dir: Path,
) -> None:
    downloader = Downloader(client=fake_client, db=fake_database, output_dir=tmp_dir)
    song = fake_database.get_song_from_id(96613)
    game = fake_database.get_game_from_song_id(song.id)
    song.title = "+++"
    game.title = "+++"
    downloader.download_brstm_file(song)
    exp = tmp_dir / "1726" / "96613.brstm"
    assert exp.exists()
    assert song.brstm_download_info is not None
    assert song.brstm_download_info.timestamp >= int(time.time())
    assert song.brstm_download_info.location == Path("1726/96613.brstm")
    assert song.brstm_download_info.file_md5 == "f8e1eb9b3294c2c0f0f0eda10f6cadb5"


@pytest.mark.parametrize(
    "game_title,song_title,exp",
    [
        ["abc", "def", "123_abc/456_def.brstm"],
        ["a-b?c", "d e+++++f", "123_a_b_c/456_d_e_f.brstm"],
        ["+++", "", "123/456.brstm"],
        ["été abc dEf", "çöÉ ἈΈᾒξθ", "123_ete_abc_def/456_coe.brstm"],
    ],
)
def test_get_game_and_music_path(game_title: str, song_title: str, exp: str) -> None:
    game_path = Downloader.get_game_path(Game(id=123, title=game_title))
    song_path = Downloader.get_music_path(game_path, Song(id=456, title=song_title))
    assert song_path == Path(exp)
