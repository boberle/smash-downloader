import docdownloader
from bs4 import BeautifulSoup

class GameList(docdownloader.PageList):

    def __init__(self, url, output_dir, output_file):
        super().__init__(url, output_dir, output_file, write_tmp=True)
        self.write(data=self._parse())
        
    def _parse(self):
        soup = BeautifulSoup(self.code, "lxml")
        data = []
        for anchor in soup.find_all('a'):
            if anchor['href'].startswith('/game/'):
                url = anchor['href']
                url = docdownloader.build_url(string=url, ref_url=self.url)
                docdownloader.log("found game at '%s'" % url)
                data.append(docdownloader.Item(name=str(anchor.string),
                    url=url, cmd='python3 download_music.py -o '
                    'just_downloaded %s' % url))
        return data

if __name__ == '__main__':
    pass
    #GameList('http://www.smashcustommusic.com', '.', 'run_game_list.sh')
