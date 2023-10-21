from pathlib import Path

from smashdown.client import GameInfo, Parser, SongInfo


def test_get_game_list_from_home_page(testdata_directory: Path) -> None:
    html = (testdata_directory / "home.html").read_text()
    games = Parser.get_game_list_from_home_page(html)
    assert games == [
        GameInfo(
            id=1726,
            title="3D Dot Game Heroes",
        ),
        GameInfo(
            id=4126,
            title="Ape Escape: Big Mission/SaruGetchu: Daisakusen",
        ),
        GameInfo(
            id=5063,
            title="16-Bit Rhythm Land",
        ),
    ]


def test_get_song_list_from_game_page(testdata_directory: Path) -> None:
    html = (testdata_directory / "game_1726.html").read_text()
    songs = Parser.get_song_list_from_game_page(html)
    assert songs == [
        SongInfo(
            id=96613,
            title="Block Destruction",
        ),
        SongInfo(
            id=32272,
            title="Main Theme",
        ),
        SongInfo(
            id=93397,
            title="The Lost Forest",
        ),
    ]
