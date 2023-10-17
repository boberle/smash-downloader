import json
import os
import subprocess
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

import pydantic
import typer
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

app = typer.Typer()


class Entry(BaseModel):
    path: Path
    loop_start: int  # microseconds
    loop_end: int
    duration: float  # seconds
    raw_output: str
    raw_output_type: Literal["midentify"] = "midentify"


class IdentifierError(Exception):
    ...  # pragma:nocover


class Identifier(Protocol):
    @abstractmethod
    def extract_metadata(self, file: Path, path: Path) -> Entry:
        ...  # pragma:nocover


class Checker(Protocol):
    @abstractmethod
    def check(self, file: Path) -> bool:
        ...  # pragma:nocover


class MplayerIdentifier(Identifier):
    def extract_metadata(self, file: Path, path: Path) -> Entry:
        lines = self._run_midentify(file)

        metadata: dict[str, str] = dict()
        for line in lines:
            key, value = line.split("=")
            metadata[key] = value

        start, end = self._extract_loop_start_and_end(metadata)
        duration = self._extract_duration(metadata)
        return Entry(
            path=path,
            loop_start=start,
            loop_end=end,
            duration=duration,
            raw_output="\n".join(lines),
        )

    def _run_midentify(self, file: Path) -> list[str]:
        """Run midentify and return the output lines.

        Note: Some file have non utf-8 metadata in them, for example:

            ...
            Playing 6_metroid_prime_2_echoes/342_ing_hive_main_theme.brstm.
            libavformat version 58.45.100 (external)
            ...
            ID_FILENAME=all/6_metroid_prime_2_echoes/342_ing_hive_main_theme.brstm
            ID_DEMUXER=nsv
            ID_AUDIO_FORMAT=�3▒�

        This is why we don't use `universal_newlines` and make the utf8
        conversion ourselves.

        Note: Some files are misidentified as TIVO:

            TiVo file format detected.

        instead of:

            libavformat file format detected.

        We force the libavformat with -demuxer 35 (see mplayer -demuxer help for the
        complete list).

        This is why we are not user `/usr/share/midentifier.sh` directly.
        """
        args = "mplayer -demuxer 35 -noconfig all -cache-min 0 -vo null -ao null -frames 0 -identify".split()
        args.append(str(file))
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise IdentifierError

        lines = proc.stdout.decode(errors="replace").splitlines()
        return list(filter(lambda x: x.startswith("ID_"), lines))

    def _extract_clip_info(self, metadata: dict[str, str]) -> dict[str, str]:
        rv: dict[str, str] = dict()
        if "ID_CLIP_INFO_N" in metadata:
            n = int(metadata["ID_CLIP_INFO_N"])
            for i in range(n):
                key = metadata[f"ID_CLIP_INFO_NAME{i}"]
                value = metadata[f"ID_CLIP_INFO_VALUE{i}"]
                rv[key] = value
        return rv

    def _extract_loop_start_and_end(self, metadata: dict[str, str]) -> tuple[int, int]:
        clip_info = self._extract_clip_info(metadata)
        start = int(clip_info.get("loop_start", "0"))
        end = int(clip_info.get("loop_end", "0"))

        if "ID_START_TIME" in metadata:
            assert float(metadata["ID_START_TIME"]) == 0.0, metadata["ID_START_TIME"]

        return start, end

    def _extract_duration(self, metadata: dict[str, str]) -> float:
        return float(metadata.get("ID_LENGTH", "0.0"))


class FFMPEGChecker(Checker):
    def check(self, file: Path) -> bool:
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", file, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return proc.returncode == 0 and not proc.stdout and not proc.stderr


class Differ:
    def diff(self, root_dir: Path, entries: list[Entry]) -> list[Path]:
        rv: list[Path] = []
        for entry in entries:
            full_path = root_dir / entry.path
            if not full_path.exists():
                rv.append(full_path)
        return rv


@dataclass
class Counters:
    successes: list[Path] = field(default_factory=list)
    checker_errors: list[Path] = field(default_factory=list)
    identifier_errors: list[Path] = field(default_factory=list)


@dataclass
class Extractor:
    identifier: Identifier
    checker: Checker
    force: bool

    def extract_metadata_from_files(
        self, root_dir: Path, entries: list[Entry]
    ) -> Counters:
        paths = {entry.path for entry in entries}
        counters = Counters()

        for root, dnames, fnames in os.walk(root_dir):
            for fname in fnames:
                full_path = Path(os.path.join(root, fname))

                if full_path.suffix != ".brstm":
                    continue

                path = Path(os.path.relpath(full_path, root_dir))
                if not self.force and path in paths:
                    continue

                if not self.checker.check(full_path):
                    counters.checker_errors.append(full_path)
                    continue

                try:
                    entry = self.identifier.extract_metadata(full_path, path)
                except IdentifierError:
                    counters.identifier_errors.append(full_path)
                else:
                    entries.append(entry)
                    counters.successes.append(full_path)

        return counters


def read_entries(file: Path) -> list[Entry]:
    data = json.load(file.open())
    return pydantic.TypeAdapter(list[Entry]).validate_python(data)


@app.command()
def extract_brstm_data(
    root_dir: Path = typer.Option(
        ...,
        help="root dir where to recursively look for brstm files. Paths will be relative to this dir",
    ),
    output_file: Path = typer.Option(
        ...,
        help="output file. If already exists, metadata will not be extracted again for file already present, except if --force is set",
    ),
    force: bool = typer.Option(
        False,
        help="re-extract data even if metadata are already extracted for the file",
    ),
) -> None:
    extractor = Extractor(
        identifier=MplayerIdentifier(),
        checker=FFMPEGChecker(),
        force=force,
    )
    if output_file.exists():
        entries = read_entries(output_file)
    else:
        entries = []

    counters = extractor.extract_metadata_from_files(root_dir, entries)
    not_in_root_dir = Differ().diff(root_dir, entries)

    with open(output_file, "w") as fh:
        json.dump(entries, fh, default=pydantic_encoder)

    if counters.checker_errors:
        print("========== CHECK ERRORS ==========")
        for file in counters.checker_errors:
            print(f" - {str(file)}")

    if counters.identifier_errors:
        print("========== IDENTIFIER ERRORS ==========")
        for file in counters.identifier_errors:
            print(f" - {str(file)}")

    if not_in_root_dir:
        print("========== NOT IN ROOT DIR ==========")
        for file in not_in_root_dir:
            print(f" - {str(file)}")


if __name__ == "__main__":
    app()
