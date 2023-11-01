import hashlib
from pathlib import Path

from pydantic import HttpUrl


def url_parser(value: str) -> str:
    return str(HttpUrl(value))


def compute_md5_hash(file: Path) -> str:
    return hashlib.md5(file.read_bytes()).hexdigest()
