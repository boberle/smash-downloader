from urllib.parse import urlparse, urlunparse
import time, urllib.request, urllib, os, random, re, argparse, tempfile
import socket, unicodedata, time

snap_time = (3, 4, 5)
#snap_time = (6, 7, 8)
#snap_time = () # no snap

max_timeout = 120
max_attempts = 10

debug_files = dict() # format: {'url' => 'local_file'}

log_name = ""

def remove_diacritics(text):
    """ Based on a perl routine I wrote several years ago:
            $text = NFD($text);
            $text =~ s/\p{NonspacingMark}//g;
            return $text;
            (NonspacingMark is Mn in short)
        See also: https://docs.python.org/3.5/library/unicodedata.html
        Other possibility
        (http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string):
        def remove_accents(input_str):
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            only_ascii = nfkd_form.encode('ASCII', 'ignore')
            return only_ascii
    """
    return ''.join(char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != "Mn")


def log(msg):
    global log_name
    if log_name:
        fh = open(log_name, "a")
        fh.write(time.ctime() + ": " + msg + "\n")
        fh.close()
    print(msg)

def ask_confirm(msg):
    while True:
        buf = input(msg)
        if buf in "Yy":
            return True
        elif buf in "Nn":
            return False
        print("Sorry, I don't understand. Try again.")

def snap():
    global snap_time
    if snap_time:
        sec = random.choice(snap_time)
        print("(zzzzzzz... for %d seconds)" % sec)
        time.sleep(sec)

def download(url): # return binary text
    global debug_files, max_timeout, max_attempts
    if debug_files and url in debug_files:
        return open(debug_files[url], "rb").read()
    count = 0
    while True:
        try:
            snap()
            log("downloading from `%s'" % url)
            fh = urllib.request.urlopen(url, timeout=max_timeout)
            return fh.read()
        except socket.timeout:
            log("attempt %d/%d failed (timeout)" %
                (count+1, max_attempts))
            count += 1
            if count < max_attempts:
                continue
            raise RuntimeError("timeout: %d" % max_timeout)
        except urllib.error.URLError as e:
            print(e)
            raise RuntimeError("can't read the page `%s'" % url)
        assert False

def write(data, path=None, force=False):
    if not path:
        path = os.path.join(tempfile.gettempdir(), "downloaded_%d.html" %
            os.getpid())
    log("saving `%s'" % path)
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        log("creating dir '%s'..." % dirname)
        os.makedirs(dirname)
    if not force and os.path.exists(path):
        raise RuntimeError("file `%s' exists" % path)
    open(path, 'wb').write(data)

def build_url(string, ref_url=""):
    parsed = urlparse(string)
    ref_parsed = urlparse(ref_url) if ref_url else None
    scheme = parsed.scheme if parsed.scheme else ref_parsed.scheme if \
        ref_parsed else ""
    netloc = parsed.netloc if parsed.netloc else ref_parsed.netloc if \
        ref_parsed else ""
    path = parsed.path
    if not path.startswith('/') and ref_parsed and ref_parsed.path:
        path = os.path.join(ref_parsed.path, path)
    params = parsed.params
    query = parsed.query
    fragment = parsed.fragment
    assert scheme, string
    assert netloc, string
    return urlunparse((scheme, netloc, path, params, query, fragment))


class Document():

    def __init__(self, url, output_dir, ref_url=None):
        self.url = build_url(url, ref_url=ref_url)
        self.output_dir = output_dir
        self.data = download(self.url) # binary
        # default name
        self.filename = self.filename_from_url_path

    def decode(self):
        return self.data.decode('utf-8')

    def write(self, force=False):
        write(data=self.data, force=force, path=os.path.join(self.output_dir,
            self.filename))

    def write_tmp(self):
        write(self.data, force=True)

    @property
    def filename_from_url_path(self, suffix=""):
        if suffix and not suffix.startswith('.'):
            suffix = "." + suffix
        parsed = urlparse(self.url)
        assert parsed.netloc, "no netloc: %s" % self.url
        return (parsed.netloc + parsed.path).replace("/", "%") + suffix

    @property
    def filename_from_url_filename(self, suffix=""):
        if suffix and not suffix.startswith('.'):
            suffix = "." + suffix
        parsed = urlparse(self.url)
        assert parsed.netloc, "no netloc: %s" % self.url
        return (parsed.netloc + os.path.basename(parsed.path)).replace("/",
            "%") + suffix

    @property
    def path(self):
        return os.path.join(self.output_dir, self.name)


class BinaryDocument(Document):

    def __init__(self, url, output_dir, ref_url=None):
        super().__init__(url, output_dir, ref_url)


class Page(Document):

    def __init__(self, url, output_dir, ref_url=None, write_tmp=False):
        super().__init__(url, output_dir=output_dir, ref_url=ref_url)
        if write_tmp:
            self.write_tmp()
        self.code = self.decode()

class Item:
    def __init__(self, name, url, cmd):
        self.name = name
        self.url = url
        self.cmd = cmd
    def __str__(self):
        if isinstance(self.cmd, list):
            cmd = " ".join(self.cmd)
        else:
            cmd = self.cmd
        return "#[ ] %s: %s\n#%s" % (self.name, self.url, self.cmd)

class PageList(Page):

    def __init__(self, url, output_dir, output_file, write_tmp=False):
        super().__init__(url, output_dir=output_dir, write_tmp=write_tmp)
        self.output_file = output_file

    def write(self, data, sort=True):
        """ data is a list of Item's """
        if sort:
            data = sorted(data, key=lambda x: x.name)
        fh = open(os.path.join(self.output_dir, self.output_file), 'w')
        for d in data:
            fh.write(str(d) + "\n")
        fh.close()
        

def parse_args(callback=None, description=""):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("url", default="", help="url")
    parser.add_argument("-o", dest="output_dir", default=".",
        help="output dir, default is current")
    if callback:
        callback(parser)
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    pass
    #args = parse_args()
    #url = args.url

    #data = download("http://www.smashcustommusic.com/brstm/23140")
    #write(data, "/tmp/more.brstm")
