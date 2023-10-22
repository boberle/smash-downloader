from pydantic import HttpUrl


def url_parser(value: str) -> str:
    return str(HttpUrl(value))
