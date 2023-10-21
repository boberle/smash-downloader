from __future__ import annotations

import functools
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Any, Optional

import pydantic
from pydantic import BaseModel, Field, PrivateAttr


class GameNotFound(Exception):
    ...  # pragma:nocover


class SongNotFound(Exception):
    ...  # pragma:nocover


class FileDownloadInfo(BaseModel):
    location: Path
    timestamp: int
    file_md5: str


class Base(BaseModel):
    @staticmethod
    def _get_last_checked(timestamps: list[int]) -> int | None:
        if len(timestamps) == 0:
            return None
        return timestamps[-1]


class Song(Base):
    id: int
    title: str
    is_deleted_from_site: bool = False
    brstm_download_info: FileDownloadInfo | None = None

    @property
    def is_brstm_downloaded(self) -> int | None:
        return self.brstm_download_info is not None


class Game(Base):
    id: int
    title: str
    songs: list[Song] = Field(default_factory=list)
    is_deleted_from_site: bool = False
    download_timestamps: list[int] = Field(default_factory=list)

    @property
    def last_checked(self) -> int | None:
        return self._get_last_checked(self.download_timestamps)


class Site(Base):
    base_url: str
    games: list[Game] = Field(default_factory=list)
    download_timestamps: list[int] = Field(default_factory=list)

    @property
    def last_checked(self) -> int | None:
        return self._get_last_checked(self.download_timestamps)


class Database(BaseModel):
    site: Site

    _random: Random = PrivateAttr(default_factory=Random)
    _output_file: Optional[Path] = PrivateAttr(None)

    @staticmethod
    def build_from_file(file: Path) -> Database:
        with file.open() as fh:
            database = pydantic.TypeAdapter(Database).validate_python(json.load(fh))
            logging.info(f"Databse read from '{file}'.")
            database.with_output_file(file)
            return database

    def with_random(self, random: Random) -> Database:
        self._random = random
        return self

    def with_output_file(self, output_file: Path) -> Database:
        self._output_file = output_file
        return self

    def save(self) -> None:
        if self._output_file is None:
            return
        with self._output_file.open("w") as fh:
            fh.write(self.model_dump_json(indent=2))
        logging.info(f"Database file saved into '{self._output_file}'")

    def get_game_from_id(self, game_id: int) -> Game:
        for game in self.site.games:
            if game.id == game_id:
                return game
        raise GameNotFound

    def get_song_from_id(self, song_id: int) -> Song:
        for game in self.site.games:
            for song in game.songs:
                if song.id == song_id:
                    return song
        raise SongNotFound

    def get_game_from_song_id(self, song_id: int) -> Game:
        for game in self.site.games:
            for song in game.songs:
                if song.id == song_id:
                    return game
        raise SongNotFound

    def get_song_from_downloaded_path(self, path: Path) -> tuple[Game, Song]:
        for game in self.site.games:
            for song in game.songs:
                if (
                    song.brstm_download_info is not None
                    and song.brstm_download_info.location == path
                ):
                    return game, song
        raise SongNotFound

    def get_games_by_last_checked(self, count: int | None) -> list[Game]:
        """Return games starting with the not checked, then the oldest checked."""
        filtered = filter(lambda g: not g.is_deleted_from_site, self.site.games)
        games = sorted(filtered, key=functools.cmp_to_key(self._cmp))
        if count is None:
            return games
        return games[:count]

    def get_songs_with_no_brstm_downloaded(self, count: int | None) -> list[Song]:
        songs: list[Song] = []
        for game in self.site.games:
            for song in game.songs:
                if not song.is_deleted_from_site and not song.is_brstm_downloaded:
                    songs.append(song)

        self._random.shuffle(songs)
        if count is None:
            return songs
        return songs[:count]

    @staticmethod
    def _cmp(a: Any, b: Any) -> int:
        if a.last_checked is None:
            return -1
        if b.last_checked is None:
            return 1
        if a.last_checked < b.last_checked:
            return -1
        if a.last_checked == b.last_checked:
            return 0
        return 1

    def get_statistics(self) -> DatabaseStatistics:
        stats = DatabaseStatistics()
        for game in self.site.games:
            stats.games += 1
            if len(game.download_timestamps) == 0:
                stats.games_not_visited += 1
            else:
                stats.games_visited += 1
                if stats.game_oldest_visit == 0:
                    stats.game_oldest_visit = game.download_timestamps[-1]
                else:
                    stats.game_oldest_visit = min(
                        stats.game_oldest_visit, game.download_timestamps[-1]
                    )
            if game.is_deleted_from_site:
                stats.games_deleted_from_site += 1

            for song in game.songs:
                stats.songs += 1

                if song.is_brstm_downloaded:
                    stats.songs_downloaded += 1
                else:
                    stats.songs_not_downloaded += 1
                if song.is_deleted_from_site:
                    stats.songs_deleted_from_site += 1

        return stats


@dataclass
class DatabaseStatistics:
    games: int = 0
    games_visited: int = 0
    games_not_visited: int = 0
    games_deleted_from_site: int = 0
    songs: int = 0
    songs_downloaded: int = 0
    songs_not_downloaded: int = 0
    songs_deleted_from_site: int = 0
    game_oldest_visit: int = 0
