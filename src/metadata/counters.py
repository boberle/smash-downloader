from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Counters:
    successes: list[Path] = field(default_factory=list)
    left_untouched: list[Path] = field(default_factory=list)
    checker_errors: list[Path] = field(default_factory=list)
    identifier_errors: list[Path] = field(default_factory=list)
    not_found_files: list[Path] = field(default_factory=list)

    def print(self) -> None:
        if self.checker_errors:
            print("========== CHECK ERRORS ==========")
            for file in self.checker_errors:
                print(f" - {str(file)}")

        if self.identifier_errors:
            print("========== IDENTIFIER ERRORS ==========")
            for file in self.identifier_errors:
                print(f" - {str(file)}")

        if self.not_found_files:
            print("========== NOT IN ROOT DIR ==========")
            for file in self.not_found_files:
                print(f" - {str(file)}")
