from pathlib import Path

import pytest

from metadata.entry import Entry
from metadata.extract import extract
from smashdown.database import Database, FileDownloadInfo, Game, Site, Song


@pytest.fixture
def database() -> Database:
    return Database(
        site=Site(
            base_url="https://idontexist.net",
            games=[
                Game(
                    id=100,
                    title="English game",
                    songs=[
                        Song(
                            id=1,
                            title="English song",
                            brstm_download_info=FileDownloadInfo(
                                location=Path("english/onetwothree_en.brstm"),
                                timestamp=123,
                                file_md5="abc",
                            ),
                        ),
                    ],
                ),
                Game(
                    id=200,
                    title="Other game",
                    songs=[
                        Song(
                            id=2,
                            title="French song",
                            brstm_download_info=FileDownloadInfo(
                                location=Path("other/onetwothree_fr.brstm"),
                                timestamp=123,
                                file_md5="abc",
                            ),
                        ),
                        Song(
                            id=3,
                            title="German song",
                            brstm_download_info=FileDownloadInfo(
                                location=Path("other/onetwothree_de.brstm"),
                                timestamp=123,
                                file_md5="abc",
                            ),
                        ),
                    ],
                ),
                Game(
                    id=300,
                    title="Strange game",
                    songs=[
                        Song(
                            id=4,
                            title="Empty song",
                            brstm_download_info=FileDownloadInfo(
                                location=Path("strange/empty.brstm"),
                                timestamp=123,
                                file_md5="abc",
                            ),
                        ),
                    ],
                ),
            ],
        )
    )


@pytest.fixture
def entries_on_disk() -> list[Entry]:
    return [
        Entry(
            path=Path("english/onetwothree_en.brstm"),
            timestamp=0,
            loop_start=1021678,
            loop_end=0,
            duration=2.82,
            size=142592,
            error=False,
            game_title="English game",
            title="English song",
        ),
        Entry(
            path=Path("other/onetwothree_de.brstm"),
            timestamp=0,
            loop_start=963628,
            loop_end=0,
            duration=3.01,
            size=152064,
            error=False,
            game_title="Other game",
            title="German song",
        ),
        Entry(
            path=Path("other/onetwothree_fr.brstm"),
            timestamp=0,
            loop_start=1358367,
            loop_end=0,
            duration=3.18,
            size=160640,
            error=False,
            game_title="Other game",
            title="French song",
        ),
        Entry(
            path=Path("strange/empty.brstm"),
            timestamp=0,
            loop_start=0,
            loop_end=0,
            duration=0.0,
            size=0,
            error=True,
            game_title=None,
            title=None,
        ),
    ]


def test_extract(
    testdata_directory: Path, database: Database, entries_on_disk: list[Entry]
) -> None:
    root_dir = testdata_directory / "songs"
    entries, counters = extract(
        root_dir=root_dir,
        db=database,
        entry_list=[],
        force=True,
    )
    # ignore timestamp
    for entry in entries:
        entry.timestamp = 0
    entries.sort(key=lambda e: str(e.path))

    assert entries == entries_on_disk

    assert counters.not_found_files == []
    assert counters.checker_errors == [Path("strange/empty.brstm")]
    assert counters.identifier_errors == []
    assert len(counters.successes) == 3
    assert counters.left_untouched == []


def test_extract_with_force(
    testdata_directory: Path, database: Database, entries_on_disk: list[Entry]
) -> None:
    root_dir = testdata_directory / "songs"
    entries, counters = extract(
        root_dir=root_dir,
        db=database,
        entry_list=[
            Entry(
                path=Path("english/onetwothree_en.brstm"),
                timestamp=0,
                loop_start=0,
                loop_end=0,
                duration=0.0,
                size=0,
                error=False,
                title="foobar",
                game_title="foobar",
            ),
        ],
        force=True,
    )
    # ignore timestamp
    for entry in entries:
        entry.timestamp = 0
    entries.sort(key=lambda e: str(e.path))

    assert entries == entries_on_disk

    assert counters.not_found_files == []
    assert counters.checker_errors == [Path("strange/empty.brstm")]
    assert counters.identifier_errors == []
    assert len(counters.successes) == 3
    assert counters.left_untouched == []


def test_extract_without_force(
    testdata_directory: Path, database: Database, entries_on_disk: list[Entry]
) -> None:
    root_dir = testdata_directory / "songs"
    entries, counters = extract(
        root_dir=root_dir,
        db=database,
        entry_list=[
            Entry(
                path=Path("english/onetwothree_en.brstm"),
                timestamp=0,
                loop_start=0,
                loop_end=0,
                duration=0.0,
                size=0,
                error=False,
                title="foobar",
                game_title="foobar",
            ),
        ],
        force=False,
    )
    # ignore timestamp
    for entry in entries:
        entry.timestamp = 0
    entries.sort(key=lambda e: str(e.path))

    expected = list(entries_on_disk)
    expected[0] = Entry(
        path=Path("english/onetwothree_en.brstm"),
        timestamp=0,
        loop_start=0,
        loop_end=0,
        duration=0.0,
        size=0,
        error=False,
        title="foobar",
        game_title="foobar",
    )

    assert entries == expected

    assert counters.not_found_files == []
    assert counters.checker_errors == [Path("strange/empty.brstm")]
    assert counters.identifier_errors == []
    assert len(counters.successes) == 2
    assert counters.left_untouched == [Path("english/onetwothree_en.brstm")]


def test_extract_with_not_found_file(
    testdata_directory: Path, database: Database, entries_on_disk: list[Entry]
) -> None:
    root_dir = testdata_directory / "songs"
    existing_entry = Entry(
        path=Path("idontexist/idontexist.brstm"),
        timestamp=0,
        loop_start=0,
        loop_end=0,
        duration=0.0,
        size=0,
        error=False,
        title="foobar",
        game_title="foobar",
    )
    entries, counters = extract(
        root_dir=root_dir,
        db=database,
        entry_list=[existing_entry],
        force=True,
    )
    # ignore timestamp
    for entry in entries:
        entry.timestamp = 0
    entries.sort(key=lambda e: str(e.path))

    expected = list(entries_on_disk)
    expected.append(existing_entry)
    expected.sort(key=lambda e: str(e.path))
    assert entries == expected

    assert counters.not_found_files == [Path("idontexist/idontexist.brstm")]
    assert counters.checker_errors == [Path("strange/empty.brstm")]
    assert counters.identifier_errors == []
    assert len(counters.successes) == 3
    assert counters.left_untouched == []
