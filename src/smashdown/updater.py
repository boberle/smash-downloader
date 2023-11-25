import logging
import time
from dataclasses import dataclass, field
from random import Random

from smashdown.client import Client, GameInfo, SongInfo
from smashdown.database import Database, Game, Song


@dataclass
class Updater:
    client: Client
    db: Database
    rand: Random = field(default_factory=Random)

    def update_game_list(self) -> None:
        game_list = self.client.get_game_list()
        games_on_site: dict[int, GameInfo] = {game.id: game for game in game_list}
        games_in_db: dict[int, Game] = {game.id: game for game in self.db.site.games}

        logging.debug("Looking for games removed from website.")
        for game_in_db in games_in_db.values():
            if game_in_db.id not in games_on_site:
                logging.info(
                    f"Game {game_in_db.id} ({game_in_db.title}) has been removed from website."
                )
                game_in_db.is_deleted_from_site = True

        logging.debug("Looking for games added.")
        for game_on_site in games_on_site.values():
            if game_on_site.id not in games_in_db:
                new_game = Game(
                    id=game_on_site.id,
                    title=game_on_site.title,
                )
                self.db.site.games.append(new_game)
                logging.info(f"Game {new_game.id} ({new_game.title}) has been added.")
            else:
                # the song may have re-appeared, so we update:
                games_in_db[game_on_site.id].is_deleted_from_site = False

        self.db.site.download_timestamps.append(int(time.time()))
        self.db.save()

    def update_game_song_list(self, game_id: int) -> None:
        game = self.db.get_game_from_id(game_id)
        song_list = self.client.get_song_list(game_id)
        songs_on_site: dict[int, SongInfo] = {song.id: song for song in song_list}
        songs_in_db: dict[int, Song] = {song.id: song for song in game.songs}

        logging.debug("Looking for songs removed from website.")
        for song_in_db in songs_in_db.values():
            if song_in_db.id not in songs_on_site:
                logging.info(
                    f"Song {song_in_db.id} ({song_in_db.title}) has been removed from website."
                )
                song_in_db.is_deleted_from_site = True

        logging.debug("Looking for songs added.")
        for song_on_site in songs_on_site.values():
            if song_on_site.id not in songs_in_db:
                new_song = Song(
                    id=song_on_site.id,
                    title=song_on_site.title,
                )
                game.songs.append(new_song)
                logging.info(f"Song {new_song.id} ({new_song.title}) has been added.")
            else:
                # the song may have re-appeared, so we update:
                songs_in_db[song_on_site.id].is_deleted_from_site = False

        game.download_timestamps.append(int(time.time()))
        self.db.save()

    def update_game_song_lists(self, max_count: int) -> None:
        for game in self.db.get_games_by_last_checked(max_count):
            self.update_game_song_list(game.id)

    def update_game_song_lists_by_using_home_page(self, max_count: int) -> None:
        games = self._get_games_with_fewer_songs_than_in_database(max_count)
        for game in games:
            self.update_game_song_list(game.id)

    def _get_games_with_fewer_songs_than_in_database(
        self, max_count: int
    ) -> list[GameInfo]:
        game_list = self.client.get_game_list()
        games_in_db: dict[int, Game] = {game.id: game for game in self.db.site.games}

        games_with_fewer_songs_than_expected: list[GameInfo] = []
        for game in game_list:
            game_in_db = games_in_db.get(game.id)
            if game_in_db is None:
                continue
            song_count_in_db = len(
                [
                    song
                    for song in game_in_db.songs
                    if song.is_deleted_from_site is False
                ]
            )
            if song_count_in_db < game.song_count:
                games_with_fewer_songs_than_expected.append(game)

        self.rand.shuffle(games_with_fewer_songs_than_expected)
        return games_with_fewer_songs_than_expected[:max_count]
