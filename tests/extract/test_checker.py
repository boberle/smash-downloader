from pathlib import Path

from extract_metadata.checker import FFMPEGChecker


def test_success(testdata_directory: Path) -> None:
    file = testdata_directory / "onetwothree.brstm"
    checker_results = FFMPEGChecker().check(file)
    assert checker_results.success is True


def test_no_success_on_empty_file(testdata_directory: Path) -> None:
    file = testdata_directory / "empty.brstm"
    checker_results = FFMPEGChecker().check(file)
    assert checker_results.success is False


def test_no_success_on_corrupted_file(testdata_directory: Path) -> None:
    file = testdata_directory / "corrupted.brstm"
    checker_results = FFMPEGChecker().check(file)
    assert checker_results.success is False
