import hashlib
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from smashdown.client import Client
from smashdown.database import Database, FileDownloadInfo, Game, Song


def remove_diacritics(text: str) -> str:
    """Return the `text` string without any diacritics."""
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def slugify(text: str) -> str:
    """Return a slugified version of the given text."""
    text = remove_diacritics(text)
    text = re.sub(r"[^a-z0-9]+", "_", text.lower())
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")
    return text


@dataclass
class Downloader:
    client: Client
    db: Database
    output_dir: Path

    def download_brstm_file(self, song: Song) -> None:
        game = self.db.get_game_from_song_id(song_id=song.id)
        game_path = self.get_game_path(game)
        music_path = self.get_music_path(game_path, song)
        music_data = self.client.get_brstm_file(song_id=song.id)
        self.write_data(music_path, music_data)
        md5 = hashlib.md5(music_data).hexdigest()
        song.brstm_download_info = FileDownloadInfo(
            location=music_path,
            timestamp=int(time.time()),
            file_md5=md5,
        )
        logging.info(f"Music saved into {music_path} (md5 {md5}).")
        self.db.save()

    def download_brstm_files(self, max_count: int) -> None:
        for song in self.db.get_songs_with_no_brstm_downloaded(max_count):
            self.download_brstm_file(song=song)

    @staticmethod
    def get_game_path(game: Game) -> Path:
        slug = slugify(game.title)
        if slug:
            slug = "_" + slug
        return Path(f"{game.id}{slug}")

    @staticmethod
    def get_music_path(game_path: Path, song: Song) -> Path:
        slug = slugify(song.title)
        if slug:
            slug = "_" + slug
        return game_path / f"{song.id}{slug}.brstm"

    def write_data(self, path: Path, data: bytes) -> None:
        path = self.output_dir / path
        parent = path.parent
        if not parent.is_dir():
            parent.mkdir(parents=True, exist_ok=True)

        path.write_bytes(data)
