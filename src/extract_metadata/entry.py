import json
from pathlib import Path
from typing import Optional

import pydantic
from pydantic import BaseModel


class Entry(BaseModel):
    path: Path
    timestamp: int
    loop_start: int = 0  # microseconds
    loop_end: int = 0  # microseconds
    duration: float = 0.0  # seconds
    size: int = 0  # bytes
    title: Optional[str] = None
    game_title: Optional[str] = None
    error: bool = False


def read_entries(file: Path) -> list[Entry]:
    data = json.load(file.open())
    return pydantic.TypeAdapter(list[Entry]).validate_python(data)
