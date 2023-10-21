from pathlib import Path

from src.extract_metadata.identifier import MplayerIdentifier


def test_can_read(testdata_directory: Path) -> None:
    file = testdata_directory / "onetwothree.brstm"
    identifier_results = MplayerIdentifier().extract_metadata(file)
    assert identifier_results.loop_start == 1_079_728
    assert identifier_results.duration == 2.82

