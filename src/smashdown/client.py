from __future__ import annotations

import logging
import random
import re
import time
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"


@dataclass
class ParsingError(Exception):
    message: str


@dataclass
class GameInfo:
    id: int
    title: str


@dataclass
class SongInfo:
    id: int
    title: str


class Client(Protocol):
    @abstractmethod
    def get_game_list(self) -> list[GameInfo]:
        ...  # pragma:nocover

    @abstractmethod
    def get_song_list(self, game_id: int) -> list[SongInfo]:
        ...  # pragma:nocover

    @abstractmethod
    def get_brstm_file(self, song_id: int) -> bytes:
        ...  # pragma:nocover


@dataclass
class SmashClient(Client):
    base_url: str
    writer: Writer | None = None
    nap_time: tuple[int, int] | None = (60, 120)

    game_url_path_template: str = "/game/{id}"
    brstm_url_path_template: str = "/brstm/{id}"

    user_agent: str = USER_AGENT
    _first_call: bool = True

    def __post_init__(self) -> None:
        headers = {
            "User-Agent": USER_AGENT,
        }
        self._session = requests.Session()
        self._session.headers.update(headers)

    def get_game_list(self) -> list[GameInfo]:
        self._nap()
        url = self.base_url
        logging.debug(f"Downloading from {url}.")
        result = self._session.get(url)
        html = result.text
        logging.info(f"Downloaded from {url}.")
        if self.writer:
            self.writer.write_home_page_html(html)
        return Parser.get_game_list_from_home_page(html)

    def get_song_list(self, game_id: int) -> list[SongInfo]:
        self._nap()
        url = urljoin(self.base_url, self.game_url_path_template.format(id=game_id))
        logging.debug(f"Downloading from {url}.")
        result = self._session.get(url)
        html = result.text
        logging.info(f"Downloaded from {url}.")
        if self.writer:
            self.writer.write_game_page_html(game_id, html)
        return Parser.get_song_list_from_game_page(html)

    def get_brstm_file(self, song_id: int) -> bytes:
        self._nap()
        url = urljoin(self.base_url, self.brstm_url_path_template.format(id=song_id))
        logging.debug(f"Downloading from {url}.")
        result = self._session.get(url)
        binary = result.content
        logging.info(f"Downloaded from {url}.")
        return binary

    def _nap(self) -> None:
        if not self._first_call and self.nap_time is not None:
            duration = random.randint(self.nap_time[0], self.nap_time[1])
            logging.info(f"Napping for {duration} seconds.")
            time.sleep(duration)
        self._first_call = False


class Writer(Protocol):
    @abstractmethod
    def write_home_page_html(self, data: str) -> None:
        ...  # pragma:nocover

    @abstractmethod
    def write_game_page_html(self, game_id: int, data: str) -> None:
        ...  # pragma:nocover


@dataclass
class FileWriter(Writer):
    output_dir: Path
    timestamp: int

    def write_home_page_html(self, data: str) -> None:
        file = f"home_{self.timestamp}.html"
        (self.output_dir / file).write_text(data, encoding="utf-8")
        logging.info(f"HTML saved in {file}.")

    def write_game_page_html(self, game_id: int, data: str) -> None:
        file = f"game_{game_id}_{self.timestamp}.html"
        (self.output_dir / file).write_text(data, encoding="utf-8")
        logging.info(f"HTML saved in {file}.")


class Parser:
    @staticmethod
    def get_game_list_from_home_page(html: str) -> list[GameInfo]:
        href_game_pattern = re.compile(r"^/game/")
        id_game_pattern = re.compile(r"/game/(\d+)")

        soup = BeautifulSoup(html, "lxml")
        games: list[GameInfo] = []
        for anchor in soup.find_all("a", dict(href=href_game_pattern)):
            path = anchor["href"]
            id_match = id_game_pattern.fullmatch(path)
            if id_match is None:
                raise ParsingError(message=f"unable to find the game id in {path}")
            id = int(id_match.group(1))
            title = anchor.get_text()
            games.append(
                GameInfo(
                    id=id,
                    title=title,
                )
            )
        logging.info(f"Parsed {len(games)} game(s) from home page.")
        return games

    @staticmethod
    def get_song_list_from_game_page(html: str) -> list[SongInfo]:
        href_song_pattern = re.compile(r"^/song/")
        id_song_pattern = re.compile(r"/song/(\d+)")

        soup = BeautifulSoup(html, "lxml")
        songs: list[SongInfo] = []
        for anchor in soup.find_all("a", dict(href=href_song_pattern)):
            path = anchor["href"]
            id_match = id_song_pattern.fullmatch(path)
            if id_match is None:
                raise ParsingError(message=f"unable to find the song id in {path}")
            id = int(id_match.group(1))
            title = anchor.get_text()
            songs.append(
                SongInfo(
                    id=id,
                    title=title,
                )
            )
        logging.info(f"Extracted {len(songs)} song(s) from game page.")
        return songs
