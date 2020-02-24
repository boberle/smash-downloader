import re
import os

from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup

import docdownloader

class GamePage(docdownloader.Page):

    def __init__(self, url, output_dir, ref_url=None):
        super().__init__(url, output_dir, ref_url, write_tmp=True)
        self.album_name = self._get_album_name()
        assert self.album_name
        self.album_name = docdownloader.remove_diacritics(self.album_name)
        self.filename = re.sub(r'[^a-z0-9]+', '_', self.album_name.lower()) + \
            ".html"
        self.filename = self.filename.strip('_')
        self.write()
        self._parse()

    def _get_album_name(self):
        soup = BeautifulSoup(self.code, "lxml")
        title = soup.find('title')
        if title:
            album_name = str(title.string)
            return album_name
        return None

    def _parse(self):
        soup = BeautifulSoup(self.code, "lxml")
        for anchor in soup.find_all('a'):
            if re.fullmatch(r'\/\d+', anchor['href']):
                url = anchor['href']
                docdownloader.log("found song at '%s'" % url)
                SongPage(url=url, output_dir=self.output_dir,
                    ref_url=self.url)

class SongPage(docdownloader.Page):

    def __init__(self, url, output_dir, ref_url=None):
        super().__init__(url, output_dir, ref_url, write_tmp=True)
        self.song_number = os.path.basename(urlparse(url).path)
        self.song_name = self._get_song_name()
        assert self.song_number
        assert self.song_name
        self.song_name = docdownloader.remove_diacritics(self.song_name)
        self.song_name = re.sub(r'[^a-z0-9]+', '_', self.song_name.lower()) \
            .strip('_')
        self.filename = self.song_name + ".html"
        self.write()
        SongDocument(self.output_dir, self.song_number, self.song_name)

    def _get_song_name(self):
        soup = BeautifulSoup(self.code, "lxml")
        title = soup.find('title')
        if title:
            song_name = str(title.string)
            if song_name.endswith(" - Video Game Music"):
                song_name = song_name[0:song_name.index(" - Video Game Music")]
            return song_name
        return None


class SongDocument(docdownloader.BinaryDocument):

    def __init__(self, output_dir, song_number, song_name):
        url = "http://www.smashcustommusic.com/brstm/%s" % song_number
        super().__init__(url, output_dir)
        self.filename = song_name + ".brstm"
        self.write()
    


if __name__ == '__main__':
    # ----- test:
    #GamePage(url="http://www.smashcustommusic.com/game/1036",
    #    output_dir="/tmp/testing")
    # -----
    docdownloader.log_name = "downloads.log"
    args = docdownloader.parse_args()
    GamePage(url=args.url, output_dir=args.output_dir)

