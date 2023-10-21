import subprocess
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class CheckerResult:
    success: bool


class Checker(Protocol):
    @abstractmethod
    def check(self, file: Path) -> CheckerResult:
        ...  # pragma:nocover


class FFMPEGChecker(Checker):
    def check(self, file: Path) -> CheckerResult:
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", file, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return CheckerResult(
            success=proc.returncode == 0 and not proc.stdout and not proc.stderr
        )
