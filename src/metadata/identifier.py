import subprocess
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


class IdentifierError(Exception):
    ...  # pragma:nocover


@dataclass
class IdentifierResults:
    loop_start: int  # microseconds
    loop_end: int  # microseconds
    duration: float  # seconds


class Identifier(Protocol):
    @abstractmethod
    def extract_metadata(self, file: Path) -> IdentifierResults:
        ...  # pragma:nocover


class MplayerIdentifier(Identifier):
    def extract_metadata(self, file: Path) -> Optional[IdentifierResults]:
        try:
            lines = self._run_midentify(file)
        except IdentifierError:
            return None

        metadata: dict[str, str] = dict()
        for line in lines:
            key, value = line.split("=")
            metadata[key] = value

        start, end = self._extract_loop_start_and_end(metadata)
        duration = self._extract_duration(metadata)
        return IdentifierResults(
            loop_start=start,
            loop_end=end,
            duration=duration,
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
